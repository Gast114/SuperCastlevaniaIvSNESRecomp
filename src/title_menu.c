/* NEW GAME+ as a native entry of the title menu.
 *
 * The retail menu (init $00:9385, input $00:93EC, confirmation $00:86F4)
 * draws text through the game's descriptor routine $00:9051 and moves a heart
 * cursor over three entries held in $1E02 (0 START, 1 CONTINUE, 2 OPTION).
 * These byte-checked patches give it a fourth entry, index 3 = NEW GAME+,
 * shown directly under START, and drop the PLAY SELECT heading so the four
 * entries keep the retail spacing without moving anything else:
 *
 *      row 17  START              (retail: PLAY SELECT; START was row 19)
 *      row 19  NEW GAME+          (new)
 *      row 21  CONTINUE
 *      row 23  OPTION
 *      row 25  TM AND (c) 1991 KONAMI CO., LTD. / LICENSED BY NINTENDO
 *
 * Everything new lives in the unused tail of bank $01 ($01:FF24-$01:FFFF,
 * all $FF in the retail ROM): the text and cursor descriptors, the cursor
 * and blink tables, the up/down order of the four entries, and a '+' glyph
 * in the game's font style. The glyph reaches VRAM through the game's own
 * asset loader ($02:80E8) as one more entry of the title's load list, packed
 * as a literal run of its LZ format ($02:863D), into the unused BG3 font tile
 * $33. All patched routines run in the interpreter (008607-00BB39 is
 * lle_only in src/gen/program_manifest.json), so they read cart->rom.
 *
 * The confirmation still branches on the retail values; campaign2.c turns a
 * confirmed 3 into START plus a second-quest request before $00:8715 reads it.
 */
#include "title_menu.h"

#include <stdio.h>
#include <string.h>

#include "guarded_patch.h"
#include "snes/cart.h"
#include "snes/snes.h"

extern Snes *g_snes;

/* Font tile numbers of the BG3 text font: A-Z = $0B-$24, space = $00. */
#define SP 0x00
#define A_ 0x0b
#define E_ 0x0f
#define G_ 0x11
#define M_ 0x17
#define N_ 0x18
#define R_ 0x1c
#define S_ 0x1d
#define T_ 0x1e
#define W_ 0x21
#define HEART 0x27   /* the menu cursor */
#define PLUS 0x33    /* new glyph, an unused tile of the font */
#define NEXT 0xfe    /* descriptor: next VRAM address follows */
#define END 0xff
#define LE(v) ((v) & 0xff), ((v) >> 8)

/* BG3 tilemap word addresses (map $5800, 32 columns). */
#define CELL(row, col) (0x5800 + (row) * 32 + (col))
enum { kRowStart = 17, kRowNewGame = 19, kRowContinue = 21, kRowOption = 23 };

enum {
    kDataBase = 0xff24,                      /* $01:FF24 */
    kCursors = kDataBase,                    /* 4 x 16 bytes */
    kCursorTable = kCursors + 64,            /* $01:FF64 */
    kBlinkTable = kCursorTable + 8,          /* $01:FF6C */
    kUpTable = kBlinkTable + 8,              /* $01:FF74 */
    kDownTable = kUpTable + 8,               /* $01:FF7C */
    kTextStart = kDownTable + 8,             /* $01:FF84 */
    kTextStartNewGame = kTextStart + 8,      /* $01:FF8C */
    kTextNewGame = kTextStartNewGame + 8,    /* $01:FF94 */
    kPlusGlyph = kTextNewGame + 12,          /* $01:FFA0 */
    kTitleAssets = kPlusGlyph + 19,          /* $01:FFB3 */
    kDataEnd = kTitleAssets + 44,            /* $01:FFDF */
};

/* One cursor descriptor per entry: the heart on its row, blanks on the
 * other three (the retail ones do the same for three rows). */
#define CURSOR(r0, r1, r2, r3) \
    LE(CELL(r0, 10)), HEART, NEXT, LE(CELL(r1, 10)), SP, NEXT, \
    LE(CELL(r2, 10)), SP, NEXT, LE(CELL(r3, 10)), SP, END

static const uint8_t kMenuData[] = {
    /* kCursors: START, CONTINUE, OPTION, NEW GAME+ (index order) */
    CURSOR(kRowStart, kRowNewGame, kRowContinue, kRowOption),
    CURSOR(kRowContinue, kRowStart, kRowNewGame, kRowOption),
    CURSOR(kRowOption, kRowStart, kRowNewGame, kRowContinue),
    CURSOR(kRowNewGame, kRowStart, kRowContinue, kRowOption),
    /* kCursorTable, indexed by $1E02 */
    LE(kCursors), LE(kCursors + 16), LE(kCursors + 32), LE(kCursors + 48),
    /* kBlinkTable: the confirmed entry blinks; CONTINUE/OPTION stay retail */
    LE(kTextStart), LE(0x857f), LE(0x858a), LE(kTextNewGame),
    /* kUpTable / kDownTable: on-screen order START, NEW GAME+, CONTINUE,
     * OPTION, wrapping like the retail menu */
    LE(2), LE(3), LE(1), LE(0),
    LE(3), LE(2), LE(0), LE(1),
    /* kTextStart */
    LE(CELL(kRowStart, 12)), S_, T_, A_, R_, T_, END,
    /* kTextStartNewGame: START, then falls through into kTextNewGame */
    LE(CELL(kRowStart, 12)), S_, T_, A_, R_, T_, NEXT,
    /* kTextNewGame */
    LE(CELL(kRowNewGame, 12)), N_, E_, W_, SP, G_, A_, M_, E_, PLUS, END,
    /* kPlusGlyph: total length, one literal run of 16 bytes, 2bpp tile.
     * Drawn like the font: 1 = face, 2 = edge, 3 = shadow.
     *   ........   ...223..   ...113..   .1111113
     *   ..311333   ...113..   ...223..   ...33...   */
    LE(19), 0x80 | 16,
    0x00, 0x00, 0x04, 0x1c, 0x1c, 0x04, 0x7f, 0x01,
    0x3f, 0x27, 0x1c, 0x04, 0x04, 0x1c, 0x18, 0x18,
    /* kTitleAssets: the retail list at $01:B5A7 plus the glyph, after the
     * punctuation chunk that also covers tiles $30-$3F */
    0x00, 0x00,
    LE(0x2000), 0x00, 0x80, 0x1b,
    LE(0x3000), 0x40, 0x99, 0x1b,
    LE(0x4000), 0x82, 0xb6, 0x1b,
    LE(0x5000), 0xc9, 0x8d, 0x07,
    LE(0x5180), 0xf4, 0x8f, 0x07,
    LE(0x5000 + PLUS * 8), LE(kPlusGlyph), 0x01,
    LE(0x0000), 0xe6, 0xc1, 0x1b,
    LE(0x1000), 0x4d, 0xc4, 0x1b,
    0xff, 0xff,
};
_Static_assert(sizeof(kMenuData) == kDataEnd - kDataBase, "menu data layout");
_Static_assert(kDataEnd <= 0x10000, "menu data must stay in bank $01");

typedef struct MenuPatch {
    uint32_t pc;              /* file offset (LoROM) */
    const char *name;
    uint8_t size;
    uint8_t original[27];
    uint8_t patched[27];
} MenuPatch;

#define PC(bank, addr) (((uint32_t)(bank) << 15) | ((addr) & 0x7fff))

static const MenuPatch kPatches[] = {
    { PC(0x00, 0x939a), "NEW GAME+: title asset list with the '+' glyph", 2,
      { LE(0xb5a7) }, { LE(kTitleAssets) } },
    /* The heading descriptor $01:8531 continues ($FE) with the copyright
     * lines at $01:853F; start drawing there. */
    { PC(0x00, 0x93b8), "NEW GAME+: no PLAY SELECT heading", 2,
      { LE(0x8531) }, { LE(0x853f) } },
    { PC(0x00, 0x93bf), "NEW GAME+: draw START and NEW GAME+", 2,
      { LE(0x8577) }, { LE(kTextStartNewGame) } },
    { PC(0x00, 0x9428), "NEW GAME+: four-entry cursor table", 2,
      { LE(0x8b2b) }, { LE(kCursorTable) } },
    { PC(0x00, 0x8706), "NEW GAME+: four-entry blink table", 2,
      { LE(0x82c6) }, { LE(kBlinkTable) } },
    /* $00:9407-$00:9421: DEC/INC with a wrap at 3 becomes a table step.
     * DB is $01 here (the cursor table read at $00:9427 relies on it). */
    { PC(0x00, 0x9407), "NEW GAME+: menu order up/down", 27,
      { 0xce, 0x02, 0x1e, 0x10, 0x16, 0xa9, 0x02, 0x00, 0x8d, 0x02, 0x1e,
        0x80, 0x0e, 0xee, 0x02, 0x1e, 0xad, 0x02, 0x1e, 0xc9, 0x03, 0x00,
        0x90, 0x03, 0x9c, 0x02, 0x1e },
      { 0xad, 0x02, 0x1e,             /* 9407 LDA $1E02      (Up)        */
        0x0a, 0xaa,                   /* 940A ASL : TAX                  */
        0xbd, LE(kUpTable),           /* 940C LDA up,X                   */
        0x80, 0x0b,                   /* 940F BRA $941C                  */
        0xea, 0xea, 0xea,             /* 9411                            */
        0xad, 0x02, 0x1e,             /* 9414 LDA $1E02      (Down/Sel.) */
        0x0a, 0xaa,                   /* 9417 ASL : TAX                  */
        0xbd, LE(kDownTable),         /* 9419 LDA down,X                 */
        0x8d, 0x02, 0x1e,             /* 941C STA $1E02                  */
        0xea, 0xea, 0xea } },         /* 941F                            */
};
enum { kPatchCount = sizeof(kPatches) / sizeof(kPatches[0]) + 1 };

static GuardedPatch g_patches[kPatchCount];
static const uint8_t *g_bound_rom;

void Cv4TitleMenuBind(void)
{
    if (!g_snes || !g_snes->cart || !g_snes->cart->rom ||
        g_bound_rom == g_snes->cart->rom)
        return;
    for (unsigned i = 0; i < kPatchCount; ++i) {
        if (g_patches[i].target) {
            (void)guarded_patch_revert(&g_patches[i]);
            guarded_patch_unregister(&g_patches[i]);
        }
        memset(&g_patches[i], 0, sizeof(g_patches[i]));
    }
    g_bound_rom = g_snes->cart->rom;
    uint8_t *rom = g_snes->cart->rom;
    size_t size = (size_t)g_snes->cart->romSize;

    /* The free tail of bank $01 first: if it is not free, nothing else is
     * applied either and the retail menu stays as it is. */
    static uint8_t free_bytes[sizeof(kMenuData)];
    memset(free_bytes, 0xff, sizeof(free_bytes));
    uint32_t data_pc = PC(0x01, kDataBase);
    GuardedPatchStatus status = size >= data_pc + sizeof(kMenuData)
        ? guarded_patch_init(&g_patches[0], "NEW GAME+: menu data in $01:FF24",
                             rom + data_pc, sizeof(kMenuData), free_bytes, kMenuData)
        : kGuardedPatch_Invalid;
    for (unsigned i = 0; status == kGuardedPatch_Ok && i < kPatchCount; ++i) {
        if (i > 0) {
            const MenuPatch *p = &kPatches[i - 1];
            status = size >= p->pc + p->size
                ? guarded_patch_init(&g_patches[i], p->name, rom + p->pc, p->size,
                                     p->original, p->patched)
                : kGuardedPatch_Invalid;
        }
        if (status == kGuardedPatch_Ok)
            status = guarded_patch_register(&g_patches[i]);
        if (status == kGuardedPatch_Ok)
            status = guarded_patch_apply(&g_patches[i]);
        if (status != kGuardedPatch_Ok)
            fprintf(stderr, "[title] patch refused: %s: %s\n",
                    g_patches[i].name ? g_patches[i].name : "?",
                    guarded_patch_status_name(status));
    }
    if (status != kGuardedPatch_Ok) {
        /* All or nothing: a partial menu would be worse than the retail one. */
        for (unsigned i = 0; i < kPatchCount; ++i) {
            if (g_patches[i].target) {
                (void)guarded_patch_revert(&g_patches[i]);
                guarded_patch_unregister(&g_patches[i]);
            }
            memset(&g_patches[i], 0, sizeof(g_patches[i]));
        }
    }
}
