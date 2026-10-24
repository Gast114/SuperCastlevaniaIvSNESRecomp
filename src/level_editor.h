#pragma once
#include <stddef.h>
struct Ppu;
#ifdef __cplusplus
extern "C" {
#endif
int Cv4LevelLoad(const char *path,char *result,size_t capacity);
void Cv4LevelBeforeFrame(void);
void Cv4LevelBeforeDraw(struct Ppu *ppu);
unsigned Cv4LevelRoom(void);
void Cv4LevelReset(void);
#ifdef __cplusplus
}
#endif
