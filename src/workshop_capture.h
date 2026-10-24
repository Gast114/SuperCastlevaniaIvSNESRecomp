#pragma once
struct Ppu;
#ifdef __cplusplus
extern "C" {
#endif
void Cv4WorkshopCaptureBegin(struct Ppu *ppu, const unsigned char *ram);
void Cv4WorkshopCaptureLine(struct Ppu *ppu, int line);
int Cv4WorkshopCaptureSave(const char *path);
#ifdef __cplusplus
}
#endif
