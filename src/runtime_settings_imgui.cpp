#include "runtime_settings_imgui.h"
#include "character_pack.h"
#include "debug_marker.h"
#include "hd_collect.h"
#include "hd_render.h"

#include "recomp_runtime_ui.h"
#include "imgui.h"
#include "imgui_impl_opengl3.h"
#include "imgui_impl_sdl3.h"
#include <SDL3/SDL.h>
#include <cstdlib>
#include <cstdio>
#include <filesystem>
#include <string>

static bool s_initialized;

static void ApplyStyle() {
  ImGuiStyle &style = ImGui::GetStyle();
  ImGui::StyleColorsDark(&style);
  style.WindowRounding = 10.0f;
  style.ChildRounding = 8.0f;
  style.FrameRounding = 6.0f;
  style.GrabRounding = 6.0f;
  style.WindowPadding = ImVec2(20.0f, 18.0f);
  style.ItemSpacing = ImVec2(10.0f, 10.0f);
  style.Colors[ImGuiCol_WindowBg] = ImVec4(0.035f, 0.045f, 0.085f, 0.98f);
  style.Colors[ImGuiCol_ChildBg] = ImVec4(0.055f, 0.070f, 0.120f, 0.96f);
  style.Colors[ImGuiCol_Button] = ImVec4(0.34f, 0.16f, 0.68f, 1.0f);
  style.Colors[ImGuiCol_ButtonHovered] = ImVec4(0.48f, 0.24f, 0.88f, 1.0f);
  style.Colors[ImGuiCol_ButtonActive] = ImVec4(0.25f, 0.75f, 0.72f, 1.0f);
  style.Colors[ImGuiCol_CheckMark] = ImVec4(0.35f, 0.95f, 0.78f, 1.0f);
  style.Colors[ImGuiCol_TabSelected] = ImVec4(0.34f, 0.16f, 0.68f, 1.0f);
  style.Colors[ImGuiCol_Header] = ImVec4(0.26f, 0.13f, 0.52f, 1.0f);
  style.Colors[ImGuiCol_HeaderHovered] = ImVec4(0.48f, 0.24f, 0.88f, 1.0f);
  style.Colors[ImGuiCol_HeaderActive] = ImVec4(0.25f, 0.75f, 0.72f, 1.0f);
}

/* Original/HD controls and export tools (docs/HD_PIPELINE.md). */
static void HdPanel() {
  const ImVec2 display = ImGui::GetIO().DisplaySize;
  ImGui::SetNextWindowPos({24, 45}, ImGuiCond_FirstUseEver);
  ImGui::SetNextWindowSize({display.x - 48 < 560 ? display.x - 48 : 560,
                           display.y - 60}, ImGuiCond_FirstUseEver);
  if (!ImGui::Begin("HD graphics")) {
    ImGui::End();
    return;
  }
  bool hd = Cv4HdEnabled() != 0;
  if (ImGui::Checkbox("HD graphics enabled", &hd)) Cv4HdEnable(hd);
  /* Exercise the real clickable widget in the opt-in UI regression. */
  if (std::getenv("SNESRECOMP_HD_UI_SELFTEST")) {
    static unsigned frame;
    ++frame;
    ImVec2 p = ImGui::GetItemRectMin();
    if (frame <= 3) ImGui::GetIO().AddMousePosEvent(p.x + 8, p.y + 8);
    if (frame == 2) ImGui::GetIO().AddMouseButtonEvent(0, true);
    if (frame == 3) ImGui::GetIO().AddMouseButtonEvent(0, false);
  }
  ImGui::TextWrapped("Switch back to original graphics at any time. Changes apply when you resume.");
  int scale = Cv4HdScale();
  const int factors[] = {2, 4, 6, 10};
  const char *labels[] = {"2x", "4x", "6x", "10x (4K target)"};
  for (int i = 0; i < 4; ++i) {
    if (i) ImGui::SameLine();
    if (ImGui::RadioButton(labels[i], scale == factors[i])) Cv4HdSetScale(factors[i]);
  }
  unsigned mask = Cv4HdLayerMask();
  const char *categories[] = {"Backgrounds", "Text / HUD", "Sprites"};
  const unsigned bits[] = {3, 12, 16};
  for (int i = 0; i < 3; ++i) {
    if (i) ImGui::SameLine();
    bool on = (mask & bits[i]) != 0;
    if (ImGui::Checkbox(categories[i], &on)) {
      mask = on ? mask | bits[i] : mask & ~bits[i]; Cv4HdSetLayerMask(mask);
    }
  }
  if (ImGui::BeginCombo("Graphics pack", Cv4HdPackPath())) {
    if (ImGui::Selectable("hd_pack")) Cv4HdLoadPack("hd_pack");
    std::error_code error;
    for (const auto &entry : std::filesystem::directory_iterator("hd_packs", error)) {
      if (!entry.is_directory(error) || !std::filesystem::exists(entry.path() / "pack.json", error)) continue;
      auto path = entry.path().generic_string();
      if (ImGui::Selectable(path.c_str())) Cv4HdLoadPack(path.c_str());
    }
    ImGui::EndCombo();
  }
  if (ImGui::Button("Reload graphics pack")) Cv4HdLoadPack(Cv4HdPackPath());
  ImGui::TextWrapped("%s", Cv4HdStatus());
  ImGui::Text("%u visible native pixels matched in the last frame", Cv4HdReplacedPixels());
  ImGui::TextWrapped("Missing tiles and unsupported effects keep their original graphics. Original sprite silhouettes are retained.");
  if (Cv4HdPackScale() > 0 && Cv4HdPackScale() < 10)
    ImGui::TextWrapped("This pack has %dx artwork. 4K output does not create missing detail; full 4K artwork should use 80 x 80 pixels per original 8 x 8 tile.", Cv4HdPackScale());
  ImGui::Separator();
  bool collecting = Cv4HdCollecting() != 0;
  if (ImGui::Checkbox("Collect graphics while playing", &collecting))
    Cv4HdSetCollecting(collecting);
  unsigned tiles = 0, captures = 0, pending = 0, errors = 0;
  Cv4HdStats(&tiles, &captures, &pending, &errors);
  ImGui::Text("%u different tiles this session, %u pictures written%s", tiles, captures,
              pending ? " (writing...)" : "");
  if (errors)
    ImGui::TextWrapped("Writing failed; collection stopped. Check game.log and available disk space.");
  ImGui::TextWrapped(
      "Every layer is saved to hd_dump/ whenever it shows tiles that are not "
      "collected yet. Play through the parts you want in HD, then run "
      "tools/hd/hd_pipeline.py to upscale them and build the HD pack.");
  ImGui::End();
}

extern "C" bool Cv4RuntimeSettingsImGuiInit(void *window, void *gl_context) {
  if (s_initialized) return true;
  if (!window || !gl_context) return false;
  IMGUI_CHECKVERSION();
  ImGui::CreateContext();
  ImGuiIO &io = ImGui::GetIO();
  io.IniFilename = nullptr;
  io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
  io.ConfigFlags |= ImGuiConfigFlags_NavEnableGamepad;
  ApplyStyle();
  if (!ImGui_ImplSDL3_InitForOpenGL(static_cast<SDL_Window *>(window), gl_context) ||
      !ImGui_ImplOpenGL3_Init("#version 330 core")) {
    ImGui::DestroyContext();
    return false;
  }
  s_initialized = true;
  return true;
}

extern "C" void Cv4RuntimeSettingsImGuiShutdown(void) {
  if (!s_initialized) return;
  ImGui_ImplOpenGL3_Shutdown();
  ImGui_ImplSDL3_Shutdown();
  ImGui::DestroyContext();
  s_initialized = false;
}

extern "C" void Cv4RuntimeSettingsImGuiProcessEvent(const void *event_ptr) {
  if (!s_initialized || !event_ptr) return;
  const SDL_Event *event = static_cast<const SDL_Event *>(event_ptr);
  /* Keyboard and controller navigation are handled by the runtime model in
     host_main.c. Feed pointer input here so ImGui rows remain clickable. */
  switch (event->type) {
    case SDL_EVENT_MOUSE_MOTION:
    case SDL_EVENT_MOUSE_BUTTON_DOWN:
    case SDL_EVENT_MOUSE_BUTTON_UP:
    case SDL_EVENT_MOUSE_WHEEL:
      ImGui_ImplSDL3_ProcessEvent(event);
      break;
    default:
      break;
  }
}

extern "C" void Cv4RuntimeSettingsImGuiRender(void *ui_ptr, int width,
                                                int height) {
  if (!s_initialized) return;
  if (Cv4DebugMarkerIsOpen()) {
    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplSDL3_NewFrame();
    ImGui::NewFrame();
    Cv4DebugMarkerDraw();
    ImGui::Render();
    ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
    return;
  }
  if (!ui_ptr) return;
  if (!recomp_runtime_ui_is_open(static_cast<RecompRuntimeUi *>(ui_ptr))) return;
  ImGui_ImplOpenGL3_NewFrame();
  ImGui_ImplSDL3_NewFrame();
  ImGui::NewFrame();
  enum { kSettings, kCharacters, kHd };
  static int tab = std::getenv("SNESRECOMP_HD_UI_SELFTEST") ? kHd :
      std::getenv("SNESRECOMP_CHARACTER_WORKSHOP_SELFTEST") ? kCharacters : kSettings;
  ImGui::SetNextWindowPos({8, 0});
  ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, ImVec2(6, 3));
  ImGui::Begin("Settings tools", nullptr, ImGuiWindowFlags_NoDecoration |
      ImGuiWindowFlags_AlwaysAutoResize | ImGuiWindowFlags_NoSavedSettings);
  if (ImGui::Button("Game settings")) tab = kSettings;
  ImGui::SameLine();
  if (ImGui::Button("Character workshop")) tab = kCharacters;
  ImGui::SameLine();
  if (ImGui::Button("HD graphics")) tab = kHd;
  ImGui::End();
  ImGui::PopStyleVar();
  if (tab == kCharacters) Cv4CharacterEditor();
  else if (tab == kHd) HdPanel();
  else recomp_runtime_ui_render_imgui(static_cast<RecompRuntimeUi *>(ui_ptr));
  ImGui::Render();
  ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
}
