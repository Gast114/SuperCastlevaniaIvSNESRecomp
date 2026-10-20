#include "game_performance.h"
#include "character_json.h"
#include <cstdlib>
#include <fstream>
#include <iterator>
extern "C" {
#include "cpu_state.h"
extern unsigned char g_ram[0x20000];
}
namespace {
bool initialized=false;
int mode=2;
void Init() {
    if(initialized)return;
    initialized=true;
    std::ifstream file("performance_settings.json");
    if(file) {
        try {
            std::string text((std::istreambuf_iterator<char>(file)),{});
            int value=character_json::Reader(text).read().at("cpu_timing").number();
            mode=value>=0&&value<=2?value:0;
        } catch(...) { mode=0; }
    }
    if(const char *value=std::getenv("SNESRECOMP_CV4_FASTROM"))mode=std::atoi(value)!=0;
    if(const char *value=std::getenv("SNESRECOMP_CV4_CPU_TIMING")) {
        int n=std::atoi(value);mode=n>=0&&n<=2?n:0;
    }
}
}
extern "C" int Cv4CpuTimingMode(void) { Init();return mode; }
extern "C" int Cv4FastRomEnabled(void) { return Cv4CpuTimingMode()!=0; }
extern "C" void Cv4SetFastRom(int enabled) { Cv4SetCpuTimingMode(enabled?1:0); }
extern "C" void Cv4SetCpuTimingMode(int value) {
    Init();mode=value>=0&&value<=2?value:0;
    std::ofstream file("performance_settings.json");file<<"{\"cpu_timing\":"<<mode<<"}\n";
}
extern "C" void Cv4PerformanceBeforeFrame(void) {
    Init();
    // This is transfer timing, not additional video frames or a larger
    // master-clock budget. Loading a state keeps the user's host preference.
    g_cpu_bus_policy=g_ram[0x32]==4?mode:0;
}
