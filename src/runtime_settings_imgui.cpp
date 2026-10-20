#include "runtime_settings_imgui.h"
#include "character_pack.h"
#include "debug_marker.h"
#include "hd_collect.h"
#include "hd_render.h"
#include "game_performance.h"

#include "recomp_runtime_ui.h"
#include "imgui.h"
#include "imgui_impl_opengl3.h"
#include "imgui_impl_sdl3.h"
extern "C" {
#include "config.h"
}
#include <cstdlib>
#include <cstdio>
#include <filesystem>
#include <string>
#include <algorithm>
extern "C" {
#include "host_main.h"
void launcher_ini_kv_write(const char *, const char *, const char *, const char *);
}

static bool s_initialized;
enum { kSettings, kCharacters, kHd, kShortcuts, kPerformance };
static int s_tab=kSettings, s_capture=-1;
static std::string s_bind_message;
static const ImGuiWindowFlags kPanelFlags=ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoResize|ImGuiWindowFlags_NoCollapse;

static bool StoreBinding(int command, SDL_Keycode key, SDL_Keymod mod) {
  int conflict=key?FindCmdForSdlKey(key,mod):0;
  if(conflict && conflict!=command) {
    int index=0,count=0;const char *group=ConfigCommandGroup(conflict,&index,&count);
    s_bind_message="Already assigned: "+std::string(group?group:"another action")+(count>1?" "+std::to_string(index+1):"");return false;
  }
  std::string value="None";
  if(key) {
    const char *name=SDL_GetKeyName(key);
    if(!name || !*name || std::string(name).find(',')!=std::string::npos) {s_bind_message="This key cannot be saved in the binding format.";return false;}
    value=std::string(mod&SDL_KMOD_CTRL?"Ctrl+":"")+(mod&SDL_KMOD_ALT?"Alt+":"")+(mod&SDL_KMOD_SHIFT?"Shift+":"")+name;
  }
  int index,count;const char *group=ConfigCommandGroup(command,&index,&count);
  if(!group)return false;
  std::string line;
  for(int i=0;i<count;++i) {
    char current[256];ConfigGetCommandBinding(command-index+i,current,sizeof(current));
    if(i)line+=",";
    line+=i==index?value:current;
  }
  launcher_ini_kv_write(SnesDesktopConfigPath(),"KeyMap",group,line.c_str());
  ConfigReloadKeyMap(SnesDesktopConfigPath());
  char actual[256];ConfigGetCommandBinding(command,actual,sizeof(actual));
  if(value!=actual) {s_bind_message="Could not save this shortcut. Existing binding retained.";return false;}
  s_bind_message="Saved. Active immediately.";return true;
}

static void ShortcutPanel() {
  static unsigned test_frame;
  bool testing=std::getenv("SNESRECOMP_SHORTCUT_UI_SELFTEST")!=nullptr;
  if(testing)++test_frame;
  ImVec2 display=ImGui::GetIO().DisplaySize;
  ImGui::SetNextWindowPos({16,76},ImGuiCond_Always);
  ImGui::SetNextWindowSize({display.x-32,std::max(120.f,display.y-92)},ImGuiCond_Always);
  if(ImGui::Begin("Shortcuts",nullptr,kPanelFlags)) {
    ImGui::TextWrapped("Click a binding, then press a key combination. Escape cancels capture. Clear removes a binding. Conflicts are kept until you clear or change the other action.");
    ImGui::TextWrapped("Debug marker: screenshot + save state + problem note. Ctrl+Enter / pad A saves the note; Esc / pad B cancels.");
    if(s_capture>=0)ImGui::TextColored({1,.8f,.3f,1},"Waiting for key combination... Escape cancels.");
    if(!s_bind_message.empty())ImGui::TextWrapped("%s",s_bind_message.c_str());
    static ImGuiTextFilter filter;filter.Draw("Filter actions");
    if(ImGui::BeginTable("Bindings",3,ImGuiTableFlags_RowBg|ImGuiTableFlags_BordersInnerH|ImGuiTableFlags_ScrollY,{0,-90})) {
      ImGui::TableSetupColumn("Action",ImGuiTableColumnFlags_WidthStretch);
      ImGui::TableSetupColumn("Binding (click to change)",ImGuiTableColumnFlags_WidthFixed,200);
      ImGui::TableSetupColumn("",ImGuiTableColumnFlags_WidthFixed,70);
      ImGui::TableSetupScrollFreeze(0,1);ImGui::TableHeadersRow();
      auto row=[&](int command,const char *label) {
        if(!filter.PassFilter(label))return;
        ImGui::PushID(command);ImGui::TableNextRow();ImGui::TableNextColumn();ImGui::TextUnformatted(label);ImGui::TableNextColumn();
        char binding[256];ConfigGetCommandBinding(command,binding,sizeof(binding));
        if(ImGui::Button(s_capture==command?"Press keys...":binding,{-1,30})) {s_capture=command;s_bind_message.clear();}
        if(testing&&command==kKeys_ToggleHD) {
          ImVec2 p=ImGui::GetItemRectMin();ImGui::GetIO().AddMousePosEvent(p.x+12,p.y+12);
          if(test_frame==2||test_frame==9||test_frame==16||test_frame==29)ImGui::GetIO().AddMouseButtonEvent(0,true);
          if(test_frame==3||test_frame==10||test_frame==17||test_frame==30)ImGui::GetIO().AddMouseButtonEvent(0,false);
        }
        // Keep the menu reachable, including a way back to Escape (Escape
        // cancels ordinary key capture). Other actions can be unbound.
        ImGui::TableNextColumn();
        if(ImGui::Button(command==kKeys_OpenSettings?"Default":"Clear",{-1,30})){
          StoreBinding(command,command==kKeys_OpenSettings?SDLK_ESCAPE:0,SDL_KMOD_NONE);s_capture=-1;
        }
        ImGui::PopID();
        if(testing&&command==kKeys_ToggleHD&&(test_frame==24||test_frame==25)) {
          ImVec2 p=ImGui::GetItemRectMin();ImGui::GetIO().AddMousePosEvent(p.x+12,p.y+12);
          ImGui::GetIO().AddMouseButtonEvent(0,test_frame==24);
        }
      };
      struct Entry {int command;const char *label;};
      const Entry entries[]={{kKeys_OpenSettings,"Open menu"},{kKeys_ToggleHD,"Original / HD graphics"},{kKeys_DebugMarker,"Debug screenshot and problem note"},{kKeys_Screenshot,"Screenshot"},{kKeys_SaveStateMenu,"Save state browser"},{kKeys_Rewind,"Rewind"},{kKeys_PauseDimmed,"Pause with dimming"},{kKeys_Pause,"Pause"},{kKeys_Fullscreen,"Fullscreen"},{kKeys_Reset,"Reset game"},{kKeys_Turbo,"Turbo (hold)"},{kKeys_WindowBigger,"Larger window"},{kKeys_WindowSmaller,"Smaller window"},{kKeys_VolumeUp,"Volume up"},{kKeys_VolumeDown,"Volume down"},{kKeys_DisplayPerf,"Show performance"},{kKeys_ToggleRenderer,"PPU renderer (diagnostic)"}};
      for(const auto &e:entries)row(e.command,e.label);
      row(kKeys_ToggleWidescreen,"Toggle widescreen");
      row(kKeys_OpenLauncher,"Open launcher (when available)");
      for(int i=0;i<20;++i) {std::string load="Load slot "+std::to_string(i+1),save="Save slot "+std::to_string(i+1);row(kKeys_Load+i,load.c_str());row(kKeys_Save+i,save.c_str());}
      ImGui::EndTable();
    }
    const char *gestures[]={"Select+L3","Select+R3","Select+L","Select+R","Select+Start","None"};
    auto gesture=[&](bool debug,const char *label,const char *saved,const char *fallback) {
      const char *current=*saved?saved:fallback;
      if(ImGui::BeginCombo(label,current)) {
        for(const char *choice:gestures)if(ImGui::Selectable(choice,!SDL_strcasecmp(current,choice))) {
          const char *other=debug?g_config.rewind_gesture:g_config.debug_gesture;
          if(!*other)other=debug?"Select+R3":"Select+L3";
          if(SDL_strcasecmp(choice,"None")&&!SDL_strcasecmp(choice,other))s_bind_message="This controller gesture is already assigned.";
          else {launcher_ini_kv_write(SnesDesktopConfigPath(),"Controller",debug?"DebugGesture":"RewindGesture",choice);SnesDesktopSetGesture(debug,choice);}
        }
        ImGui::EndCombo();
      }
    };
    ImGui::SetNextItemWidth(150);gesture(true,"Controller debug marker",g_config.debug_gesture,"Select+L3");
    ImGui::SameLine();ImGui::SetNextItemWidth(150);gesture(false,"Controller rewind",g_config.rewind_gesture,"Select+R3");
    if(testing) {
      auto key=[](SDL_Keycode k,SDL_Keymod mod){SDL_Event e{};e.type=SDL_EVENT_KEY_DOWN;e.key.key=k;e.key.mod=mod;SDL_PushEvent(&e);};
      if(test_frame==5)key(SDLK_D,SDL_KMOD_CTRL);
      if(test_frame==7){std::fprintf(stderr,"shortcut conflict retained=%d\n",s_capture==kKeys_ToggleHD&&s_bind_message.find("Already assigned")!=std::string::npos);key(SDLK_ESCAPE,SDL_KMOD_NONE);}
      if(test_frame==12||test_frame==32)key(SDLK_H,SDL_KMOD_ALT);
      if(test_frame==14)std::fprintf(stderr,"shortcut rebound=%d\n",FindCmdForSdlKey(SDLK_H,SDL_KMOD_ALT)==kKeys_ToggleHD&&FindCmdForSdlKey(SDLK_H,SDL_KMOD_CTRL)==0);
      if(test_frame==19)key(SDLK_ESCAPE,SDL_KMOD_NONE);
      if(test_frame==22)std::fprintf(stderr,"shortcut cancel retained=%d\n",s_capture==-1&&FindCmdForSdlKey(SDLK_H,SDL_KMOD_ALT)==kKeys_ToggleHD);
      if(test_frame==27)std::fprintf(stderr,"shortcut cleared=%d\n",FindCmdForSdlKey(SDLK_H,SDL_KMOD_ALT)==0);
      if(test_frame==35)std::fprintf(stderr,"shortcut final=%d\n",FindCmdForSdlKey(SDLK_H,SDL_KMOD_ALT)==kKeys_ToggleHD);
    }
  }
  ImGui::End();
}

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
  ImGui::SetNextWindowPos({24, 76}, ImGuiCond_Always);
  ImGui::SetNextWindowSize({display.x - 48 < 560 ? display.x - 48 : 560,
                           display.y - 92}, ImGuiCond_Always);
  if (!ImGui::Begin("HD graphics",nullptr,kPanelFlags)) {
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
  if(Cv4HdScale()!=10)Cv4HdSetScale(10);
  ImGui::TextUnformatted("HD resolution: 10x (4K target)");
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
  s_tab=std::getenv("SNESRECOMP_PERFORMANCE_UI_SELFTEST")?kPerformance:std::getenv("SNESRECOMP_HD_UI_SELFTEST")?kHd:std::getenv("SNESRECOMP_CHARACTER_WORKSHOP_SELFTEST")?kCharacters:std::getenv("SNESRECOMP_SHORTCUT_UI_SELFTEST")?kShortcuts:kSettings;
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

extern "C" bool Cv4RuntimeSettingsImGuiProcessEvent(const void *event_ptr) {
  if (!s_initialized || !event_ptr) return false;
  const SDL_Event *event = static_cast<const SDL_Event *>(event_ptr);
  if(s_capture>=0 && event->type==SDL_EVENT_KEY_DOWN) {
    SDL_Keycode key=event->key.key;
    if(key==SDLK_ESCAPE){s_capture=-1;s_bind_message="Capture cancelled.";}
    else if(key!=SDLK_LCTRL&&key!=SDLK_RCTRL&&key!=SDLK_LSHIFT&&key!=SDLK_RSHIFT&&key!=SDLK_LALT&&key!=SDLK_RALT&&!event->key.repeat) {
      if(StoreBinding(s_capture,key,event->key.mod))s_capture=-1;
    }
    return true;
  }
  if(s_tab!=kSettings) {
    ImGui_ImplSDL3_ProcessEvent(event);
    if(event->type==SDL_EVENT_KEY_DOWN&&event->key.key!=SDLK_ESCAPE)return true;
    return false;
  }
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
  return false;
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
  // Reserve a real work area, so the shared settings window cannot cover
  // the navigation strip. Pointer targets stay outside the resize border.
  ImGuiViewport *viewport=ImGui::GetMainViewport();
  ImVec2 oldPos=viewport->WorkPos,oldSize=viewport->WorkSize;
  viewport->WorkPos.y=72;viewport->WorkSize.y=std::max(120.f,ImGui::GetIO().DisplaySize.y-72);
  if (s_tab == kPerformance) {
    ImGui::SetNextWindowPos({16,76},ImGuiCond_Always);
    ImGui::SetNextWindowSize({width-32.f,std::max(120.f,height-92.f)},ImGuiCond_Always);
    if(ImGui::Begin("Performance",nullptr,kPanelFlags)) {
      int timing=Cv4CpuTimingMode();
      const char *labels[]={"Original SNES","FastROM","FastROM + CPU boost"};
      const char *test=std::getenv("SNESRECOMP_PERFORMANCE_UI_SELFTEST");
      static unsigned frame;
      if(test && ++frame==1)std::fprintf(stderr,"performance initial=%d\n",timing);
      bool open=ImGui::BeginCombo("SNES slowdown reduction",labels[timing]);
      ImVec2 combo=ImGui::GetItemRectMin();
      if(open) {
        for(int i=0;i<3;++i) {
          if(ImGui::Selectable(labels[i],timing==i))Cv4SetCpuTimingMode(i);
          if(test && i==std::atoi(test) && (frame==6||frame==7)) {
            ImVec2 p=ImGui::GetItemRectMin();ImGui::GetIO().AddMousePosEvent(p.x+12,p.y+8);
            ImGui::GetIO().AddMouseButtonEvent(0,frame==6);
          }
        }
        ImGui::EndCombo();
      }
      if(test && (frame==2||frame==3)) {
        ImGui::GetIO().AddMousePosEvent(combo.x+12,combo.y+8);
        ImGui::GetIO().AddMouseButtonEvent(0,frame==2);
      }
      if(test && frame==10)std::fprintf(stderr,"performance selected=%d\n",Cv4CpuTimingMode());
      ImGui::TextWrapped("FastROM accelerates ROM access. CPU boost adds headroom for busy scenes. Video remains at its original NTSC rate; gameplay outside overload keeps its normal speed.");
      ImGui::TextWrapped("HD graphics keep their full selected resolution. Unchanged HD cells are reused automatically.");
    }
    ImGui::End();
  }
  else if (s_tab == kCharacters) Cv4CharacterEditor();
  else if (s_tab == kHd) HdPanel();
  else if (s_tab == kShortcuts) ShortcutPanel();
  else recomp_runtime_ui_render_imgui(static_cast<RecompRuntimeUi *>(ui_ptr));
  viewport->WorkPos=oldPos;viewport->WorkSize=oldSize;
  ImGui::SetNextWindowPos({8,8});
  ImGui::SetNextWindowSize({ImGui::GetIO().DisplaySize.x-16,52});
  ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, ImVec2(10,6));
  ImGui::Begin("Settings tools", nullptr, ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoMove);
  auto button=[&](const char *name,int tab){if(ImGui::Button(name,{0,38})){s_tab=tab;s_capture=-1;}};
  button("Game settings",kSettings);
  ImGui::SameLine();
  button("Character workshop",kCharacters);
  ImGui::SameLine();
  button("HD graphics",kHd);
  ImGui::SameLine();button("Shortcuts",kShortcuts);
  ImGui::SameLine();button("Performance",kPerformance);
  ImGui::SameLine();if(ImGui::Button("Resume",{0,38})){s_capture=-1;recomp_runtime_ui_close(static_cast<RecompRuntimeUi *>(ui_ptr));}
  if(std::getenv("SNESRECOMP_PERFORMANCE_UI_SELFTEST")) {
    static bool reported;
    if(!reported){reported=true;std::fprintf(stderr,"performance navigation fits=%d\n",ImGui::GetItemRectMax().x<ImGui::GetIO().DisplaySize.x-6);}
  }
  ImGui::End();
  ImGui::PopStyleVar();
  ImGui::Render();
  ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
}
