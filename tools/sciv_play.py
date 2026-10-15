"""Drive a running Super Castlevania IV session through the Lua TCP bridge.

Needs a build configured with -DSNESRECOMP_ENABLE_LUA=ON. The session runs in
an isolated folder (never the player's config, saves or character packs) and
starts paused: the game only advances when a command says so, which makes
every step reproducible. Output is JSON, one object per command.

  python tools/sciv_play.py start --build-dir build-lua [--widescreen] [--visible] [--fast]
  python tools/sciv_play.py state                 # frame + named RAM fields
  python tools/sciv_play.py press Right+B 30      # hold buttons for N frames
  python tools/sciv_play.py wait 60               # advance N frames, no input
  python tools/sciv_play.py shot out.png          # last rasterized field
  python tools/sciv_play.py save 1 | load 1 | reset
  python tools/sciv_play.py ppu                   # BG modes, tilemaps, scroll, widescreen margins
  python tools/sciv_play.py peek 0x54a 2          # read WRAM (bytes, little endian)
  python tools/sciv_play.py poke 0x1f0 3          # write one WRAM byte
  python tools/sciv_play.py eval "return emu.framecount()"
  python tools/sciv_play.py stop

Buttons: B Y Select Start Up Down Left Right A X L R, joined with '+'.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import sciv_test_support as sciv

sys.path.insert(0, str(sciv.ROOT / 'snesrecomp' / 'tools'))
from lua_tcp import LuaClient  # noqa: E402

SESSION = sciv.ROOT / 'build-play' / 'session.json'
BUTTONS = ('B', 'Y', 'Select', 'Start', 'Up', 'Down', 'Left', 'Right', 'A', 'X', 'L', 'R')

# Named WRAM fields (D:\Reverse Engineering\docs\sc4\analysis.md and src/).
# (address, bytes). Extend as more of the RAM map is identified.
FIELDS = {
    'game_mode': (0x32, 1),     # 0 logo, 1 title menu, 2 attract, 3 confirm, 4 game, 5 options, 6 continue, 7 ending
    'mode_step': (0x34, 1),
    'frame_counter': (0x3A, 1),
    'nmi_busy': (0x3C, 1),
    'level_phase': (0x70, 1),   # level load 1..5 while game_mode = 4
    'game_phase': (0x72, 1),
    'block': (0x86, 1),         # running block index, 0 = 1-1
    'camera_x': (0x1C, 2),
    'camera_y': (0x1E, 2),
    'camera_lock_left': (0xA0, 2),
    'joy_held': (0x20, 2),
    'joy_new': (0x28, 2),
    'player_pose': (0x540, 2),
    'player_x': (0x54A, 2),
    'player_y': (0x54E, 2),
    'player_state': (0x552, 2),
}


def out(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def session():
    if not SESSION.exists():
        raise SystemExit('no session; run: sciv_play.py start --build-dir <lua build>')
    return json.loads(SESSION.read_text())


def client():
    return LuaClient(port=session()['port'])


def wait_idle(lua, timeout=600):
    """Block until the running coroutine (if any) has finished."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = lua.command('status')
        if status.get('error'):
            raise RuntimeError(status['error'])
        if not status['running']:
            return status
        time.sleep(0.01)
    raise TimeoutError('game did not finish the requested frames')


def advance(lua, frames, buttons=()):
    """Run exactly `frames` frames from a paused machine, holding `buttons`."""
    held = '{' + ','.join(f'{b}=true' for b in buttons) + '}'
    lua.command('pause')
    lua.run(f'for i=1,{int(frames)} do joypad.set({held},1) emu.frameadvance() end')
    return wait_idle(lua)


def parse_buttons(text):
    names = {b.lower(): b for b in BUTTONS}
    result = []
    for part in text.split('+'):
        if part.lower() not in names:
            raise SystemExit(f'unknown button {part!r}; use {"/".join(BUTTONS)}')
        result.append(names[part.lower()])
    return result


def read_state(lua):
    reads = ','.join(
        f'mainmemory.read_u{8 * size}{"_le" if size > 1 else ""}({addr})'
        for addr, size in FIELDS.values())
    result = lua.eval(f'return emu.framecount(),{reads}')
    values = [int(v) for v in result['values']]
    state = {'frame': values[0], 'paused': result['paused']}
    state.update({name: value for name, value in zip(FIELDS, values[1:])})
    return state


def start(args):
    if SESSION.exists():
        try:
            with client() as lua:
                lua.command('ping')
            raise SystemExit('a session is already running; stop it first')
        except OSError:
            pass
    build = sciv.build_dir(args)
    folder = (sciv.ROOT / 'build-play' / 'game').resolve()
    graphics = {'Widescreen': int(args.widescreen)}
    general = {'DisableFrameDelay': 1} if args.fast else {}
    sciv.prepare(folder, build, {'Graphics': graphics, 'General': general})
    env = sciv.clean_env(SNESRECOMP_LUA_PORT=args.port, SNESRECOMP_LUA_PAUSED=1)
    log = (folder / 'game.log').open('w')
    flags = subprocess.DETACHED_PROCESS if os.name == 'nt' else 0
    proc = subprocess.Popen([str(folder / sciv.EXE_NAME), str(Path(args.rom).resolve())],
                            cwd=folder, env=env, stdout=log, stderr=log,
                            startupinfo=None if args.visible else sciv.hidden_window(),
                            creationflags=flags)
    SESSION.write_text(json.dumps({'pid': proc.pid, 'port': args.port, 'folder': str(folder)}))
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with LuaClient(port=args.port, timeout=2) as lua:
                out({'started': True, 'pid': proc.pid, 'folder': str(folder), **read_state(lua)})
                return
        except OSError:
            if proc.poll() is not None:
                raise SystemExit(f'game exited ({proc.returncode}); see {folder / "game.log"}')
            time.sleep(0.2)
    raise SystemExit('the game did not open the Lua port; is this a SNESRECOMP_ENABLE_LUA build?')


def stop(_args):
    info = session()
    try:
        subprocess.run(['taskkill', '/PID', str(info['pid']), '/F'] if os.name == 'nt'
                       else ['kill', str(info['pid'])], capture_output=True)
    finally:
        SESSION.unlink(missing_ok=True)
    out({'stopped': info['pid']})


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('start')
    sciv.add_build_arg(p)
    p.add_argument('--rom', default=str(sciv.ROOT / 'Super Castlevania IV (USA).sfc'))
    p.add_argument('--port', type=int, default=4380)
    p.add_argument('--widescreen', action='store_true')
    p.add_argument('--visible', action='store_true', help='show the game window')
    p.add_argument('--fast', action='store_true', help='run frames unthrottled')
    sub.add_parser('stop')
    sub.add_parser('state')
    p = sub.add_parser('press')
    p.add_argument('buttons')
    p.add_argument('frames', type=int, nargs='?', default=1)
    p = sub.add_parser('wait')
    p.add_argument('frames', type=int)
    p = sub.add_parser('shot')
    p.add_argument('path')
    for name in ('save', 'load'):
        sub.add_parser(name).add_argument('slot', type=int)
    sub.add_parser('reset')
    sub.add_parser('ppu')
    p = sub.add_parser('peek')
    p.add_argument('addr', type=lambda v: int(v, 0))
    p.add_argument('count', type=int, nargs='?', default=1)
    p = sub.add_parser('poke')
    p.add_argument('addr', type=lambda v: int(v, 0))
    p.add_argument('value', type=lambda v: int(v, 0))
    p = sub.add_parser('eval')
    p.add_argument('source')
    args = parser.parse_args()

    if args.cmd == 'start':
        return start(args)
    if args.cmd == 'stop':
        return stop(args)
    with client() as lua:
        if args.cmd == 'state':
            out(read_state(lua))
        elif args.cmd in ('press', 'wait'):
            buttons = parse_buttons(args.buttons) if args.cmd == 'press' else ()
            advance(lua, args.frames, buttons)
            out(read_state(lua))
        elif args.cmd == 'shot':
            path = str(Path(args.path).resolve())
            size = lua.eval(f'return game.command("screenshot", {json.dumps(path)})')['values'][0]
            out({'screenshot': path, 'size': size})
        elif args.cmd in ('save', 'load'):
            result = lua.eval(f'return game.command("{args.cmd}", "{args.slot}")')['values'][0]
            out({'result': result, **read_state(lua)})
        elif args.cmd == 'ppu':
            out(json.loads(lua.eval('return game.command("ppu")')['values'][0]))
        elif args.cmd == 'reset':
            lua.eval('return game.command("reset")')
            out(read_state(lua))
        elif args.cmd == 'peek':
            values = lua.eval(f'local t={{}} for i=0,{args.count - 1} do t[#t+1]=mainmemory.read_u8({args.addr}+i) end '
                              'return table.concat(t,",")')['values'][0]
            data = [int(v) for v in values.split(',')]
            out({'addr': hex(args.addr), 'bytes': data, 'le': sum(b << (8 * i) for i, b in enumerate(data))})
        elif args.cmd == 'poke':
            lua.eval(f'mainmemory.write_u8({args.addr},{args.value})')
            out({'addr': hex(args.addr), 'written': args.value})
        elif args.cmd == 'eval':
            out(lua.eval(args.source))


if __name__ == '__main__':
    main()
