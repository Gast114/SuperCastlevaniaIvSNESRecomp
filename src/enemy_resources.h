#pragma once
#include <stddef.h>
struct Ppu;
#ifdef __cplusplus
extern "C" {
#endif
/* Atomic graphics-only import. Does not load a level, actors, CPU or save state. */
int Cv4EnemyResources(struct Ppu *ppu,unsigned char *ram,const char *path,char *error,size_t capacity);
#ifdef __cplusplus
}
#endif
