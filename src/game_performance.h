#ifndef CV4_GAME_PERFORMANCE_H
#define CV4_GAME_PERFORMANCE_H
#ifdef __cplusplus
extern "C" {
#endif
int Cv4FastRomEnabled(void);
void Cv4SetFastRom(int enabled);
int Cv4CpuTimingMode(void);
void Cv4SetCpuTimingMode(int mode);
void Cv4PerformanceBeforeFrame(void);
#ifdef __cplusplus
}
#endif
#endif
