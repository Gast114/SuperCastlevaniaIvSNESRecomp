#pragma once

/* Registers the game-command handler of the opt-in Lua bridge (no-op without
 * -DSNESRECOMP_ENABLE_LUA=ON). See lua_commands.c. */
void Cv4LuaCommandsInstall(void);
