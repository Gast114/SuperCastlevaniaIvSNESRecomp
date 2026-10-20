#pragma once
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
struct Ppu;
void Cv4HdRenderBegin(struct Ppu *ppu);
void Cv4HdRenderLine(struct Ppu *ppu, int line);
void Cv4HdRenderEnd(void);
void Cv4HdRenderShutdown(void);
int Cv4HdEnabled(void);
void Cv4HdEnable(int enabled);
int Cv4HdScale(void);
void Cv4HdSetScale(int scale);
unsigned Cv4HdLayerMask(void);
void Cv4HdSetLayerMask(unsigned mask);
int Cv4HdLoadPack(const char *directory);
const char *Cv4HdPackPath(void);
const char *Cv4HdStatus(void);
unsigned Cv4HdPackTiles(void);
int Cv4HdPackScale(void);
unsigned Cv4HdReplacedPixels(void);
uint64_t Cv4HdFrameChecksum(void);
int Cv4HdPresentationScale(void);
void Cv4HdPresent(uint8_t *dst, size_t pitch, int width, int height, int scale);
int Cv4HdScreenshot(const char *path);
#ifdef __cplusplus
}
#endif
