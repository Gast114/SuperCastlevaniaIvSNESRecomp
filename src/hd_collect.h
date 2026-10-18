#pragma once
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif
struct Ppu;

/* Per-scanline PPU registers, recorded on every frame (a few bytes per line)
 * for layer reconstruction with HDMA parallax. Windows, mosaic, colour math,
 * and mid-frame VRAM/CGRAM changes are not recorded in this initial format.
 * Layout of one record, little endian, 32 bytes:
 *   u8 valid, inidisp, obsel, bgmode, bgXsc[4], main, sub, 0, 0,
 *   u16 bgTileAdr, hScroll[4], vScroll[4], 0
 * Record i belongs to ppu_runLine(i): scanline i, screen row i - 1. */
typedef struct Cv4HdLine {
    uint8_t valid, inidisp, obsel, bgmode, bgXsc[4], main_screen, sub_screen, pad0[2];
    uint16_t bg_tile_adr, h_scroll[4], v_scroll[4], pad1;
} Cv4HdLine;
enum { kCv4HdLines = 225 };

/* Before ppu_runLine(line): the registers that line is drawn with. */
void Cv4HdRecordLine(const struct Ppu *ppu, int line);
/* After the field is drawn. Collects graphics when collecting is on. */
void Cv4HdFrame(const struct Ppu *ppu, const char *scene, unsigned block);
/* The last frame's line records (kCv4HdLines of them). */
const Cv4HdLine *Cv4HdLines(void);

/* Collector switch (persisted in hd_dump/collect.txt) and its counters. */
int Cv4HdCollecting(void);
void Cv4HdSetCollecting(int enabled);
void Cv4HdStats(unsigned *tiles, unsigned *captures, unsigned *pending, unsigned *errors);
/* Write everything still queued (at shutdown). */
void Cv4HdFlush(void);
#ifdef __cplusplus
}
#endif
