#pragma once
#include "snes/ppu.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Apply the designed margin columns for `scene` (a name used in
 * assets/widescreen_margins.txt) to a render-only copy of VRAM, or render
 * from the guest VRAM again when the scene has none. Call once per simulated
 * frame, after the guest frame and before the PPU draws it. */
void Cv4MarginFillApply(Ppu *ppu, const char *scene);

#ifdef __cplusplus
}
#endif
