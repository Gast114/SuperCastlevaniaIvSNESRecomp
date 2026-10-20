"""Separate PC frame cost from guest logic stalls using an isolated Lua build.

Default: original-speed pacing. --unthrottled measures PC headroom only; its
FPS is not the gameplay rate. Nothing writes player configuration or saves.
Example: --fixture path/state.sav --pack path/hd_pack --scale 10 --frames 360
"""
import argparse
import csv
import json
from pathlib import Path
import socket
import statistics
import subprocess
import time

import sciv_play as play
import sciv_test_support as sciv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--pack', type=Path)
    parser.add_argument('--scale', type=int, choices=(0, 2, 4, 6, 10), default=0)
    parser.add_argument('--workers', type=int, choices=range(1, 33), default=8)
    parser.add_argument('--frames', type=int, default=360)
    parser.add_argument('--warmup', type=int, default=60)
    parser.add_argument('--unthrottled', action='store_true')
    parser.add_argument('--medusa-death-at', type=int, default=0,
                        help='Synthetic test only: enter native Medusa death state at this frame')
    sciv.add_build_arg(parser)
    args = parser.parse_args()
    if not 2 <= args.frames < 36000 or not 0 <= args.warmup < args.frames - 1:
        parser.error('need 2..35999 frames and at least two measured frames after warmup')
    if args.scale and not args.pack:
        parser.error('--scale requires --pack')
    if args.medusa_death_at:
        if not 1 <= args.medusa_death_at <= args.frames:
            parser.error('death frame must be inside the recorded run')
        # Retail LoROM tables $01:AE07/AE87, used by $00:DC43 after a kill.
        rom = args.rom.read_bytes()
        if len(rom) != 0x100000 or (rom[0xAE07], rom[0xAE87]) != (7, 2):
            parser.error('Medusa diagnostic requires the verified retail death tables')
    build = sciv.build_dir(args)
    work = sciv.work_dir(build, 'fps-profile-')
    exe = sciv.prepare(work, build, {'Graphics': {'Widescreen': 1},
        'General': {'DisableFrameDelay': int(args.unthrottled)}})
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = sciv.clean_env(SNESRECOMP_LUA_PORT=port, SNESRECOMP_LUA_PAUSED=1,
        SNESRECOMP_RUN_FRAMES=args.frames + 1, SNESRECOMP_HOST_PROFILE=1,
        SNESRECOMP_FRAME_TIMING=work / 'timing.csv', SNESRECOMP_RENDER_WORKERS=args.workers)
    env['SCIV_HD_TIMINGS'] = '1'
    lua = None
    with (work / 'game.log').open('w') as log:
        proc = subprocess.Popen([str(exe), str(args.rom.resolve())], cwd=work, env=env,
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

            if args.scale:
                command('hd', 'pack ' + str(args.pack.resolve()))
                command('hd', 'scale ' + str(args.scale))
                command('hd', 'on')
            else:
                command('hd', 'off')
            command('loadfile', args.fixture.resolve())
            # Counters are collected in the running Lua coroutine, without a
            # network round trip or disk flush per emulated field. Busy alone
            # is not proof of lag: compare the actual logic counter at $3A.
            lua.run('''profile={}
for i=1,%d do
  if i==%d then
    for a=0x580,0xE80,0x40 do
      if mainmemory.read_u16_le(a+0x10)==7 and mainmemory.read_u16_le(a+0x12)==1 then
        for _,off in ipairs({6,0x16,0x2E}) do
          mainmemory.write_u8(a+off,0);mainmemory.write_u8(a+off+1,0)
        end
        mainmemory.write_u8(a+0x12,2);mainmemory.write_u8(a+0x13,0)
      end
    end
  end
  joypad.set({},1);emu.frameadvance()
  local actors,heads,fragments=0,0,0
  for a=0x580,0xE80,0x40 do
    local ty=mainmemory.read_u16_le(a+0x10)
    if ty~=0 then actors=actors+1 end
    if ty==7 then
      if mainmemory.read_u16_le(a+0x12)==3 then fragments=fragments+1
      else heads=heads+1 end
    end
  end
  profile[i]=table.concat({mainmemory.read_u8(0x3A),mainmemory.read_u8(0x3C),actors,
    mainmemory.read_u8(0x86),mainmemory.read_u8(0x70),heads,fragments},",")
end''' % (args.frames, args.medusa_death_at))
            play.wait_idle(lua)
            guest = []
            for start in range(1, args.frames + 1, 20):
                # A bridge string is limited to 1024 bytes; each batch fits.
                chunk = lua.eval('return table.concat(profile,";",%d,%d)' %
                    (start, min(args.frames, start + 19)))['values'][0]
                guest.extend([list(map(int, row.split(','))) for row in chunk.split(';')])
            assert len(guest) == args.frames
            state = play.read_state(lua)
            command('screenshot', work / 'native.png')
            if args.scale:
                command('hdshot', work / 'hd.png')
            # One final frame exits normally and flushes the buffered timing
            # trace. It is excluded from the measurements and guest samples.
            try:
                lua.command('resume')
            except ConnectionError:
                pass
            proc.wait(timeout=30)
            assert proc.returncode == 0, proc.returncode
        finally:
            if lua:
                lua.close()
            if proc.poll() is None:
                proc.terminate(); proc.wait(timeout=10)
    timings = list(csv.DictReader((work / 'timing.csv').open()))[args.warmup:args.frames]
    assert len(timings) == args.frames - args.warmup
    spans = [(a, b) for a, b in zip(guest[args.warmup:], guest[args.warmup + 1:])
             if a[3:5] == b[3:5] and b[4] == 5]
    report = {'arguments': {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
        'state': state, 'guest_columns': ['logic_counter', 'busy', 'actors', 'block', 'phase', 'heads', 'fragments'],
        'guest': guest, 'measured_fields': len(timings), 'comparable_gameplay_intervals': len(spans),
        'logic_updates': sum((b[0] - a[0]) & 255 for a, b in spans),
        'logic_repeats': sum(a[0] == b[0] for a, b in spans),
        'max_medusa_fragments': max(row[6] for row in guest), 'timings': {}}
    seconds = float(timings[-1]['present_seconds']) - float(timings[0]['present_seconds'])
    report['host_fps'] = (len(timings) - 1) / seconds
    if args.medusa_death_at and not report['max_medusa_fragments']:
        raise RuntimeError('Stress fixture did not produce native Medusa death fragments')
    for key in timings[0]:
        if key == 'frame':
            continue
        values = [float(row[key]) for row in timings]
        report['timings'][key] = {'mean': statistics.mean(values),
            'p95': sorted(values)[int(.95 * (len(values) - 1))], 'max': max(values)}
    (work / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ('host_fps', 'logic_updates',
        'comparable_gameplay_intervals', 'logic_repeats', 'max_medusa_fragments')}, indent=2))


if __name__ == '__main__':
    main()
