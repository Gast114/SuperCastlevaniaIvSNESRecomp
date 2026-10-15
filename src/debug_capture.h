#pragma once
/* Capture helpers shared by the Lua automation commands and debug markers.
 * All of them read host-side copies only; none touches guest state. */
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* The last rasterized field, widescreen margins included, as RGB PNG. */
int Cv4CaptureFieldPng(const char *path, char *error, size_t capacity);
/* VRAM, CGRAM, OAM and the OAM high table, raw little endian:
 * 0x10000 + 0x200 + 0x200 + 0x20 bytes (tools/re/render_map.py reads it). */
int Cv4CaptureVideoDump(const char *path);
/* The 128 KB of WRAM. */
int Cv4CaptureWram(const char *path);
/* BG mode, per-layer map/tile bases, sizes and scroll, widescreen margins,
 * as one JSON object. Returns the length written (0 without a PPU). */
size_t Cv4CapturePpuJson(char *out, size_t capacity);
/* A save state written to `path` (outside the numbered slots). */
int Cv4CaptureSaveState(const char *path);

/* Host facts for C++ callers, which cannot include the C-only host headers. */
int Cv4CaptureWidescreenOn(void);
int Cv4CaptureHasPanelPresenter(void);   /* OpenGL presenter: ImGui panels */
unsigned Cv4CaptureFrameNumber(void);

#ifdef __cplusplus
}
#endif
