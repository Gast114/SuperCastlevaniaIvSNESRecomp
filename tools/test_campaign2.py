"""Exercise the native second quest in an isolated Lua-enabled game copy.

The ending fixture enters the cartridge's final fade handler, not a host
approximation of its difficulty. It does not claim a full-game playthrough.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time

import sciv_play as play
import sciv_test_support as sciv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, required=True)
    sciv.add_build_arg(parser)
    args = parser.parse_args()
    build = sciv.build_dir(args)
    work = sciv.work_dir(build, 'second-quest-check-')
    exe = sciv.prepare(work / 'game', build, {
        'General': {'DisableFrameDelay': 1}, 'Graphics': {'Widescreen': 1}})
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    report = {'passed': False, 'full_game_playthrough': False, 'checks': [],
              'rom_sha256': hashlib.sha256(args.rom.read_bytes()).hexdigest()}
    lua = None
    with (work / 'game/game.log').open('w') as log:
        proc = subprocess.Popen([str(exe), str(args.rom.resolve())], cwd=work / 'game',
            env=sciv.clean_env(SNESRECOMP_LUA_PORT=port, SNESRECOMP_LUA_PAUSED=1),
            stdout=log, stderr=log, startupinfo=sciv.hidden_window())
        try:
            for _ in range(200):
                try:
                    lua = play.LuaClient(port=port)
                    lua.command('ping')
                    break
                except OSError:
                    if proc.poll() is not None:
                        raise RuntimeError('Game exited; see game.log')
                    time.sleep(.05)
            if lua is None:
                raise RuntimeError('No Lua bridge; use a Lua-enabled build')

            def command(name, arg=''):
                result = lua.eval(f'return game.command({json.dumps(name)},{json.dumps(str(arg))})')
                if result.get('error'):
                    raise RuntimeError(result)
                return result['values'][0]

            def words(*addresses):
                return list(map(int, lua.eval('return ' + ','.join(
                    f'mainmemory.read_u16_le({a})' for a in addresses))['values']))

            def write(**values):
                lua.eval(';'.join(f'mainmemory.write_u16_le({int(a,16)},{v})'
                                  for a, v in values.items()))

            def menu_start(second=False):
                command('reset')
                play.advance(lua, 240)
                play.advance(lua, 2, ('Start',))
                play.advance(lua, 50)
                assert words(0x32)[0] == 1, words(0x32, 0x34)
                if second:
                    play.advance(lua, 2, ('Down',))
                    play.advance(lua, 68)
                    assert words(0x1e02)[0] == 3, 'NEW GAME+ cursor missing'
                play.advance(lua, 2, ('Start',))
                if second:
                    for _ in range(120):
                        play.advance(lua, 1)
                        if words(0x11e0)[0] == 0xc402:
                            break
                    assert words(0x11e0)[0] == 0xc402, 'No pending quest request'
                    command('save',2)
                    command('load',0)
                    play.advance(lua,2)
                    assert words(0x88,0x11e0) == [0,0]
                    command('load',2)
                    assert words(0x11e0)[0] == 0xc402
                for _ in range(4):
                    play.advance(lua, 180)
                    if words(0x32, 0x70) == [4, 5]:
                        break
                    play.advance(lua, 2, ('Start',))
                assert words(0x32, 0x70) == [4, 5], words(0x32, 0x70)
                return dict(zip(('mode','level_phase','block','quest','difficulty','request'),
                                words(0x32,0x70,0x86,0x88,0x84,0x11e0)))

            normal = menu_start()
            assert normal['quest'] == 0 and normal['request'] == 0, normal
            command('save', 0)
            command('screenshot', work / 'start.png')
            hard = menu_start(True)
            assert hard['quest'] == 1 and hard['request'] == 0, hard
            assert hard['block'] == normal['block'] == 0
            assert hard['difficulty'] == normal['difficulty'] + 16, (normal, hard)
            command('save', 1)
            command('screenshot', work / 'new-game-plus.png')
            report['menu_start'] = normal
            report['menu_new_game_plus'] = hard
            report['checks'].append('Menu NEW GAME+ starts native block zero with second-quest difficulty')

            # Save/load must preserve native quest and never retain a stale
            # host request when a first-quest state is restored.
            command('load', 0)
            play.advance(lua, 2)
            assert words(0x88, 0x11e0) == [0,0]
            command('load', 1)
            play.advance(lua, 2)
            assert words(0x88, 0x11e0) == [1,0]
            report['checks'].append('Native quest and pending confirmation follow save/load without host-static state')

            # Real final ending handler $03:FCAE: the last fade tick naturally
            # writes $88=1, block0, phase3. No host NEW GAME+ request is armed.
            command('load', 0)
            write(**{'32':7, '1c10':18, '1e80':1, '3a':7, '11e0':0})
            for _ in range(20):
                play.advance(lua,1)
                if words(0x32)[0] == 4:
                    break
            ending = dict(zip(('mode','level_phase','block','quest','request'),
                              words(0x32,0x70,0x86,0x88,0x11e0)))
            assert ending == dict(mode=4,level_phase=3,block=0,quest=1,request=0), ending
            for _ in range(100):
                play.advance(lua,1)
                if words(0x70)[0] == 5:
                    break
            assert words(0x70,0x84,0x88) == [5,hard['difficulty'],1]
            report['native_ending_restart'] = ending
            report['checks'].append('Native final ending handler produces the same second-quest flag and room difficulty')

            # Re-enter A02 through native room loading; the entrance bridge has
            # only props. This is a room fixture, not a natural bridge crossing.
            command('load', 0)
            route = {}
            for quest in (0,1):
                command('load',0)
                write(**{'88':quest, '86':1, '70':3})
                play.advance(lua,100)
                # The first hard-only ordinary-actor record is x576. Place
                # Simon nearby so native streaming reaches it reproducibly.
                write(**{'54a':550,'54e':100})
                samples=[]
                for _ in range(8):
                    play.advance(lua,15,('Right',))
                    samples.append(lua.eval('local r={} for a=0x580,0xE80,0x40 do '
                        'local id=mainmemory.read_u16_le(a) if id~=0 then '
                        'r[#r+1]=string.format("%X:%d:%d",id,mainmemory.read_u16_le(a+0xA),'
                        'mainmemory.read_u16_le(a+0xE)) end end '
                        'return table.concat(r,",")')['values'][0])
                route[str(quest)] = samples
            report['native_actor_route'] = {'synthetic_room_load':True,
                'synthetic_player_placement':[550,100],'block':1,'samples':route}
            assert any(len(hard_sample.split(',')) >= len(normal_sample.split(',')) + 2
                       for normal_sample, hard_sample in zip(route['0'], route['1'])), \
                'Native hard-only actors did not spawn on the fixture route'
            report['checks'].append('Native actor spawning changes on the same A02 room fixture route')

            reset = menu_start()
            assert reset['quest'] == 0 and reset['difficulty'] == normal['difficulty'], reset
            report['checks'].append('Reset then START returns to first quest')
            report['passed'] = True
            print('PASS:', '; '.join(report['checks']), flush=True)
        finally:
            (work / 'report.json').write_text(json.dumps(report,indent=2))
            if lua:
                lua.close()
            proc.terminate()
            proc.wait(timeout=10)


if __name__ == '__main__':
    main()
