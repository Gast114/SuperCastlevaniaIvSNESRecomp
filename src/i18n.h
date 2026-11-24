#pragma once

#ifdef __cplusplus
extern "C" {
#endif

/* Initialize localization by scanning assets/locales/*.json.
   preferred_code may be NULL or empty to default to "de" (or "en" if absent). */
void Cv4I18nInit(const char *preferred_code);

/* Translate a key in the active language, falling back to English, then key itself. */
const char *Cv4Tr(const char *key);

/* Enumerate all discovered languages (auto-discovered from assets/locales/*.json). */
int Cv4I18nCount(void);
const char *Cv4I18nCode(int index);
const char *Cv4I18nName(int index);
int Cv4I18nCurrentIndex(void);
const char *Cv4I18nCurrentCode(void);

/* Switch active language by ISO code (e.g. "en", "de", "es", "fr", ...). */
void Cv4I18nSetLanguage(const char *code);

#ifdef __cplusplus
}
#endif
