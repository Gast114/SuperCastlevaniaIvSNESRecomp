"""Replay drawbridge/HUD, stair exit lifetime and original-speed pacing.

Fixtures are local captures from the player's ROM. The recovered stair save
contains the native exit actor restored before the original level transition;
the original broken save is retained separately. Nothing writes player files.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time

import numpy as np
from PIL import Image
import sciv_play as play
import sciv_test_support as sciv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('rom', 'pack', 'bridge', 'stairs', 'recovered'):
        parser.add_argument('--' + name, type=Path, required=True)
    sciv.add_build_arg(parser)
    args = parser.parse_args()
    build = sciv.build_dir(args)
    work = sciv.work_dir(build, 'hd-transitions-')
    folder = work / 'game'
    exe = sciv.prepare(folder, build, {'Graphics': {'Widescreen': 1}})
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    report = {'checks': [], 'pacing': {}}
    lua = None
    with (folder / 'game.log').open('w') as log:
        proc = subprocess.Popen([str(exe), str(args.rom.resolve())], cwd=folder,
            env=sciv.clean_env(SNESRECOMP_LUA_PORT=port, SNESRECOMP_LUA_PAUSED=1),
            stdout=log, stderr=log, startupinfo=sciv.hidden_window())
        try:
            for _ in range(200):
                if proc.poll() is not None:
                    raise RuntimeError('Game exited; inspect game.log')
                try:
                    lua = play.LuaClient(port=port)
                    lua.command('ping')
                    break
                except OSError:
                    time.sleep(.05)
            assert lua

            def command(name, arg=''):
                return lua.eval(f'return game.command({json.dumps(name)},'
                                f'{json.dumps(str(arg))})')['values'][0]

            def word(address, value):
                lua.eval(f'mainmemory.write_u8({address},{value & 255});'
                         f'mainmemory.write_u8({address + 1},{value >> 8})')

            def exits():
                return lua.eval('local n=0 for a=0x580,0xE80,0x40 do '
                    'if mainmemory.read_u16_le(a+0x10)==0x15 then n=n+1 end end return n')['values'][0]

            command('hd', 'pack ' + str(args.pack.resolve()))
            command('hd', 'scale 10')
            runs = []
            outgoing = new_room = False
            for enabled in (False, True):
                command('hd', 'on' if enabled else 'off')
                command('loadfile', args.bridge.resolve())
                samples = []
                for n in range(0, 181, 4):
                    play.advance(lua, 4 if n else 1, ('Right',) if n else ())
                    state = play.read_state(lua)
                    state.pop('frame'); state.pop('paused')
                    shot = work / 'native.png'
                    command('screenshot', shot)
                    pixels = np.array(Image.open(shot).convert('RGB'))
                    hd = json.loads(command('hd'))
                    if enabled and n == 0:
                        command('hdshot', work / 'bridge-hd.png')
                        rendered = np.array(Image.open(work / 'bridge-hd.png').convert('RGB'))
                        nearest = pixels.repeat(10, 0).repeat(10, 1)
                        assert np.array_equal(rendered[:320, :2200], nearest[:320, :2200]), 'HUD text/bars changed'
                        assert np.any(rendered[:320, 2200:] != nearest[:320, 2200:]), 'upper chain remained native'
                    if enabled and state['block'] == 1 and state['level_phase'] == 6:
                        assert hd['matched'] > 1000, 'outgoing bridge lost HD during fade'
                        outgoing = True
                    if enabled and state['block'] == 1 and state['level_phase'] == 5:
                        assert hd['matched'] == 0, 'outgoing scenery leaked into next room'
                        new_room = True
                    samples.append((state, hashlib.sha256(pixels.tobytes()).hexdigest()))
                runs.append(samples)
            assert runs[0] == runs[1], 'HD changed native pixels or game state'
            assert outgoing and new_room, 'fixture missed transition'
            report['checks'].append('HUD chain replaced, HUD text exact; phase-6 fade retains HD; new room guarded; native identity')

            # This old snapshot has already lost the exit. Reproduce its
            # reverse-spawn at the left boundary through the native parser.
            command('loadfile', args.stairs.resolve())
            assert int(exits()) == 0, 'expected original missing-exit fixture'
            for address, value in ((0x54A, 828), (0x1C, 700), (0x1280, 700), (0x94, 0x83E0)):
                word(address, value)
            for _ in range(8):
                play.advance(lua, 1)
                assert int(exits()) == 1, 'exit culled immediately after reverse spawn'
            command('loadfile', args.recovered.resolve())
            assert int(exits()) == 1, 'recovered save must contain exactly one native exit'
            play.advance(lua, 80, ('Up',))
            state = play.read_state(lua)
            assert state['block'] == 6 and state['level_phase'] == 5 and state['player_y'] < 256, state
            command('screenshot', work / 'next-section.png')
            play.advance(lua, 10, ('Right',))
            assert play.read_state(lua)['player_x'] != state['player_x'], 'new room did not resume gameplay'
            report['checks'].append('Exit survives widened reverse boundary; native block 5->6; recovered F5 loads next room and resumes gameplay')

            # Normal config, VSync off, same guest save and 180 frames. HD
            # may run slower when over budget; it must never speed up play.
            for enabled in (False, True):
                command('hd', 'on' if enabled else 'off')
                command('loadfile', args.bridge.resolve())
                play.advance(lua, 10)
                started = time.perf_counter()
                play.advance(lua, 180)
                elapsed = time.perf_counter() - started
                fps = 180 / elapsed
                assert 10 < fps < 61, ('unpaced execution or stalled renderer', enabled, fps)
                if not enabled:
                    assert fps > 57, ('native playback below original speed', fps)
                report['pacing']['hd' if enabled else 'original'] = {'frames': 180, 'seconds': elapsed, 'fps': fps}
            report['passed'] = True
            (work / 'report.json').write_text(json.dumps(report, indent=2))
            print('PASS:', '; '.join(report['checks']), report['pacing'])
        finally:
            if lua:
                lua.close()
            proc.terminate(); proc.wait(timeout=10)


if __name__ == '__main__':
    main()
