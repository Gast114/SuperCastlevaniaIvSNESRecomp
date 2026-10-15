/* Game commands for the opt-in Lua automation bridge (docs/LUA_TCP.md).
 *
 * A -DSNESRECOMP_ENABLE_LUA=ON build started with SNESRECOMP_LUA_PORT lets a
 * local client drive the game through Lua; game.command(name, args) reaches
 * the handler below for what the BizHawk-style API cannot do: capture the
 * presented field, save/load a state slot, and reset the console.
 * tools/sciv_play.py is the client. Ordinary builds compile this to nothing.
 */
#include "lua_commands.h"

#if SNESRECOMP_ENABLE_LUA
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "common_rtl.h"
#include "host_main.h"
#include "lua_bridge.h"
#include "snes/ppu.h"
#include "third_party/stb_image_write.h"

extern Ppu *g_ppu;

/* The last rasterized field as RGB PNG (renderBuffer is 0x00RRGGBB). */
static int Cv4LuaScreenshot(const char *path, char *result, size_t capacity)
{
    int w = snesrecomp_desktop_frame_width(), h = snesrecomp_desktop_frame_height();
    if (!g_ppu || !g_ppu->renderBuffer || w <= 0 || h <= 0 || !path[0]) {
        snprintf(result, capacity, "no frame to capture (or empty path)");
        return 0;
    }
    uint8_t *rgb = malloc((size_t)w * h * 3);
    if (!rgb) {
        snprintf(result, capacity, "out of memory");
        return 0;
    }
    for (int y = 0; y < h; y++) {
        const uint32_t *row = (const uint32_t *)(g_ppu->renderBuffer + (size_t)y * g_ppu->renderPitch);
        for (int x = 0; x < w; x++) {
            uint8_t *out = &rgb[((size_t)y * w + x) * 3];
            out[0] = (uint8_t)(row[x] >> 16);
            out[1] = (uint8_t)(row[x] >> 8);
            out[2] = (uint8_t)row[x];
        }
    }
    int ok = stbi_write_png(path, w, h, 3, rgb, w * 3);
    free(rgb);
    if (!ok) {
        snprintf(result, capacity, "cannot write %s", path);
        return 0;
    }
    snprintf(result, capacity, "%dx%d", w, h);
    return 1;
}

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
    if (!strcmp(name, "__reset"))
        return 1;
    if (!strcmp(name, "screenshot"))
        return Cv4LuaScreenshot(args, result, capacity);
    if (!strcmp(name, "save") || !strcmp(name, "load")) {
        if (!Cv4LuaSlot(args, &slot)) {
            snprintf(result, capacity, "slot must be 0..9");
            return 0;
        }
        RtlSaveLoad(name[0] == 's' ? kSaveLoad_Save : kSaveLoad_Load, slot);
        snprintf(result, capacity, "%s %d", name, slot);
        return 1;
    }
    if (!strcmp(name, "reset")) {
        RtlReset(1);   /* keep battery SRAM, like the console's reset button */
        snprintf(result, capacity, "reset");
        return 1;
    }
    snprintf(result, capacity, "unknown command '%s' (screenshot, save, load, reset)", name);
    return 0;
}

void Cv4LuaCommandsInstall(void)
{
    lua_bridge_set_game_command_handler(&Cv4LuaCommand);
}
#else
void Cv4LuaCommandsInstall(void) {}
#endif
