#pragma once
#ifdef __cplusplus
extern "C" {
#endif
/* The scene the guest shows now ("title", "prologue", "gate", "level") or
 * NULL for anything else; see Cv4CurrentScene in main.c. */
const char *Cv4CurrentSceneName(void);
#ifdef __cplusplus
}
#endif
