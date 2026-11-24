#pragma once

#ifdef __cplusplus
extern "C" {
#endif

/* Draw the collapsible Level & Section Warp panel inside the ESC menu.
   ui_ptr is RecompRuntimeUi* so clicking a section closes the menu after warping. */
void Cv4StageWarpDraw(void *ui_ptr);

/* Release cached OpenGL thumbnail textures on shutdown. */
void Cv4StageWarpShutdown(void);

#ifdef __cplusplus
}
#endif
