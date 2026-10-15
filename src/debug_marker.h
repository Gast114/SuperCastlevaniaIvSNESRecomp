#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* SnesDesktopHostGame.debug_marker_* hooks; see debug_marker.cpp. */
int Cv4DebugMarkerOpen(void);
int Cv4DebugMarkerIsOpen(void);
void Cv4DebugMarkerEvent(const void *sdl_event);
void Cv4DebugMarkerPump(uint32_t pad_pressed);
/* The note panel; called from the ImGui overlay while a marker is open. */
void Cv4DebugMarkerDraw(void);
#ifdef __cplusplus
}
#endif
