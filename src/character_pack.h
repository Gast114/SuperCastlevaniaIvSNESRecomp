#pragma once
#include <stdint.h>
struct Ppu;
typedef struct Cv4CharacterHdFrame {
  const uint32_t *pixels;
  int x, y, width, height, scale;
  uint64_t revision;
} Cv4CharacterHdFrame;
#ifdef __cplusplus
extern "C" {
#endif
void Cv4CharacterInit(const uint8_t *rom, unsigned size);
void Cv4CharacterBeforeFrame(void);
void Cv4CharacterBegin(struct Ppu *ppu, const uint8_t *ram);
void Cv4CharacterEnd(struct Ppu *ppu);
void Cv4CharacterEditor(void);
const Cv4CharacterHdFrame *Cv4CharacterHd(void);
const char *Cv4CharacterPose(void);
#ifdef __cplusplus
}
#endif
