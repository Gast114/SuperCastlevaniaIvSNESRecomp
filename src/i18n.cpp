#include "i18n.h"
#include "character_json.h"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <map>
#include <string>
#include <vector>

namespace {

struct LocalePack {
  std::string code;
  std::string name;
  std::map<std::string, std::string> strings;
};

static std::vector<LocalePack> g_locales;
static int g_current = 0;
static int g_english = -1;
static bool g_inited = false;

static std::filesystem::path FindLocalesDir() {
  const char *candidates[] = {
    "assets/locales",
    "../assets/locales",
    "../../assets/locales",
  };
  for (const char *c : candidates) {
    std::filesystem::path p(c);
    if (std::filesystem::is_directory(p)) return p;
  }
  return "assets/locales";
}

static void LoadLocaleFile(const std::filesystem::path &path) {
  try {
    std::ifstream f(path);
    if (!f) return;
    std::string data((std::istreambuf_iterator<char>(f)), {});
    auto root = character_json::Reader(data).read();
    if (root.kind != '{') return;
    LocalePack pack;
    pack.code = path.stem().string();
    pack.name = pack.code;
    for (const auto &kv : root.object) {
      if (kv.second.kind != 's') continue;
      if (kv.first == "_code") pack.code = kv.second.text;
      else if (kv.first == "_name") pack.name = kv.second.text;
      else pack.strings[kv.first] = kv.second.text;
    }
    if (!pack.code.empty()) {
      g_locales.push_back(std::move(pack));
    }
  } catch (...) {
    // Ignore malformed locale files cleanly
  }
}

static void EnsureFallbackLocale() {
  if (!g_locales.empty()) return;
  LocalePack en;
  en.code = "en";
  en.name = "English";
  g_locales.push_back(std::move(en));
}

} // namespace

extern "C" void Cv4I18nInit(const char *preferred_code) {
  g_locales.clear();
  g_current = 0;
  g_english = -1;

  std::filesystem::path dir = FindLocalesDir();
  std::error_code ec;
  if (std::filesystem::is_directory(dir, ec)) {
    std::vector<std::filesystem::path> files;
    for (const auto &entry : std::filesystem::directory_iterator(dir, ec)) {
      if (entry.is_regular_file(ec) && entry.path().extension() == ".json") {
        files.push_back(entry.path());
      }
    }
    std::sort(files.begin(), files.end());
    for (const auto &f : files) LoadLocaleFile(f);
  }
  EnsureFallbackLocale();

  // Order nicely: en, de, es, fr first, then any additional community languages alphabetically
  auto rank = [](const std::string &c) -> int {
    if (c == "de") return 0;
    if (c == "en") return 1;
    if (c == "es") return 2;
    if (c == "fr") return 3;
    return 10;
  };
  std::stable_sort(g_locales.begin(), g_locales.end(), [&](const LocalePack &a, const LocalePack &b) {
    int ra = rank(a.code), rb = rank(b.code);
    return ra != rb ? ra < rb : a.name < b.name;
  });

  for (int i = 0; i < static_cast<int>(g_locales.size()); ++i) {
    if (g_locales[i].code == "en") g_english = i;
  }

  g_inited = true;
  if (preferred_code && *preferred_code) {
    Cv4I18nSetLanguage(preferred_code);
  } else {
    Cv4I18nSetLanguage("de");
  }
}

extern "C" const char *Cv4Tr(const char *key) {
  if (!key) return "";
  if (!g_inited) Cv4I18nInit(nullptr);
  if (g_current >= 0 && g_current < static_cast<int>(g_locales.size())) {
    const auto &m = g_locales[g_current].strings;
    auto it = m.find(key);
    if (it != m.end()) return it->second.c_str();
  }
  if (g_english >= 0 && g_english < static_cast<int>(g_locales.size())) {
    const auto &m = g_locales[g_english].strings;
    auto it = m.find(key);
    if (it != m.end()) return it->second.c_str();
  }
  return key;
}

extern "C" int Cv4I18nCount(void) {
  if (!g_inited) Cv4I18nInit(nullptr);
  return static_cast<int>(g_locales.size());
}

extern "C" const char *Cv4I18nCode(int index) {
  if (!g_inited) Cv4I18nInit(nullptr);
  if (index < 0 || index >= static_cast<int>(g_locales.size())) return "en";
  return g_locales[index].code.c_str();
}

extern "C" const char *Cv4I18nName(int index) {
  if (!g_inited) Cv4I18nInit(nullptr);
  if (index < 0 || index >= static_cast<int>(g_locales.size())) return "English";
  return g_locales[index].name.c_str();
}

extern "C" int Cv4I18nCurrentIndex(void) {
  if (!g_inited) Cv4I18nInit(nullptr);
  return g_current;
}

extern "C" const char *Cv4I18nCurrentCode(void) {
  return Cv4I18nCode(Cv4I18nCurrentIndex());
}

extern "C" void Cv4I18nSetLanguage(const char *code) {
  if (!g_inited) Cv4I18nInit(nullptr);
  if (!code || !*code) return;
  for (int i = 0; i < static_cast<int>(g_locales.size()); ++i) {
    if (g_locales[i].code == code) {
      g_current = i;
      return;
    }
  }
}
