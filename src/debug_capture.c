#include "debug_capture.h"

#include <stdio.h>
#include <stdlib.h>

#include "common_rtl.h"
#include "desktop/config.h"
#include "game_rtl.h"
#include "host_main.h"
#include "snes/ppu.h"
#include "third_party/stb_image_write.h"

extern Ppu *g_ppu;
extern unsigned char g_ram[0x20000];

int Cv4CaptureFieldPng(const char *path, char *error, size_t capacity)
{
    int w = snesrecomp_desktop_frame_width(), h = snesrecomp_desktop_frame_height();
    if (!g_ppu || !g_ppu->renderBuffer || w <= 0 || h <= 0 || !path[0]) {
        snprintf(error, capacity, "no frame to capture (or empty path)");
        return 0;
    }
    uint8_t *rgb = malloc((size_t)w * h * 3);
    if (!rgb) {
        snprintf(error, capacity, "out of memory");
        return 0;
    }
    /* renderBuffer is 0x00RRGGBB. */
    for (int y = 0; y < h; y++) {
        const uint32_t *row = (const uint32_t *)(g_ppu->renderBuffer + (size_t)y * g_ppu->renderPitch);
        for (int x = 0; x < w; x++) {
            uint8_t *out = &rgb[((size_t)y * w + x) * 3];
            out[0] = (uint8_t)(row[x] >> 16);
            out[1] = (uint8_t)(row[x] >> 8);
            out[2] = (uint8_t)row[x];
        }
    }
    int ok = stbi_write_png(path, w, h, 3, rgb, w * 3);
    free(rgb);
    if (!ok)
        snprintf(error, capacity, "cannot write %s", path);
    else
        snprintf(error, capacity, "%dx%d", w, h);
    return ok;
}

int Cv4CaptureVideoDump(const char *path)
{
    FILE *f = path[0] && g_ppu ? fopen(path, "wb") : NULL;
    if (!f)
        return 0;
    fwrite(g_ppu->vram, 1, sizeof(g_ppu->vram), f);
    fwrite(g_ppu->cgram, 1, sizeof(g_ppu->cgram), f);
    fwrite(g_ppu->oam, 1, sizeof(g_ppu->oam), f);
    fwrite(g_ppu->highOam, 1, sizeof(g_ppu->highOam), f);
    return fclose(f) == 0;
}

int Cv4CaptureWram(const char *path)
{
    FILE *f = path[0] ? fopen(path, "wb") : NULL;
    if (!f)
        return 0;
    fwrite(g_ram, 1, sizeof(g_ram), f);
    return fclose(f) == 0;
}

size_t Cv4CapturePpuJson(char *out, size_t capacity)
{
    if (!g_ppu || !capacity)
        return 0;
    size_t n = (size_t)snprintf(out, capacity, "{\"bgmode\":%u,\"layers\":[",
                                (unsigned)g_ppu->bgmode);
    for (int i = 0; i < 4 && n < capacity; i++)
        n += (size_t)snprintf(out + n, capacity - n,
            "%s{\"map\":%u,\"tiles\":%u,\"wide\":%d,\"tall\":%d,\"big\":%d,\"h\":%u,\"v\":%u}",
            i ? "," : "", (unsigned)PPU_bgTilemapAdr(g_ppu, i), (unsigned)PPU_bgTileAdr(g_ppu, i),
            PPU_bgTilemapWider(g_ppu, i) != 0, PPU_bgTilemapHigher(g_ppu, i) != 0,
            PPU_bigTiles(g_ppu, i) != 0, (unsigned)g_ppu->hScroll[i],
            (unsigned)g_ppu->vScroll[i]);
    if (n < capacity)
        n += (size_t)snprintf(out + n, capacity - n,
                              "],\"extra\":%u,\"left\":%u,\"right\":%u,\"main\":%u,\"sub\":%u,\"math\":%u,\"color_control\":%u,\"m7\":[%d,%d,%d,%d,%d,%d,%d,%d],\"m7sel\":%u}",
                              (unsigned)g_ppu->extraLeftRight, (unsigned)g_ppu->extraLeftCur,
                              (unsigned)g_ppu->extraRightCur, (unsigned)g_ppu->screenEnabled[0],
                              (unsigned)g_ppu->screenEnabled[1], (unsigned)g_ppu->cgadsub, (unsigned)g_ppu->cgwsel,
                              g_ppu->m7matrix[0],g_ppu->m7matrix[1],g_ppu->m7matrix[2],g_ppu->m7matrix[3],
                              g_ppu->m7matrix[4],g_ppu->m7matrix[5],g_ppu->m7matrix[6],g_ppu->m7matrix[7],g_ppu->m7sel);
    return n < capacity ? n : capacity - 1;
}

int Cv4CaptureSaveState(const char *path)
{
    return path[0] && RtlSaveSnapshot(path);
}

int Cv4CaptureWidescreenOn(void) { return g_config.widescreen != 0; }
int Cv4CaptureHasPanelPresenter(void) { return g_config.output_method == kOutputMethod_OpenGL; }
unsigned Cv4CaptureFrameNumber(void) { return GameFrameNumber(); }
