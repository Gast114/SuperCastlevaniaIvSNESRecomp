#pragma once
#include <stddef.h>
struct Ppu;
#ifdef __cplusplus
extern "C" {
#endif
int Cv4LevelLoad(const char *path,char *result,size_t capacity);
void Cv4LevelBeforeFrame(void);
void Cv4LevelBeforeDraw(struct Ppu *ppu);
void Cv4LevelBeforeLine(struct Ppu *ppu,int line);
void Cv4LevelTrack(struct Ppu *ppu);
void Cv4LevelRenderLine(struct Ppu *ppu,int line);
unsigned Cv4LevelRoom(void);
void Cv4LevelStatus(char *result,size_t capacity);
void Cv4LevelReset(void);
/* Per-family original graphics for custom projects, independent of native OBJ VRAM. */
int Cv4LevelSpritePixel(unsigned type,unsigned variant,unsigned actualAdd,unsigned attr,int size,int x,int y,unsigned *index,unsigned *rgba);
void Cv4LevelSprites(struct Ppu *ppu);
#ifdef __cplusplus
}
#endif
