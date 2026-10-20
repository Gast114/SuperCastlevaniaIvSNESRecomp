/* Debug markers: Ctrl+D (config.ini [KeyMap] DebugMarker) or Select+L3 on a
 * pad ([Controller] DebugGesture) freezes the game and records the moment
 * into debug_markers/<time>_<scene>/ beside the executable:
 *
 *   state.sav    save state (sciv_play.py loadfile <path>)
 *   screen.png   the presented field, widescreen margins included
 *   video.bin    VRAM + CGRAM + OAM (tools/re/render_map.py)
 *   wram.bin     128 KB WRAM
 *   lines.bin    per-scanline PPU registers (hd_collect.h)
 *   marker.json  scene, game state, PPU layers, the note
 *   note.md      the same for reading
 *
 * A small panel then asks what is wrong. Ctrl+Enter or pad A keeps the
 * marker, Escape or pad B discards it. tools/debug_markers.py lists them.
 *
 * Self-test: SNESRECOMP_DEBUG_MARKER_AT=<frame> opens a marker at that frame
 * and SNESRECOMP_DEBUG_MARKER_NOTE=<text> saves it with that note.
 * SNESRECOMP_DEBUG_MARKER_TYPE=<text> instead types the text through SDL's
 * event queue and presses Ctrl+Enter about two seconds later, so the whole
 * keyboard path (host pump, ImGui focus and text input) is exercised. */
#include "debug_marker.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <string>

#include "debug_capture.h"
#include "hd_collect.h"
#include "hd_render.h"
#include "imgui.h"
#include "imgui_impl_sdl3.h"
#include "scene.h"
#include <SDL3/SDL.h>

extern "C" unsigned char g_ram[0x20000];

namespace fs = std::filesystem;

namespace {

bool g_open;
bool g_focus_note;
unsigned g_pumps;
fs::path g_dir;
std::string g_created, g_scene, g_ppu_json, g_hd_json;
bool g_hd_image;
unsigned g_frame;
char g_note[4096];

unsigned Word(unsigned address) { return g_ram[address] | g_ram[address + 1] << 8; }

std::string JsonEscape(const char *text) {
  std::string out;
  for (const char *c = text; *c; c++) {
    switch (*c) {
    case '"': out += "\\\""; break;
    case '\\': out += "\\\\"; break;
    case '\n': out += "\\n"; break;
    case '\r': break;
    case '\t': out += "\\t"; break;
    default:
      if ((unsigned char)*c < 0x20) {
        char buf[8];
        std::snprintf(buf, sizeof(buf), "\\u%04x", *c);
        out += buf;
      } else {
        out += *c;
      }
    }
  }
  return out;
}

/* RAM fields the analysis notes name (D:\Reverse Engineering\docs\sc4). */
std::string GameStateJson() {
  char buf[512];
  std::snprintf(buf, sizeof(buf),
      "{\"game_mode\":%u,\"mode_step\":%u,\"level_phase\":%u,\"pre_level\":%u,"
      "\"block\":%u,\"camera_x\":%u,\"camera_y\":%u,\"camera_lock_left\":%u,"
      "\"player_x\":%u,\"player_y\":%u,\"title_choice\":%u,\"campaign_tag\":%u}",
      g_ram[0x32], g_ram[0x34], g_ram[0x70], g_ram[0x72], g_ram[0x86],
      Word(0x1c), Word(0x1e), Word(0xa0), Word(0x54a), Word(0x54e),
      Word(0x1e02), Word(0x11e0));
  return buf;
}

void Close() {
  g_open = false;
  g_note[0] = 0;
}

void Save() {
  const std::string note = JsonEscape(g_note);
  std::ofstream json(g_dir / "marker.json", std::ios::binary);
  json << "{\n  \"created\": \"" << g_created << "\",\n"
       << "  \"note\": \"" << note << "\",\n"
       << "  \"frame\": " << g_frame << ",\n"
       << "  \"scene\": \"" << g_scene << "\",\n"
       << "  \"widescreen\": " << (Cv4CaptureWidescreenOn()) << ",\n"
       << "  \"state\": " << GameStateJson() << ",\n"
       << "  \"hd\": " << g_hd_json << ",\n"
       << "  \"ppu\": " << (g_ppu_json.empty() ? "null" : g_ppu_json) << "\n}\n";
  json.close();
  std::ofstream md(g_dir / "note.md", std::ios::binary);
  md << "# Debug-Marker " << g_created << "\n\n"
     << (g_note[0] ? g_note : "(ohne Beschreibung)") << "\n\n"
     << "- Szene: " << (g_scene.empty() ? "?" : g_scene) << ", Frame " << g_frame
     << ", Widescreen " << (Cv4CaptureWidescreenOn() ? "an" : "aus") << "\n"
     << "- Zustand: " << GameStateJson() << "\n"
     << "- Dateien: state.sav, screen.png, video.bin, wram.bin, lines.bin, marker.json\n";
  if (g_hd_image) md << "- HD-Bild: hd_screen.png (Originalbild separat in screen.png)\n";
  md.close();
  std::fprintf(stderr, "[debug marker] saved %s\n", g_dir.string().c_str());
  Close();
}

void Discard() {
  std::error_code error;
  fs::remove_all(g_dir, error);
  std::fprintf(stderr, "[debug marker] discarded %s\n", g_dir.string().c_str());
  Close();
}

}  // namespace

extern "C" int Cv4DebugMarkerOpen(void) {
  if (g_open)
    return 1;
  std::time_t now = std::time(nullptr);
  std::tm local{};
#if defined(_WIN32)
  localtime_s(&local, &now);
#else
  localtime_r(&now, &local);
#endif
  char stamp[32], created[32];
  std::strftime(stamp, sizeof(stamp), "%Y-%m-%d_%H-%M-%S", &local);
  std::strftime(created, sizeof(created), "%Y-%m-%d %H:%M:%S", &local);
  const char *scene = Cv4CurrentSceneName();
  g_scene = scene ? scene : "";
  g_created = created;
  g_frame = Cv4CaptureFrameNumber();
  const auto base = fs::path("debug_markers") / (std::string(stamp) + "_" + (scene ? scene : "other"));
  std::error_code error;
  fs::create_directories(base.parent_path(), error);
  if (!error) for (unsigned suffix=0;;++suffix) {
    g_dir = suffix ? fs::path(base.string()+"_"+std::to_string(suffix)) : base;
    if (fs::create_directory(g_dir,error) || error) break;
  }
  if (error) {
    std::fprintf(stderr, "[debug marker] cannot create %s\n", g_dir.string().c_str());
    return 0;
  }
  char message[128];
  bool ok = Cv4CaptureSaveState((g_dir / "state.sav").string().c_str()) != 0;
  ok &= Cv4CaptureFieldPng((g_dir / "screen.png").string().c_str(), message, sizeof(message)) != 0;
  g_hd_image = Cv4HdEnabled() && Cv4HdScreenshot((g_dir / "hd_screen.png").string().c_str());
  g_hd_json = "{\"enabled\":" + std::to_string(Cv4HdEnabled()) +
      ",\"scale\":" + std::to_string(Cv4HdScale()) +
      ",\"layers\":" + std::to_string(Cv4HdLayerMask()) +
      ",\"art_scale\":" + std::to_string(Cv4HdPackScale()) +
      ",\"pack\":\"" + JsonEscape(Cv4HdPackPath()) + "\"}";
  ok &= Cv4CaptureVideoDump((g_dir / "video.bin").string().c_str()) != 0;
  ok &= Cv4CaptureWram((g_dir / "wram.bin").string().c_str()) != 0;
  {
    /* Per-scanline registers of the frozen frame (hd_collect.h layout), so
     * tools/hd/hd_preview.py can reconstruct supported layers and parallax. */
    std::ofstream lines(g_dir / "lines.bin", std::ios::binary);
    lines.write(reinterpret_cast<const char *>(Cv4HdLines()), sizeof(Cv4HdLine) * kCv4HdLines);
    ok &= lines.good();
  }
  char ppu[1024];
  g_ppu_json = Cv4CapturePpuJson(ppu, sizeof(ppu)) ? ppu : "";
  if (!ok)
    std::fprintf(stderr, "[debug marker] some captures failed in %s\n", g_dir.string().c_str());
  g_note[0] = 0;
  g_pumps = 0;
  g_open = true;
  g_focus_note = true;
  /* Without the OpenGL presenter there is no panel to type into: keep the
   * capture with an empty note instead of freezing behind nothing. */
  if (!Cv4CaptureHasPanelPresenter() || !ImGui::GetCurrentContext()) {
    Save();
    return 0;
  }
  return 1;
}

extern "C" int Cv4DebugMarkerIsOpen(void) { return g_open; }

extern "C" void Cv4DebugMarkerEvent(const void *event_ptr) {
  if (!g_open || !event_ptr)
    return;
  const SDL_Event *event = static_cast<const SDL_Event *>(event_ptr);
  if (ImGui::GetCurrentContext())
    ImGui_ImplSDL3_ProcessEvent(event);
  /* Handled here as well as in the panel, so the keys work even on a pass
   * the overlay is not drawn. */
  if (event->type == SDL_EVENT_KEY_DOWN && !event->key.repeat) {
    if (event->key.key == SDLK_ESCAPE)
      Discard();
    else if ((event->key.key == SDLK_RETURN || event->key.key == SDLK_KP_ENTER) &&
             (event->key.mod & SDL_KMOD_CTRL))
      Save();
  }
}

extern "C" void Cv4DebugMarkerPump(uint32_t pad_pressed) {
  if (!g_open)
    return;
  g_pumps++;
  static const char *selftest_note = std::getenv("SNESRECOMP_DEBUG_MARKER_NOTE");
  if (selftest_note && g_pumps == 5) {
    std::snprintf(g_note, sizeof(g_note), "%s", selftest_note);
    Save();
    return;
  }
  static const char *selftest_type = std::getenv("SNESRECOMP_DEBUG_MARKER_TYPE");
  if (selftest_type && (g_pumps == 10 || g_pumps == 250)) {
    SDL_Event event{};
    /* ImGui's SDL3 backend drops keyboard events for unknown windows. */
    int windows = 0;
    SDL_Window **list = SDL_GetWindows(&windows);
    const SDL_WindowID window = list && windows > 0 ? SDL_GetWindowID(list[0]) : 0;
    SDL_free(list);
    if (g_pumps == 10) {
      event.type = SDL_EVENT_TEXT_INPUT;
      event.text.windowID = window;
      event.text.text = selftest_type;   /* static: outlives the queue */
    } else {
      event.type = SDL_EVENT_KEY_DOWN;
      event.key.windowID = window;
      event.key.key = SDLK_RETURN;
      event.key.scancode = SDL_SCANCODE_RETURN;
      event.key.mod = SDL_KMOD_LCTRL;
      event.key.down = true;
    }
    SDL_PushEvent(&event);
  }
  /* The overlay pad word (snes_overlay_draw.h): A = bit 8, B = bit 0. */
  if (pad_pressed & (1u << 8))
    Save();
  else if (pad_pressed & (1u << 0))
    Discard();
}

extern "C" void Cv4DebugMarkerDraw(void) {
  if (!g_open)
    return;
  const ImGuiIO &io = ImGui::GetIO();
  const float width = io.DisplaySize.x - 48 < 620 ? io.DisplaySize.x - 48 : 620;
  ImGui::SetNextWindowPos({io.DisplaySize.x * 0.5f, io.DisplaySize.y * 0.5f},
                          ImGuiCond_Always, {0.5f, 0.5f});
  ImGui::SetNextWindowSize({width, 0}, ImGuiCond_Always);
  ImGui::Begin("Debug-Marker", nullptr,
               ImGuiWindowFlags_NoCollapse | ImGuiWindowFlags_NoSavedSettings |
               ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize);
  ImGui::TextWrapped("Savestate, Bild, PPU/VRAM und WRAM sind gesichert. "
                     "Was stimmt hier nicht?");
  ImGui::TextDisabled("%s  (Szene %s, Frame %u)", g_dir.filename().string().c_str(),
                      g_scene.empty() ? "?" : g_scene.c_str(), g_frame);
  if (g_focus_note) {
    ImGui::SetKeyboardFocusHere();
    g_focus_note = false;
  }
  ImGui::InputTextMultiline("##note", g_note, sizeof(g_note), {-1, 150});
  if (ImGui::Button("Speichern  (Strg+Enter / A)"))
    Save();
  ImGui::SameLine();
  if (g_open && ImGui::Button("Verwerfen  (Esc / B)"))
    Discard();
  ImGui::End();
}
