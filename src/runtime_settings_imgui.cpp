#include "runtime_settings_imgui.h"
#include "character_pack.h"
#include "enemy_pack.h"
#include "debug_marker.h"
#include "hd_collect.h"
#include "hd_render.h"
#include "game_performance.h"
#include "character_json.h"

#include "recomp_runtime_ui.h"
#include "imgui.h"
#include "imgui_impl_opengl3.h"
#include "imgui_impl_sdl3.h"
#include "opengl.h"
extern "C" {
#include "config.h"
}
#include <cstdlib>
#include <cstdio>
#include <filesystem>
#include <string>
#include <algorithm>
#include <fstream>
#include <iterator>
#include <vector>
#include <cmath>
extern "C" {
#include "host_main.h"
void launcher_ini_kv_write(const char *, const char *, const char *, const char *);
}

static bool s_initialized;
static RecompRuntimeUi *s_runtime_ui;
enum { kSettings, kCharacters, kHd, kShortcuts, kPerformance };
static int s_tab=kSettings, s_capture=-1;
static std::string s_bind_message;
static const ImGuiWindowFlags kPanelFlags=ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoResize|ImGuiWindowFlags_NoCollapse;
static SDL_Window *s_window;
static ImGuiStyle s_base_style;
static std::vector<ImFont *> s_fonts;
static float s_scale=1.f;
static int s_scale_percent;
static float S(float value) { return value*s_scale; }

extern "C" float Cv4RuntimeUiScale(void) { return s_scale; }
extern "C" void Cv4RuntimeUiPanel(float max_width, float max_height) {
  const ImGuiViewport *v=ImGui::GetMainViewport();
  const float width=std::min(S(max_width),v->WorkSize.x-S(24));
  const float height=std::min(S(max_height),v->WorkSize.y-S(16));
  ImGui::SetNextWindowPos({v->WorkPos.x+(v->WorkSize.x-width)*.5f,v->WorkPos.y+S(8)},ImGuiCond_Always);
  ImGui::SetNextWindowSize({width,std::max(S(100),height)},ImGuiCond_Always);
}

// Keep fonts rasterized near their actual display size. Enlarging only the
// original 13px atlas makes text blurry even when the surrounding widgets grow.
static void UpdateUiScale() {
  ImGuiIO &io=ImGui::GetIO();
  const float density=std::max(1.f,io.DisplayFramebufferScale.y);
  const float dpi=SDL_GetWindowDisplayScale(s_window)/density;
  const float resolution=std::min(io.DisplaySize.x/1920.f,io.DisplaySize.y/1080.f);
  const float fit=std::max(1.f,std::min(io.DisplaySize.x/800.f,io.DisplaySize.y/600.f));
  s_scale=std::min(fit,s_scale_percent?s_scale_percent/100.f:std::max({1.f,dpi,resolution}));
  s_scale=std::clamp(s_scale,1.f,2.5f);
  ImFont *font=s_fonts.front();
  for(ImFont *candidate:s_fonts)
    if(std::abs(candidate->FontSize-18*s_scale)<std::abs(font->FontSize-18*s_scale))font=candidate;
  io.FontDefault=font;
  io.FontGlobalScale=18*s_scale/font->FontSize;
  ImGui::GetStyle()=s_base_style;
  ImGui::GetStyle().ScaleAllSizes(s_scale);
}

static float DrawNavigation(RecompRuntimeUi *ui) {
  static unsigned test_frame;
  const char *pick=std::getenv("SNESRECOMP_UI_SCALE_PICK");
  if(std::getenv("SNESRECOMP_UI_SCALE_SELFTEST"))++test_frame;
  const float available=ImGui::GetIO().DisplaySize.x-S(16);
  const char *names[]={"Game settings","Character workshop","HD graphics","Shortcuts","Performance","Resume"};
  const ImGuiStyle &style=ImGui::GetStyle();
  const float row=S(40), gap=style.ItemSpacing.x, padding=S(10);
  float used=0;int rows=1;
  for(const char *name:names) {
    float w=ImGui::CalcTextSize(name).x+style.FramePadding.x*2+S(12);
    if(used && used+gap+w>available-padding*2){++rows;used=0;}
    used+=(used?gap:0)+w;
  }
  const float height=padding*2+rows*row+(rows-1)*style.ItemSpacing.y+ImGui::GetFrameHeight()+style.ItemSpacing.y;
  ImGui::SetNextWindowPos({S(8),S(8)});
  ImGui::SetNextWindowSize({available,height});
  ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding,{padding,padding});
  ImGui::Begin("Settings tools",nullptr,ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoMove);
  used=0;bool fits=true;
  for(int i=0;i<6;++i) {
    float w=ImGui::CalcTextSize(names[i]).x+style.FramePadding.x*2+S(12);
    if(used && used+gap+w>available-padding*2)used=0;
    else if(used)ImGui::SameLine();
    const bool active=i==s_tab;
    if(active) {
      ImGui::PushStyleColor(ImGuiCol_Button,style.Colors[ImGuiCol_HeaderActive]);
      ImGui::PushStyleColor(ImGuiCol_Text,{.025f,.07f,.10f,1});
    }
    if(ImGui::Button(names[i],{w,row})) {
      s_capture=-1;
      if(i==5)recomp_runtime_ui_close(ui);else s_tab=i;
    }
    if(active)ImGui::PopStyleColor(2);
    fits= fits && ImGui::GetItemRectMax().x<=ImGui::GetIO().DisplaySize.x-S(8);
    used+=(used?gap:0)+w;
  }
  const char *sizes[]={"Automatic","100%","125%","150%","175%","200%","250%"};
  const int values[]={0,100,125,150,175,200,250};
  int selected=0;for(int i=1;i<7;++i)if(values[i]==s_scale_percent)selected=i;
  ImGui::SetNextItemWidth(S(150));
  if(ImGui::BeginCombo("Menu size",sizes[selected])) {
    for(int i=0;i<7;++i) {
      if(ImGui::Selectable(sizes[i],selected==i)) {
        s_scale_percent=values[i];
        std::ofstream file("ui_settings.json");file<<"{\"menu_scale\":"<<s_scale_percent<<"}\n";
      }
      if(pick && values[i]==std::atoi(pick) && (test_frame==6||test_frame==7)) {
        const ImVec2 pos=ImGui::GetItemRectMin();
        ImGui::GetIO().AddMousePosEvent(pos.x+S(12),pos.y+S(8));
        ImGui::GetIO().AddMouseButtonEvent(0,test_frame==6);
      }
    }
    ImGui::EndCombo();
  }
  if(pick && (test_frame==2||test_frame==3)) {
    const ImVec2 pos=ImGui::GetItemRectMin();
    ImGui::GetIO().AddMousePosEvent(pos.x+S(12),pos.y+S(8));
    ImGui::GetIO().AddMouseButtonEvent(0,test_frame==2);
  }
  if(available>S(520)){ImGui::SameLine();ImGui::TextDisabled("%.0f%%  |  Escape: back",s_scale*100);}
  if(std::getenv("SNESRECOMP_PERFORMANCE_UI_SELFTEST")) {
    static bool reported;if(!reported){reported=true;std::fprintf(stderr,"performance navigation fits=%d\n",fits);}
  }
  if(std::getenv("SNESRECOMP_UI_SCALE_SELFTEST")) {
    if(test_frame==12) {
      std::fprintf(stderr,"menu layout display=%.0fx%.0f scale=%.2f font=%.1f nav_bottom=%.1f fits=%d\n",ImGui::GetIO().DisplaySize.x,ImGui::GetIO().DisplaySize.y,s_scale,ImGui::GetFontSize(),S(8)+height,fits);
      OpenGLRenderer_RequestScreenshot();
    }
  }
  ImGui::End();ImGui::PopStyleVar();
  return S(8)+height;
}

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
  Cv4RuntimeUiPanel(1120,1100);
  if(ImGui::Begin("Shortcuts",nullptr,kPanelFlags)) {
    ImGui::TextWrapped("Select a binding and press your new key combination. Escape cancels.");
    if(s_capture>=0)ImGui::TextColored({1,.8f,.3f,1},"Waiting for key combination... Escape cancels.");
    if(!s_bind_message.empty())ImGui::TextWrapped("%s",s_bind_message.c_str());
    static ImGuiTextFilter filter;filter.Draw("Filter actions",std::min(S(360),ImGui::GetContentRegionAvail().x*.65f));
    const float footer=ImGui::GetFrameHeight()+ImGui::GetStyle().ItemSpacing.y;
    if(ImGui::BeginTable("Bindings",3,ImGuiTableFlags_RowBg|ImGuiTableFlags_BordersInnerH|ImGuiTableFlags_ScrollY,{0,std::max(S(80),ImGui::GetContentRegionAvail().y-footer)})) {
      ImGui::TableSetupColumn("Action",ImGuiTableColumnFlags_WidthStretch);
      ImGui::TableSetupColumn("Binding",ImGuiTableColumnFlags_WidthFixed,S(240));
      ImGui::TableSetupColumn("",ImGuiTableColumnFlags_WidthFixed,S(90));
      ImGui::TableSetupScrollFreeze(0,1);ImGui::TableHeadersRow();
      auto row=[&](int command,const char *label) {
        if(!filter.PassFilter(label))return;
        ImGui::PushID(command);ImGui::TableNextRow();ImGui::TableNextColumn();ImGui::AlignTextToFramePadding();ImGui::TextWrapped("%s",label);ImGui::TableNextColumn();
        char binding[256];ConfigGetCommandBinding(command,binding,sizeof(binding));
        if(ImGui::Button(s_capture==command?"Press keys...":binding,{-1,S(42)})) {s_capture=command;s_bind_message.clear();}
        if(testing&&command==kKeys_ToggleHD) {
          ImVec2 p=ImGui::GetItemRectMin();ImGui::GetIO().AddMousePosEvent(p.x+12,p.y+12);
          if(test_frame==2||test_frame==9||test_frame==16||test_frame==29)ImGui::GetIO().AddMouseButtonEvent(0,true);
          if(test_frame==3||test_frame==10||test_frame==17||test_frame==30)ImGui::GetIO().AddMouseButtonEvent(0,false);
        }
        // Keep the menu reachable, including a way back to Escape (Escape
        // cancels ordinary key capture). Other actions can be unbound.
        ImGui::TableNextColumn();
        if(ImGui::Button(command==kKeys_OpenSettings?"Default":"Clear",{-1,S(42)})){
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
      row(kKeys_FrameInspection,"Frame by frame: pause / resume");
      row(kKeys_FrameAdvance,"Frame by frame: next frame");
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
    if(ImGui::CollapsingHeader("Controller shortcuts and help")) {
      ImGui::SetNextItemWidth(S(180));gesture(true,"Debug marker",g_config.debug_gesture,"Select+L3");
      ImGui::SetNextItemWidth(S(180));gesture(false,"Rewind",g_config.rewind_gesture,"Select+R3");
      ImGui::TextWrapped("Clear removes a binding. Free an occupied key before assigning it to another action. Debug marker saves a picture, state and note; Ctrl+Enter / pad A saves, Escape / pad B cancels.");
    }
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
  Cv4RuntimeUiPanel(850,1100);
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
  int resolution=Cv4HdScale();
  const int resolutions[]={2,4,6,10};
  const std::string resolutionLabel=std::to_string(resolution)+"x";
  if(ImGui::BeginCombo("HD render resolution",resolutionLabel.c_str())) {
    for(int value:resolutions) {
      const std::string label=std::to_string(value)+"x"+(value==4?" (recommended)":"");
      if(ImGui::Selectable(label.c_str(),resolution==value))Cv4HdSetScale(value);
    }
    ImGui::EndCombo();
  }
  ImGui::TextWrapped("4x preserves the detail of 4x artwork, including on a 4K screen. Higher render resolutions need more processing power.");
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
  ImGui::TextWrapped("Missing artwork and unsupported effects keep their original graphics. Your artwork keeps its intended size at different source resolutions.");
  ImGui::SeparatorText("Enemy graphics");
  bool enemiesCollect=Cv4EnemyCapturing()!=0;
  if(ImGui::Checkbox("Collect enemy poses while playing",&enemiesCollect))
    Cv4EnemyCommand(enemiesCollect?"capture on":"capture off");
  const std::string enemySelection=Cv4EnemySelection();
  if(ImGui::BeginCombo("Enemy pack",enemySelection.empty()?"Original enemies":enemySelection.c_str())) {
    if(ImGui::Selectable("Original enemies",enemySelection.empty()))Cv4EnemyCommand("off");
    std::error_code error;
    for(const auto &entry:std::filesystem::directory_iterator("enemy_packs",error)) {
      if(!entry.is_directory(error)||entry.path().filename()=="native-template"||
         !std::filesystem::exists(entry.path()/"enemies.json",error))continue;
      auto name=entry.path().filename().string();
      if(ImGui::Selectable(name.c_str(),name==enemySelection))Cv4EnemyCommand(("pack "+name).c_str());
    }
    ImGui::EndCombo();
  }
  if(ImGui::Button("Reload enemy images"))Cv4EnemyCommand("reload");
  ImGui::TextWrapped("%s",Cv4EnemyStatus());
  ImGui::TextWrapped("Skeleton poses are collected automatically. Finished images can be prepared with the enemy import tool; missing poses keep their original appearance.");
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
  s_base_style=ImGui::GetStyle();
  s_window=static_cast<SDL_Window *>(window);
  s_fonts.clear();
  for(float size:{18.f,22.f,27.f,32.f,36.f,40.f,45.f}) {
    ImFontConfig config;config.SizePixels=size;
    ImFont *font=nullptr;
    if(std::filesystem::exists("assets/fonts/LatoLatin-Regular.ttf"))
      font=io.Fonts->AddFontFromFileTTF("assets/fonts/LatoLatin-Regular.ttf",size,&config);
    if(!font)font=io.Fonts->AddFontDefault(&config);
    s_fonts.push_back(font);
  }
  s_scale_percent=0;
  try {
    std::ifstream file("ui_settings.json");
    if(file) {
      std::string data((std::istreambuf_iterator<char>(file)),{});
      int n=character_json::Reader(data).read().at("menu_scale").number();
      if(n==100||n==125||n==150||n==175||n==200||n==250)s_scale_percent=n;
    }
  }catch(...) { s_scale_percent=0; }
  if(const char *test=std::getenv("SNESRECOMP_UI_SCALE_SELFTEST")) {
    int w=0,h=0;if(std::sscanf(test,"%dx%d",&w,&h)==2&&w>=800&&h>=600)SDL_SetWindowSize(s_window,w,h);
  }
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
  s_fonts.clear();s_window=nullptr;
}

extern "C" bool Cv4RuntimeSettingsImGuiProcessEvent(const void *event_ptr) {
  if (!s_initialized || !event_ptr) return false;
  const SDL_Event *event = static_cast<const SDL_Event *>(event_ptr);
  if(SnesDesktopFrameInspection()&&!Cv4DebugMarkerIsOpen()&&
      (!s_runtime_ui||!recomp_runtime_ui_is_open(s_runtime_ui))) {
    // The floating inspection controls receive pointer input. Game keys and
    // remappable inspection shortcuts still go through the host dispatcher.
    if(event->type==SDL_EVENT_MOUSE_MOTION||event->type==SDL_EVENT_MOUSE_BUTTON_DOWN||event->type==SDL_EVENT_MOUSE_BUTTON_UP||event->type==SDL_EVENT_MOUSE_WHEEL) {
      ImGui_ImplSDL3_ProcessEvent(event);
      return ImGui::GetIO().WantCaptureMouse;
    }
    return false;
  }
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
  s_runtime_ui=static_cast<RecompRuntimeUi *>(ui_ptr);
  if (Cv4DebugMarkerIsOpen()) {
    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplSDL3_NewFrame();
    UpdateUiScale();
    ImGui::NewFrame();
    Cv4DebugMarkerDraw();
    ImGui::Render();
    ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
    return;
  }
  bool menu=ui_ptr&&recomp_runtime_ui_is_open(static_cast<RecompRuntimeUi *>(ui_ptr));
  if(!menu) {
    if(!SnesDesktopFrameInspection())return;
    ImGui_ImplOpenGL3_NewFrame();ImGui_ImplSDL3_NewFrame();UpdateUiScale();ImGui::NewFrame();
    static unsigned inspect_test_tick,inspect_test_start;
    bool inspect_test=std::getenv("SNESRECOMP_FRAME_INSPECTION_UI_SELFTEST")!=nullptr;
    if(inspect_test&&++inspect_test_tick==1)inspect_test_start=SnesDesktopInspectionFrame();
    auto test_click=[&](unsigned tick) {
      if(inspect_test&&(inspect_test_tick==tick||inspect_test_tick==tick+1)) {
        ImVec2 pos=ImGui::GetItemRectMin();ImGui::GetIO().AddMousePosEvent(pos.x+15,pos.y+15);
        ImGui::GetIO().AddMouseButtonEvent(0,inspect_test_tick==tick);
      }
    };
    ImGui::SetNextWindowPos({width-S(12),S(80)},ImGuiCond_Once,{1,0});
    ImGui::SetNextWindowBgAlpha(.90f);
    if(ImGui::Begin("Frame by frame",nullptr,ImGuiWindowFlags_AlwaysAutoResize|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoResize)) {
    char toggle[256],step[256];
    ConfigGetCommandBinding(kKeys_FrameInspection,toggle,sizeof(toggle));ConfigGetCommandBinding(kKeys_FrameAdvance,step,sizeof(step));
    ImGui::Text("Frame %u",SnesDesktopInspectionFrame());
    if(ImGui::Button("Next frame",{S(130),S(40)}))SnesDesktopAdvanceFrame();
    test_click(2);
    ImGui::SameLine();if(ImGui::Button("Resume",{S(100),S(40)})) {
      SnesDesktopSetFrameInspection(false);
      if(inspect_test){std::fprintf(stderr,"inspection ui resumed=1\n");std::fflush(stderr);}
    }
    test_click(8);
    if(inspect_test&&inspect_test_tick==7) {
      std::fprintf(stderr,"inspection ui one step=%d\n",SnesDesktopInspectionFrame()==inspect_test_start+1);
      std::fflush(stderr);
      OpenGLRenderer_RequestScreenshot();
    }
    ImGui::Text("%s: next | %s: resume",step,toggle);
    ImGui::TextUnformatted("Hold a direction or action while stepping.");
    }
    ImGui::End();ImGui::Render();ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
    return;
  }
  ImGui_ImplOpenGL3_NewFrame();
  ImGui_ImplSDL3_NewFrame();
  UpdateUiScale();
  ImGui::NewFrame();
  // Reserve a real work area, so the shared settings window cannot cover
  // the navigation strip. Pointer targets stay outside the resize border.
  ImGuiViewport *viewport=ImGui::GetMainViewport();
  ImVec2 oldPos=viewport->WorkPos,oldSize=viewport->WorkSize;
  const float nav_bottom=DrawNavigation(static_cast<RecompRuntimeUi *>(ui_ptr));
  viewport->WorkPos.y=nav_bottom;viewport->WorkSize.y=std::max(S(120),ImGui::GetIO().DisplaySize.y-nav_bottom);
  if (s_tab == kPerformance) {
    Cv4RuntimeUiPanel(1000,1100);
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
      ImGui::SeparatorText("Frame by frame");
      ImGui::TextWrapped("Freeze the picture without dimming. Hold a direction or action and advance one frame at a time. Shortcuts can be changed under Shortcuts.");
      if(ImGui::Button("Inspect frames",{S(180),S(40)})) {
        SnesDesktopSetFrameInspection(true);
        recomp_runtime_ui_close(static_cast<RecompRuntimeUi *>(ui_ptr));
      }
    }
    ImGui::End();
  }
  else if (s_tab == kCharacters) Cv4CharacterEditor();
  else if (s_tab == kHd) HdPanel();
  else if (s_tab == kShortcuts) ShortcutPanel();
  else recomp_runtime_ui_render_imgui(static_cast<RecompRuntimeUi *>(ui_ptr));
  viewport->WorkPos=oldPos;viewport->WorkSize=oldSize;
  ImGui::Render();
  ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
}
