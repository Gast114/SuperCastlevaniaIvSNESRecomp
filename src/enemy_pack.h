#pragma once
#include <stdint.h>
struct Ppu;
/* Immutable throughout one rendered field. Coordinates are native pixels;
 * pixels are ARGB32 at image resolution (which need not be an integer scale). */
typedef struct Cv4EnemyHdFrame {
  const uint32_t *pixels;
  int x, y, width, height, displayWidth, displayHeight;
  unsigned flip;
  uint16_t priority, actorType, pose;
  uint8_t oamSlot;
  uint64_t revision;
  const char *id;
} Cv4EnemyHdFrame;
#ifdef __cplusplus
extern "C" {
#endif
void Cv4EnemyInit(const uint8_t *rom, unsigned size);
void Cv4EnemyBegin(struct Ppu *ppu, const uint8_t *ram);
void Cv4EnemyEnd(struct Ppu *ppu);
const Cv4EnemyHdFrame *Cv4EnemyHd(unsigned index);
unsigned Cv4EnemyHdCount(void);
const char *Cv4EnemyStatus(void);
int Cv4EnemyCapturing(void);
const char *Cv4EnemySelection(void);
const char *Cv4EnemyObservation(void);
int Cv4EnemyWorkshop(void);
/* capture on/off, reload, pack <directory>, status; no gameplay writes. */
int Cv4EnemyCommand(const char *command);
#ifdef __cplusplus
}
#endif
