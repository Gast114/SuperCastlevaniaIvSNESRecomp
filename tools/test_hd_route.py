"""Replay a versioned scene route from one immutable state: original, HD, original.

Uses sciv_play's Lua controller in an isolated process. --fixture reuses an
existing state.sav; otherwise record a fresh start state from the user's ROM.
Checkpoints compare native pixels and named simulation fields. This is a
repeatable scripted route, not an interactive input recorder or every-frame
simulation checksum. Timing includes Lua control and presentation overhead.
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


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom', required=True, type=Path)
    p.add_argument('--pack', required=True, type=Path)
    p.add_argument('--fixture', type=Path)
    p.add_argument('--route', type=Path, default=sciv.ROOT/'assets/hd/block_1_1.route.json')
    sciv.add_build_arg(p)
    args = p.parse_args()
    route = json.loads(args.route.read_text())
    assert route['version'] == 1
    assert len({s['name'] for s in route['steps']}) == len(route['steps'])
    for s in route['steps']:
        assert s['name'].replace('-', '').isalnum() and 1 <= s['frames'] <= 3600
        if s['buttons']: play.parse_buttons(s['buttons'])
        for field, bounds in s.get('expect', {}).items():
            assert field in play.FIELDS and len(bounds) == 2 and bounds[0] <= bounds[1]
    build = sciv.build_dir(args)
    work = sciv.work_dir(build, 'hd-route-')
    fixture = args.fixture.resolve() if args.fixture else None
    if not fixture:
        capture = work/'capture'
        sciv.prepare(capture, build, {'Graphics': {'Widescreen': 1}})
        sciv.run(capture, route['boot_script'], args.rom, sciv.clean_env(
            SNESRECOMP_RUN_FRAMES=route['marker_frame']+1,
            SNESRECOMP_DEBUG_MARKER_AT=route['marker_frame'],
            SNESRECOMP_DEBUG_MARKER_NOTE='HD route immutable start'))
        fixture, = (capture/'debug_markers').glob('*/state.sav')
    folder = work/'game'
    exe = sciv.prepare(folder, build, {'Graphics': {'Widescreen': 1}, 'General': {'DisableFrameDelay': 1}})
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    env = sciv.clean_env(SNESRECOMP_LUA_PORT=port, SNESRECOMP_LUA_PAUSED=1)
    report = {'route': str(args.route.resolve()), 'route_sha256': sha(args.route),
              'rom_sha256': sha(args.rom), 'exe_sha256': sha(exe),
              'fixture': str(fixture), 'fixture_sha256': sha(fixture),
              'pack': str(args.pack.resolve()), 'pack_files': {
                  f.name: sha(f) for f in sorted(args.pack.glob('*')) if f.suffix in ('.json', '.png')},
              'runs': {}}
    lua = None
    with (folder/'game.log').open('w') as log:
        proc = subprocess.Popen([str(exe), str(args.rom.resolve())], cwd=folder,
                                env=env, stdout=log, stderr=log, startupinfo=sciv.hidden_window())
        try:
            for _ in range(200):
                if proc.poll() is not None: raise RuntimeError('Game exited; inspect game.log')
                try:
                    lua = play.LuaClient(port=port); lua.command('ping'); break
                except OSError: time.sleep(.05)
            if lua is None: raise RuntimeError('Lua build required')
            def command(name, arg=''):
                return lua.eval(f'return game.command({json.dumps(name)},{json.dumps(str(arg))})')['values'][0]
            command('hd', f'pack {args.pack.resolve()}'); command('hd', 'scale 10')
            for label in ('original', 'hd', 'original-again'):
                command('hd', 'on' if label == 'hd' else 'off')
                command('loadfile', fixture)
                output = work/label; output.mkdir()
                rows = []
                for step in route['steps']:
                    buttons = play.parse_buttons(step['buttons']) if step['buttons'] else ()
                    t = time.perf_counter(); play.advance(lua, step['frames'], buttons)
                    elapsed = time.perf_counter()-t
                    state = play.read_state(lua); state.pop('frame'); state.pop('paused')
                    shot = output/(step['name']+'.png'); command('screenshot', shot)
                    row = {'step': step['name'], 'state': state, 'native_sha256': sha(shot),
                           'frames': step['frames'], 'elapsed_seconds': elapsed}
                    if label == 'hd':
                        command('hdshot', output/(step['name']+'-hd.png'))
                        row['hd'] = json.loads(command('hd'))
                    rows.append(row)
                    for field, (low, high) in step.get('expect', {}).items():
                        assert low <= state[field] <= high, (label, step['name'], field, state[field])
                report['runs'][label] = rows
                (work/'report.json').write_text(json.dumps(report, indent=2))
            reference = report['runs']['original']
            for label in ('hd', 'original-again'):
                for a, b in zip(reference, report['runs'][label]):
                    assert a['state'] == b['state'] and a['native_sha256'] == b['native_sha256'], (label, a['step'])
            assert all(r['state']['block'] == 0 and r['state']['game_mode'] == 4 for r in reference)
            assert any(r['hd']['matched'] for r in report['runs']['hd']), 'Route did not exercise this pack'
            report['passed'] = True
            report['checkpoint_y'] = {r['step']: r['state']['player_y'] for r in reference}
            (work/'report.json').write_text(json.dumps(report, indent=2))
            print('PASS: original/HD/original-again native checkpoints and named state identical', flush=True)
            print(json.dumps(report['checkpoint_y']), flush=True)
        finally:
            if lua: lua.close()
            proc.terminate(); proc.wait(timeout=10)


if __name__ == '__main__':
    main()
