/* Game commands for the opt-in Lua automation bridge (docs/LUA_TCP.md).
 *
 * A -DSNESRECOMP_ENABLE_LUA=ON build started with SNESRECOMP_LUA_PORT lets a
 * local client drive the game through Lua; game.command(name, args) reaches
 * the handler below for what the BizHawk-style API cannot do: capture the
 * presented field and the PPU, save/load a state slot or file, and reset the
 * console.
 * tools/sciv_play.py is the client. Ordinary builds compile this to nothing.
 */
#include "lua_commands.h"

#if SNESRECOMP_ENABLE_LUA
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "common_rtl.h"
#include "debug_capture.h"
#include "hd_render.h"
#include "hd_collect.h"
#include "host_main.h"
#include "lua_bridge.h"
#include "game_performance.h"
#include "character_pack.h"
#include "enemy_pack.h"
#include "workshop_capture.h"
#include "enemy_resources.h"
#include "level_editor.h"
#include "cpu_state.h"
#include "snes/ppu.h"

extern Ppu *g_ppu;
extern unsigned char g_ram[0x20000];

static int Cv4LuaSlot(const char *args, int *slot)
{
    char *end = NULL;
    long value = strtol(args, &end, 10);
    if (!args[0] || *end || value < 0 || value > 9)
        return 0;
    *slot = (int)value;
    return 1;
}

static int Cv4LuaCommand(const char *name, const char *args, char *result, size_t capacity)
{
    int slot;
    if(!strcmp(name,"level_project"))return Cv4LevelLoad(args,result,capacity);
    if(!strcmp(name,"level_room")){snprintf(result,capacity,"%u",Cv4LevelRoom());return 1;}
    if(!strcmp(name,"enemy_resources"))return Cv4EnemyResources(g_ppu,g_ram,args,result,capacity);
    if(!strcmp(name,"enemy_surface")) {
        int ok=Cv4WorkshopCaptureSave(args);
        snprintf(result,capacity,ok?"Native Mode7 workshop surface saved":"No active Mode7 boss surface");return ok;
    }
    if(!strcmp(name,"enemy_snapshot")) {
        FILE *file=fopen(args,"wb");
        if(!file){snprintf(result,capacity,"Cannot write workshop snapshot");return 0;}
        const char *json=Cv4EnemyObservation();
        int ok=fwrite(json,1,strlen(json),file)==strlen(json);
        if(fclose(file))ok=0;
        snprintf(result,capacity,ok?"Workshop snapshot saved":"Cannot save workshop snapshot");return ok;
    }
    if(!strcmp(name,"enemy")) {
        int ok=Cv4EnemyCommand(args[0]?args:"status");
        snprintf(result,capacity,"%s",Cv4EnemyStatus());return ok;
    }
    if(!strcmp(name,"frameinspect")) {
        if(!strcmp(args,"on"))SnesDesktopSetFrameInspection(true);
        else if(!strcmp(args,"off"))SnesDesktopSetFrameInspection(false);
        else if(!strcmp(args,"step"))SnesDesktopAdvanceFrame();
        else if(args[0]) {snprintf(result,capacity,"frameinspect: on|off|step");return 0;}
        snprintf(result,capacity,"{\"enabled\":%d,\"frame\":%u}",SnesDesktopFrameInspection(),SnesDesktopInspectionFrame());
        return 1;
    }
    if(!strcmp(name,"characterhd")) {
        const Cv4CharacterHdFrame *f=Cv4CharacterHd();
        snprintf(result,capacity,"{\"active\":%d,\"pose\":\"%s\",\"x\":%d,\"y\":%d,\"width\":%d,\"height\":%d}",
            f!=NULL,Cv4CharacterPose(),f?f->x:0,f?f->y:0,f?f->width:0,f?f->height:0);
        return 1;
    }
    if (!strcmp(name,"hdhash")) {
        snprintf(result,capacity,"%016llx",(unsigned long long)Cv4HdFrameChecksum());return 1;
    }
    if (!strcmp(name, "performance")) {
        if (!strcmp(args,"fastrom 0")) Cv4SetFastRom(0);
        else if (!strcmp(args,"fastrom 1")) Cv4SetFastRom(1);
        else if (!strcmp(args,"timing 0") || !strcmp(args,"timing 1") || !strcmp(args,"timing 2"))Cv4SetCpuTimingMode(args[7]-'0');
        else if (args[0]) { snprintf(result,capacity,"performance: timing 0|1|2");return 0; }
        snprintf(result,capacity,"{\"cpu_timing\":%d,\"rom_cost\":%u,\"wram_cost\":%u,\"mmio_cost\":%u}",
            Cv4CpuTimingMode(),cpu_region_speed(0x008000),cpu_region_speed(0x7e8000),cpu_region_speed(0x002100));
        return 1;
    }
    if (!strcmp(name, "__reset"))
        return 1;
    if (!strcmp(name, "screenshot"))
        return Cv4CaptureFieldPng(args, result, capacity);
    if (!strcmp(name, "hdshot")) {
        int ok = Cv4HdScreenshot(args);
        snprintf(result, capacity, ok ? "HD frame saved" : "No HD frame or cannot write file");
        return ok;
    }
    if (!strcmp(name, "hd")) {
        if (!strcmp(args, "on")) Cv4HdEnable(1);
        else if (!strcmp(args, "off")) Cv4HdEnable(0);
        else if (!strncmp(args, "scale ", 6)) Cv4HdSetScale(atoi(args + 6));
        else if (!strncmp(args, "layers ", 7)) Cv4HdSetLayerMask(strtoul(args + 7, NULL, 0));
        else if (!strncmp(args, "pack ", 5)) {
            if (!Cv4HdLoadPack(args + 5)) { snprintf(result, capacity, "%s", Cv4HdStatus()); return 0; }
        } else if (args[0]) { snprintf(result, capacity, "hd: on|off|scale N|layers MASK|pack PATH"); return 0; }
        snprintf(result, capacity, "{\"enabled\":%d,\"scale\":%d,\"layers\":%u,\"tiles\":%u,\"art_scale\":%d,\"matched\":%u}",
                 Cv4HdEnabled(), Cv4HdScale(), Cv4HdLayerMask(), Cv4HdPackTiles(), Cv4HdPackScale(), Cv4HdReplacedPixels());
        return 1;
    }
    if (!strcmp(name, "save") || !strcmp(name, "load")) {
        if (!Cv4LuaSlot(args, &slot)) {
            snprintf(result, capacity, "slot must be 0..9");
            return 0;
        }
        RtlSaveLoad(name[0] == 's' ? kSaveLoad_Save : kSaveLoad_Load, slot);
        snprintf(result, capacity, "%s %d", name, slot);
        return 1;
    }
    if (!strcmp(name, "ppu")) {
        /* Layer configuration the widescreen policy depends on, as JSON. */
        if (!Cv4CapturePpuJson(result, capacity)) {
            snprintf(result, capacity, "no ppu");
            return 0;
        }
        return 1;
    }
    if (!strcmp(name, "dump")) {
        int ok = Cv4CaptureVideoDump(args);
        snprintf(result, capacity, ok ? "vram+cgram+oam" : "cannot write '%s'", args);
        return ok;
    }
    if(!strcmp(name,"wram")) {
        int ok=Cv4CaptureWram(args);
        snprintf(result,capacity,ok?"128 KiB native WRAM":"Cannot write native WRAM");return ok;
    }
    if (!strcmp(name, "lines")) {
        FILE *file = fopen(args, "wb");
        int ok = 0;
        if (file) {
            ok = fwrite(Cv4HdLines(), sizeof(Cv4HdLine), kCv4HdLines, file) == kCv4HdLines;
            if (fclose(file)) ok = 0;
        }
        snprintf(result, capacity, ok ? "225 scanline records" : "cannot write '%s'", args);
        return ok;
    }
    if (!strcmp(name, "loadfile")) {
        /* A save state outside the slots, e.g. a debug marker's state.sav. */
        int ok = RtlLoadSnapshot(args);
        snprintf(result, capacity, ok ? "loaded %s" : "cannot load '%s'", args);
        return ok;
    }
    if (!strcmp(name, "layers")) {
        /* Host-only render filter (bit0=BG1 .. bit3=BG4, bit4=OBJ); applies
         * from the next rasterized field. */
        g_snes_ppu_dbg_layer_mask = args[0] ? (uint8_t)strtoul(args, NULL, 0) : 0xff;
        snprintf(result, capacity, "0x%02x", (unsigned)g_snes_ppu_dbg_layer_mask);
        return 1;
    }
    if (!strcmp(name, "reset")) {
        RtlReset(1);   /* keep battery SRAM, like the console's reset button */
        snprintf(result, capacity, "reset");
        return 1;
    }
    snprintf(result, capacity, "unknown command '%s' (screenshot, hdshot, hd, save, load, loadfile, ppu, dump, lines, layers, reset)", name);
    return 0;
}

void Cv4LuaCommandsInstall(void)
{
    lua_bridge_set_game_command_handler(&Cv4LuaCommand);
}
#else
void Cv4LuaCommandsInstall(void) {}
#endif
