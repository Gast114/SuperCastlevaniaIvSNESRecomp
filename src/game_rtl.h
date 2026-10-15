#ifndef GAME_RTL_H
#define GAME_RTL_H

#include "common_cpu_infra.h"

/* One frame of Super Castlevania IV. See game_rtl.c — this is the port. */
void GameRunOneFrame(void);
void GameDrawPpuFrame(void);
void GameSessionReset(void);
/* Guest frames run since boot (restored by save states). */
unsigned GameFrameNumber(void);

extern const RtlGameInfo kGameInfo;

#endif /* GAME_RTL_H */
