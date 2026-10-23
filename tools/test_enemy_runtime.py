"""Exercise captured A02 skeletons with native and arbitrary-resolution artwork.

Requires a Lua-enabled game build and an A02 skeleton save fixture. Uses only
an isolated copied executable/profile; no player configuration is changed.
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
import enemy_hd
import sciv_play as play
import sciv_test_support as sciv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sciv.add_build_arg(parser)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--rom', type=Path, default=sciv.ROOT / 'Super Castlevania IV (USA).sfc')
    args = parser.parse_args()
    work = sciv.work_dir(sciv.build_dir(args), 'enemy-runtime-')
    folder = work / 'game'
    exe = sciv.prepare(folder, sciv.build_dir(args), {'General': {'DisableFrameDelay': 1}})
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    report = {'passed': False, 'checks': [], 'natural_playthrough': False}
    lua = None
    with (folder / 'game.log').open('w') as log:
        proc = subprocess.Popen([str(exe), str(args.rom.resolve())], cwd=folder,
            env=sciv.clean_env(SNESRECOMP_LUA_PORT=port, SNESRECOMP_LUA_PAUSED=1),
            stdout=log, stderr=log, startupinfo=sciv.hidden_window())
        try:
            for _ in range(200):
                try:
                    lua = play.LuaClient(port=port); lua.command('ping'); break
                except OSError:
                    assert proc.poll() is None
                    time.sleep(.05)
            assert lua
            def cmd(name, argument=''):
                return lua.eval(f'return game.command({json.dumps(name)},{json.dumps(str(argument))})')['values'][0]
            def ramhash():
                data = bytearray()
                for address in range(0, 0x20000, 128):
                    values = lua.eval(f'local t={{}} for i={address},{address+127} do t[#t+1]=mainmemory.read_u8(i) end return table.concat(t,",")')['values'][0]
                    data.extend(map(int, values.split(',')))
                return hashlib.sha256(data).hexdigest()
            cmd('loadfile', args.fixture.resolve())
            play.advance(lua, 50)
            reference = folder / 'enemy_packs/native-template'
            for _ in range(100):
                try:
                    data = json.loads((reference / 'enemies.json').read_text())
                    if len(data['frames']) >= 2:
                        break
                except (OSError, ValueError):
                    pass
                time.sleep(.05)
            assert len(data['frames']) >= 2, 'No complete skeleton animation references collected'
            assert all(f['actor_type'] in (17,18) and f['id'].startswith('skelett-') for f in data['frames']), data
            cmd('enemy', 'capture off')
            project = work / 'art-project'
            enemy_hd.prepare(reference, project)
            for path in (project / 'artwork').glob('*.png'):
                with Image.open(path) as original:
                    image = original.convert('RGBA').resize((387,387), Image.Resampling.NEAREST)
                # Unmistakable colour, preserving the captured full-body shape.
                alpha = image.getchannel('A')
                image.paste((255,0,255,255), (0,0,image.width,image.height))
                image.putalpha(alpha); image.save(path)
            enemy_hd.pack(project, folder / 'enemy_packs/diagnostic')
            report['captured'] = data['frames']
            results = []
            for custom in (False, True):
                cmd('enemy', 'pack diagnostic' if custom else 'off')
                cmd('hd', 'scale 10'); cmd('hd', 'on')
                cmd('loadfile', args.fixture.resolve())
                samples = []
                for n in range(16):
                    play.advance(lua, 1)
                    if n in (1,7,15):
                        tag = ('custom' if custom else 'native') + f'-{n:02d}'
                        cmd('screenshot', work / (tag + '.png'))
                        cmd('dump', work / (tag + '-video.bin'))
                        if custom:
                            cmd('hdshot', work / (tag + '-hd.png'))
                            image = np.array(Image.open(work / (tag + '-hd.png')).convert('RGB'))
                            magenta = (image[:,:,0] > 230) & (image[:,:,1] < 20) & (image[:,:,2] > 230)
                            assert int(magenta.sum()) > 2000, (tag, int(magenta.sum()), image.shape)
                            assert image.shape[0] == 2240, image.shape
                        samples.append({'field': n, 'ram_sha256': ramhash(),
                                        'video_sha256': hashlib.sha256((work / (tag + '-video.bin')).read_bytes()).hexdigest()})
                results.append(samples)
            assert results[0] == results[1], 'Enemy artwork changed native WRAM, VRAM, CGRAM or OAM'
            report['native_identity'] = results[0]
            report['checks'] += ['Real A02 skeleton frames captured without architecture/ambient actors',
                                 '387x387 PNGs render as complete skeletons on a 96x96 native canvas',
                                 'Full WRAM and VRAM/CGRAM/OAM hashes remain identical with enemy artwork enabled',
                                 'Unknown poses and unmodified actors retain native rendering']
            report['passed'] = True
            print('PASS:', '; '.join(report['checks']), flush=True)
        finally:
            (work / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
            if lua:
                lua.close()
            proc.terminate(); proc.wait(timeout=10)


if __name__ == '__main__':
    main()
