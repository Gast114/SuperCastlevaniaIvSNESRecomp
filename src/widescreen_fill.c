/* Designed widescreen margins for scenes the game authored only 256 px wide.
 *
 * Several cutscenes draw one 256-pixel picture and leave the rest of their
 * 64-column map empty or holding unrelated tiles (the gate before stage 1, the
 * tombstone of the prologue). Widescreen shows 43 px of that on either side.
 * The rules in assets/widescreen_margins.txt compose the missing columns from
 * the scene's own tiles instead, so the margins look like part of the
 * picture.
 *
 * Rules are applied to a render-only copy of VRAM (Ppu.renderVram). The
 * guest's VRAM, its savestates and the 4:3 picture are untouched, and a rule
 * never changes a column the native 256-pixel field shows. The file is read
 * again whenever it changes, so a margin can be designed while the scene is
 * on screen: edit <exe dir>/assets/widescreen_margins.txt and advance a frame.
 *
 * Format, one rule per line, '#' starts a comment. Columns and rows are
 * tilemap cells of the layer (0..63 on a 64-wide/tall map), ranges inclusive:
 *
 *   <scene> copy   <BG1..BG4> <c0>-<c1> <src> <r0>-<r1> [hflip]
 *       column c0+i <- column src+i, rows r0..r1. With hflip the block is
 *       mirrored: column c1-i <- column src+i with each tile flipped, which
 *       continues a picture seamlessly past its own edge (the way SCIV's
 *       artists built symmetric scenes such as the castle gate).
 *   <scene> clear  <BGn> <c0>-<c1> <r0>-<r1>
 *   <scene> tile   <BGn> <col> <row> <tilemap word, hex>
 *   <scene> follow <BGn>
 *       a margin row stays empty while the same row is empty across the
 *       whole native field (for layers that scroll in from off screen)
 */
#include "widescreen_fill.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>

#define MARGIN_FILE "assets/widescreen_margins.txt"
/* Margin columns a rule may touch on each side of the field: 6 x 8 px
 * covers the 43-pixel widescreen margin. */
enum { kMarginCols = 6, kMaxRules = 256 };

typedef enum { kOpCopy, kOpClear, kOpTile, kOpFollow } MarginOp;

typedef struct MarginRule {
    char scene[16];
    MarginOp op;
    uint8_t layer, hflip;
    uint8_t c0, c1, src, r0, r1;
    uint16_t word;
} MarginRule;

static MarginRule g_rules[kMaxRules];
static int g_rule_count;
static time_t g_loaded_mtime = (time_t)-1;
static unsigned g_check_countdown;
static uint16_t g_render_vram[0x8000];

static int ParseRange(const char *text, unsigned *lo, unsigned *hi)
{
    char *end;
    *lo = *hi = (unsigned)strtoul(text, &end, 10);
    if (end == text)
        return 0;
    if (*end == '-')
        *hi = (unsigned)strtoul(end + 1, &end, 10);
    return *end == 0 && *lo <= *hi && *hi < 64;
}

static int ParseLayer(const char *text, uint8_t *layer)
{
    if (strlen(text) != 3 || strncmp(text, "BG", 2) || text[2] < '1' || text[2] > '4')
        return 0;
    *layer = (uint8_t)(text[2] - '1');
    return 1;
}

static int ParseRule(char *line, MarginRule *rule)
{
    char *tok[8];
    int n = 0;
    for (char *t = strtok(line, " \t\r\n"); t && n < 8; t = strtok(NULL, " \t\r\n"))
        tok[n++] = t;
    unsigned lo, hi, a, b;
    if (n < 3 || strlen(tok[0]) >= sizeof(rule->scene) || !ParseLayer(tok[2], &rule->layer))
        return 0;
    snprintf(rule->scene, sizeof(rule->scene), "%s", tok[0]);
    if (!strcmp(tok[1], "copy") && (n == 6 || n == 7)) {
        rule->op = kOpCopy;
        if (!ParseRange(tok[3], &lo, &hi) || !ParseRange(tok[4], &a, &b) || a != b ||
            !ParseRange(tok[5], &a, &b))
            return 0;
        rule->c0 = (uint8_t)lo; rule->c1 = (uint8_t)hi;
        rule->src = (uint8_t)strtoul(tok[4], NULL, 10);
        rule->r0 = (uint8_t)a; rule->r1 = (uint8_t)b;
        rule->hflip = n == 7 && !strcmp(tok[6], "hflip");
        return n == 6 || rule->hflip;
    }
    if (!strcmp(tok[1], "clear") && n == 5) {
        rule->op = kOpClear;
        if (!ParseRange(tok[3], &lo, &hi) || !ParseRange(tok[4], &a, &b))
            return 0;
        rule->c0 = (uint8_t)lo; rule->c1 = (uint8_t)hi;
        rule->r0 = (uint8_t)a; rule->r1 = (uint8_t)b;
        return 1;
    }
    if (!strcmp(tok[1], "tile") && n == 6) {
        rule->op = kOpTile;
        if (!ParseRange(tok[3], &lo, &hi) || lo != hi || !ParseRange(tok[4], &a, &b) || a != b)
            return 0;
        rule->c0 = rule->c1 = (uint8_t)lo;
        rule->r0 = rule->r1 = (uint8_t)a;
        rule->word = (uint16_t)strtoul(tok[5], NULL, 16);
        return 1;
    }
    if (!strcmp(tok[1], "follow") && n == 3) {
        rule->op = kOpFollow;
        return 1;
    }
    return 0;
}

static void LoadRulesIfChanged(void)
{
    struct stat st;
    if (g_check_countdown) {
        g_check_countdown--;
        return;
    }
    g_check_countdown = 30;
    if (stat(MARGIN_FILE, &st) != 0) {
        g_rule_count = 0;
        g_loaded_mtime = (time_t)-1;
        return;
    }
    if (st.st_mtime == g_loaded_mtime)
        return;
    g_loaded_mtime = st.st_mtime;
    g_rule_count = 0;
    FILE *f = fopen(MARGIN_FILE, "r");
    if (!f)
        return;
    char line[256];
    for (int number = 1; fgets(line, sizeof(line), f); number++) {
        char *hash = strchr(line, '#');
        if (hash)
            *hash = 0;
        if (strspn(line, " \t\r\n") == strlen(line))
            continue;
        if (g_rule_count == kMaxRules || !ParseRule(line, &g_rules[g_rule_count]))
            fprintf(stderr, "[widescreen] %s:%d: rule ignored\n", MARGIN_FILE, number);
        else
            g_rule_count++;
    }
    fclose(f);
    fprintf(stderr, "[widescreen] %d margin rules loaded\n", g_rule_count);
}

typedef struct LayerMap {
    unsigned base, cols, rows, wide;
    uint8_t in_field[64];   /* map column visible in the native field */
    unsigned first, count;  /* field columns: first .. first+count-1 (wrapping) */
} LayerMap;

static void DescribeLayer(const Ppu *ppu, unsigned layer, LayerMap *map)
{
    map->base = PPU_bgTilemapAdr(ppu, layer);
    map->wide = PPU_bgTilemapWider(ppu, layer) != 0;
    map->cols = map->wide ? 64 : 32;
    map->rows = PPU_bgTilemapHigher(ppu, layer) ? 64 : 32;
    unsigned h = ppu->hScroll[layer] & 0x3ff;
    map->first = (h >> 3) % map->cols;
    map->count = (h & 7) ? 33 : 32;
    memset(map->in_field, 0, sizeof(map->in_field));
    for (unsigned i = 0; i < map->count; i++)
        map->in_field[(map->first + i) % map->cols] = 1;
}

static unsigned CellAddress(const LayerMap *map, unsigned col, unsigned row)
{
    col %= map->cols;
    row %= map->rows;
    return (map->base + ((col >> 5) << 10) + ((row >> 5) << (map->wide ? 11 : 10)) +
            ((row & 31) << 5) + (col & 31)) & 0x7fff;
}

static void PutCell(const LayerMap *map, unsigned col, unsigned row, uint16_t word)
{
    if (!map->in_field[col % map->cols])
        g_render_vram[CellAddress(map, col, row)] = word;
}

static void ApplyRule(const Ppu *ppu, const MarginRule *rule)
{
    LayerMap map;
    DescribeLayer(ppu, rule->layer, &map);
    switch (rule->op) {
    case kOpCopy:
        for (unsigned c = rule->c0; c <= rule->c1; c++)
            for (unsigned r = rule->r0; r <= rule->r1; r++) {
                uint16_t word = ppu->vram[CellAddress(&map, rule->src + (c - rule->c0), r)];
                if (rule->hflip)
                    PutCell(&map, rule->c1 - (c - rule->c0), r, (uint16_t)(word ^ 0x4000));
                else
                    PutCell(&map, c, r, word);
            }
        break;
    case kOpClear:
        for (unsigned c = rule->c0; c <= rule->c1; c++)
            for (unsigned r = rule->r0; r <= rule->r1; r++)
                PutCell(&map, c, r, 0);
        break;
    case kOpTile:
        PutCell(&map, rule->c0, rule->r0, rule->word);
        break;
    case kOpFollow:
        for (unsigned r = 0; r < map.rows; r++) {
            int empty = 1;
            for (unsigned i = 0; i < map.count && empty; i++)
                empty = !(ppu->vram[CellAddress(&map, map.first + i, r)] & 0x3ff);
            if (!empty)
                continue;
            for (unsigned i = 1; i <= kMarginCols; i++) {
                PutCell(&map, map.first + map.cols - i, r, 0);
                PutCell(&map, map.first + map.count - 1 + i, r, 0);
            }
        }
        break;
    }
}

void Cv4MarginFillApply(Ppu *ppu, const char *scene)
{
    if (!ppu)
        return;
    ppu->renderVram = NULL;
    if (!ppu->extraLeftRight || !scene)
        return;   /* 4:3 renders the guest VRAM, bit for bit */
    LoadRulesIfChanged();
    int copied = 0;
    for (int i = 0; i < g_rule_count; i++) {
        if (strcmp(g_rules[i].scene, scene))
            continue;
        if (!copied) {
            memcpy(g_render_vram, ppu->vram, sizeof(g_render_vram));
            copied = 1;
        }
        ApplyRule(ppu, &g_rules[i]);
    }
    if (copied)
        ppu->renderVram = g_render_vram;
}
