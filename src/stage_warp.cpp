#include "stage_warp.h"
#include "runtime_settings_imgui.h"
#include "character_json.h"
#include "recomp_runtime_ui.h"
#include "imgui.h"
#include "third_party/stb_image.h"

#include <SDL3/SDL_opengl.h>

extern "C" {
#include "snes/snes.h"
extern Snes *g_snes;
}

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <map>
#include <string>
#include <vector>

namespace {

struct WarpRoom {
  int room = 0;
  int stage = 1;
  int section = 1;
  bool boss = false;
  std::string stage_name;
  std::string label;
  std::string image;
  GLuint tex = 0;
  int tex_w = 0;
  int tex_h = 0;
  bool tex_tried = false;
};

static std::vector<WarpRoom> g_rooms;
static bool g_loaded = false;
static std::filesystem::path g_thumb_dir;
static bool g_only_bosses = false;
static char g_search[64] = "";
static int g_expand_cmd = 0; // 0 = none, +1 = expand all, -1 = collapse all

static float S(float v) { return v * Cv4RuntimeUiScale(); }

static std::string ToLower(const std::string &s) {
  std::string out = s;
  for (char &c : out) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
  return out;
}

static std::filesystem::path FindThumbDir() {
  const char *candidates[] = {
    "warp_thumbs",
    "../warp_thumbs",
    "../../warp_thumbs",
  };
  for (const char *c : candidates) {
    std::filesystem::path p(c);
    if (std::filesystem::is_directory(p)) return p;
  }
  return "warp_thumbs";
}

static void PopulateFallbackRooms() {
  static const char *kStageNames[12] = {
    "",
    "Stage 1 · Burgtor & Stallungen",
    "Stage 2 · Wald & Sumpf",
    "Stage 3 · Höhlen & Wasserfall",
    "Stage 4 · Drehturm & Gewölbe",
    "Stage 5 · Burghof & Brücke",
    "Stage 6 · Großer Ballsaal",
    "Stage 7 · Bibliothek",
    "Stage 8 · Kerker & Folterkammer",
    "Stage 9 · Schatzkammer",
    "Stage 10 · Uhrturm",
    "Stage 11 · Bergfried & Dracula",
  };
  struct Range { int st, lo, hi; };
  static const Range kRanges[] = {
    {1,0,7},{2,8,12},{3,13,18},{4,19,27},{5,28,29},
    {6,30,36},{7,37,43},{8,44,48},{9,49,58},{10,59,62},{11,63,67}
  };
  static const std::map<int, const char *> kBosses = {
    {7,"Boss: Rowdain"},{12,"Boss: Medusa"},{18,"Boss: Orphic Vipers"},
    {23,"Boss: Puwexyl"},{27,"Boss: Koranot"},{36,"Boss: Dancing Specters"},
    {43,"Boss: Sir Grakul"},{48,"Boss: Frankenstein"},{53,"Boss: Zapf Bat"},
    {58,"Boss: Akmodan II"},{64,"Boss: Slogra"},{65,"Boss: Gaibon"},
    {66,"Boss: Death"},{67,"Final Boss: Dracula"},
  };
  g_rooms.clear();
  for (const auto &rg : kRanges) {
    for (int r = rg.lo; r <= rg.hi; ++r) {
      WarpRoom wr;
      wr.room = r;
      wr.stage = rg.st;
      wr.section = (r - rg.lo) + 1;
      wr.stage_name = kStageNames[rg.st];
      auto it = kBosses.find(r);
      wr.boss = (it != kBosses.end());
      char buf[64];
      if (rg.st >= 10) std::snprintf(buf, sizeof(buf), "%X-%d", rg.st, wr.section);
      else std::snprintf(buf, sizeof(buf), "%d-%d", rg.st, wr.section);
      wr.label = buf;
      if (wr.boss) { wr.label += " · "; wr.label += it->second; }
      char img[32];
      std::snprintf(img, sizeof(img), "room_%02d.png", r);
      wr.image = img;
      g_rooms.push_back(std::move(wr));
    }
  }
}

static void EnsureLoaded() {
  if (g_loaded) return;
  g_loaded = true;
  g_thumb_dir = FindThumbDir();
  std::filesystem::path meta = g_thumb_dir / "rooms.json";
  if (std::filesystem::is_regular_file(meta)) {
    try {
      std::ifstream f(meta);
      std::string text((std::istreambuf_iterator<char>(f)), {});
      auto root = character_json::Reader(text).read();
      const auto &arr = root.at("rooms").items();
      g_rooms.clear();
      g_rooms.reserve(arr.size());
      for (const auto &item : arr) {
        WarpRoom wr;
        wr.room = item.at("room").number();
        wr.stage = item.at("stage").number();
        wr.section = item.at("section").number();
        wr.boss = (item.at("boss").text == "true");
        wr.stage_name = item.at("stage_name").string();
        wr.label = item.at("label").string();
        wr.image = item.at("image").string();
        g_rooms.push_back(std::move(wr));
      }
      if (!g_rooms.empty()) return;
    } catch (...) {
      // Fall back to built-in table if rooms.json is malformed
    }
  }
  PopulateFallbackRooms();
}

static void EnsureTexture(WarpRoom &wr) {
  if (wr.tex_tried) return;
  wr.tex_tried = true;
  std::filesystem::path p = g_thumb_dir / wr.image;
  if (!std::filesystem::is_regular_file(p)) return;
  int w = 0, h = 0, ch = 0;
  unsigned char *pixels = stbi_load(p.string().c_str(), &w, &h, &ch, 4);
  if (!pixels || w <= 0 || h <= 0) {
    if (pixels) stbi_image_free(pixels);
    return;
  }
  GLuint tex = 0;
  glGenTextures(1, &tex);
  glBindTexture(GL_TEXTURE_2D, tex);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
  glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, pixels);
  glBindTexture(GL_TEXTURE_2D, 0);
  stbi_image_free(pixels);
  wr.tex = tex;
  wr.tex_w = w;
  wr.tex_h = h;
}

static void WarpToRoom(int room, void *ui_ptr) {
  if (!g_snes || room < 0 || room > 67) return;
  // If currently on title screen or non-gameplay mode, enter gameplay cleanly
  if (g_snes->ram[0x0032] != 4) {
    g_snes->ram[0x0032] = 4;
    g_snes->ram[0x0033] = 0;
    g_snes->ram[0x0034] = 0;
    g_snes->ram[0x0035] = 0;
    if (g_snes->ram[0x0076] == 0) g_snes->ram[0x0076] = 3; // Lives
    if (g_snes->ram[0x13f4] == 0) g_snes->ram[0x13f4] = 16; // Full HP
  }
  // Set target block ($0086) and trigger native level-load phase ($0070 = 3)
  g_snes->ram[0x0086] = static_cast<uint8_t>(room);
  g_snes->ram[0x0087] = 0;
  g_snes->ram[0x0070] = 3;
  g_snes->ram[0x0071] = 0;
  if (ui_ptr) {
    recomp_runtime_ui_close(static_cast<RecompRuntimeUi *>(ui_ptr));
  }
}

} // namespace

extern "C" void Cv4StageWarpDraw(void *ui_ptr) {
  EnsureLoaded();
  Cv4RuntimeUiPanel(1280, 960);
  const ImGuiWindowFlags flags =
      ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoCollapse;
  if (!ImGui::Begin("Level-Warp · Alle Abschnitte", nullptr, flags)) {
    ImGui::End();
    return;
  }

  const int cur_room = g_snes ? static_cast<int>(g_snes->ram[0x0086]) : -1;
  const bool in_game = g_snes && g_snes->ram[0x0032] == 4;

  // ── Top Filter & Controls Bar ────────────────────────────────────────────
  if (in_game && cur_room >= 0 && cur_room < static_cast<int>(g_rooms.size())) {
    ImGui::TextColored({0.83f, 0.69f, 0.35f, 1.0f}, "Aktuell: R-%02d  (%s)",
                       cur_room, g_rooms[cur_room].label.c_str());
  } else {
    ImGui::TextDisabled("Wähle ein Level und klicke auf einen Abschnitt zum sofortigen Teleportieren.");
  }

  ImGui::SetNextItemWidth(S(240));
  ImGui::InputTextWithHint("##warp_search", "Suchen (z. B. Medusa, 4-1, Boss)...", g_search, sizeof(g_search));
  ImGui::SameLine();
  ImGui::Checkbox("Nur Bosse", &g_only_bosses);
  ImGui::SameLine();
  if (ImGui::Button("Alle aufklappen")) g_expand_cmd = +1;
  ImGui::SameLine();
  if (ImGui::Button("Alle zuklappen")) g_expand_cmd = -1;
  ImGui::Separator();

  // ── Scrollable Stage Accordion List ──────────────────────────────────────
  const std::string query = ToLower(g_search);
  const float avail_w = ImGui::GetContentRegionAvail().x;
  const float card_w = S(210);
  const float thumb_w = S(192);
  const float thumb_h = S(168);
  const int cols = std::max(1, static_cast<int>(avail_w / (card_w + S(12))));

  if (ImGui::BeginChild("##warp_scroll", {0, 0}, false)) {
    for (int st = 1; st <= 11; ++st) {
      std::vector<WarpRoom *> stage_rooms;
      std::string stage_title;
      for (auto &wr : g_rooms) {
        if (wr.stage != st) continue;
        if (stage_title.empty()) stage_title = wr.stage_name;
        if (g_only_bosses && !wr.boss) continue;
        if (!query.empty()) {
          char rcode[16];
          std::snprintf(rcode, sizeof(rcode), "r-%02d", wr.room);
          if (ToLower(wr.label).find(query) == std::string::npos &&
              ToLower(wr.stage_name).find(query) == std::string::npos &&
              std::string(rcode).find(query) == std::string::npos) {
            continue;
          }
        }
        stage_rooms.push_back(&wr);
      }
      if (stage_rooms.empty()) continue;

      if (g_expand_cmd != 0) {
        ImGui::SetNextItemOpen(g_expand_cmd > 0, ImGuiCond_Always);
      } else if (!query.empty() || g_only_bosses) {
        ImGui::SetNextItemOpen(true, ImGuiCond_Appearing);
      } else if (st == 1) {
        ImGui::SetNextItemOpen(true, ImGuiCond_Once);
      }

      char hdr[128];
      std::snprintf(hdr, sizeof(hdr), "%s  (%zu Abschnitte)##stage_%d",
                    stage_title.c_str(), stage_rooms.size(), st);
      ImGui::PushStyleColor(ImGuiCol_Header, {0.16f, 0.19f, 0.27f, 1.0f});
      ImGui::PushStyleColor(ImGuiCol_HeaderHovered, {0.24f, 0.20f, 0.28f, 1.0f});
      ImGui::PushStyleColor(ImGuiCol_HeaderActive, {0.35f, 0.26f, 0.16f, 1.0f});
      const bool open = ImGui::CollapsingHeader(hdr);
      ImGui::PopStyleColor(3);

      if (open) {
        ImGui::Spacing();
        for (size_t i = 0; i < stage_rooms.size(); ++i) {
          WarpRoom &wr = *stage_rooms[i];
          EnsureTexture(wr);
          if (i % cols != 0) ImGui::SameLine(0.0f, S(10));

          const bool is_cur = (in_game && wr.room == cur_room);
          ImVec4 border_col = is_cur ? ImVec4{0.85f, 0.70f, 0.32f, 1.0f}
                            : wr.boss ? ImVec4{0.68f, 0.22f, 0.28f, 1.0f}
                                      : ImVec4{0.22f, 0.27f, 0.36f, 1.0f};
          ImGui::PushStyleColor(ImGuiCol_ChildBg, {0.09f, 0.11f, 0.16f, 1.0f});
          ImGui::PushStyleColor(ImGuiCol_Border, border_col);
          ImGui::PushStyleVar(ImGuiStyleVar_ChildRounding, S(6));
          ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, {S(8), S(8)});

          char cid[32];
          std::snprintf(cid, sizeof(cid), "##card_%02d", wr.room);
          if (ImGui::BeginChild(cid, {card_w, thumb_h + S(74)}, true, ImGuiWindowFlags_NoScrollbar)) {
            if (wr.tex) {
              char img_id[32];
              std::snprintf(img_id, sizeof(img_id), "##img_%02d", wr.room);
              if (ImGui::ImageButton(img_id, (ImTextureID)(intptr_t)wr.tex, {thumb_w, thumb_h})) {
                WarpToRoom(wr.room, ui_ptr);
              }
            } else {
              char ph[32];
              std::snprintf(ph, sizeof(ph), "R-%02d##ph_%02d", wr.room, wr.room);
              if (ImGui::Button(ph, {thumb_w, thumb_h})) {
                WarpToRoom(wr.room, ui_ptr);
              }
            }

            if (wr.boss) {
              ImGui::TextColored({0.95f, 0.76f, 0.35f, 1.0f}, "%s", wr.label.c_str());
            } else {
              ImGui::Text("%s  (R-%02d)", wr.label.c_str(), wr.room);
            }

            char btn[48];
            std::snprintf(btn, sizeof(btn), "%s##go_%02d",
                          is_cur ? "Neu starten" : "Teleportieren", wr.room);
            if (ImGui::Button(btn, {-1.0f, S(26)})) {
              WarpToRoom(wr.room, ui_ptr);
            }
          }
          ImGui::EndChild();
          ImGui::PopStyleVar(2);
          ImGui::PopStyleColor(2);
        }
        ImGui::Spacing();
      }
    }
    g_expand_cmd = 0;
  }
  ImGui::EndChild();
  ImGui::End();
}

extern "C" void Cv4StageWarpShutdown(void) {
  for (auto &wr : g_rooms) {
    if (wr.tex) {
      glDeleteTextures(1, &wr.tex);
      wr.tex = 0;
    }
    wr.tex_tried = false;
  }
  g_rooms.clear();
  g_loaded = false;
}
