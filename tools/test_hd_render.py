"""Live HD regression using the same Lua control helpers as sciv_play.py.

Requires a Lua build. --capture can reuse a test_hd_pipeline collected folder;
otherwise a fresh collection and block 1-1 marker are recorded first.
"""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import time

import numpy as np
from PIL import Image
import sciv_test_support as sciv
import sciv_play as play

sys.path.insert(0, str(Path(__file__).parent / 'hd'))
import hd_common as hd
from hd_tiles import write_pack


def image(path):
    return np.asarray(Image.open(path).convert('RGB'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom', required=True)
    p.add_argument('--capture', type=Path)
    sciv.add_build_arg(p)
    args = p.parse_args()
    build = sciv.build_dir(args)
    work = sciv.work_dir(build, 'hd-live-check-')
    capture = args.capture.resolve() if args.capture else work / 'capture'
    if not args.capture:
        sciv.prepare(capture, build, {'Graphics': {'Widescreen': 1}})
        sciv.run(capture, 'widescreen_smoke.input', args.rom, sciv.clean_env(
            SNESRECOMP_RUN_FRAMES=1320, SNESRECOMP_HD_COLLECT=1,
            SNESRECOMP_DEBUG_MARKER_AT=1300, SNESRECOMP_DEBUG_MARKER_NOTE='HD live test'))
    marker = next((capture / 'debug_markers').glob('*_level/state.sav'))
    tiles = hd.load_tiles(capture / 'hd_dump')
    native = {key: tile.rgba() for key, tile in tiles.items()}
    nearest = work / 'nearest'
    write_pack({key: tile.repeat(4, 0).repeat(4, 1) for key, tile in native.items()}, nearest, 4)
    detailed = work / 'diagnostic-10x'
    # Distinct per-subpixel RGB and alpha, not an enlargement. Every native
    # texel varies inside its 10x10 cell, exercising actual 80x80 assets.
    yy, xx = np.indices((80, 80))
    pattern = np.stack((30 + (xx % 10) * 20, 40 + (yy % 10) * 19, (xx * 11 + yy * 7) % 256), axis=2).astype(np.uint8)
    art = {}
    for key, tile in native.items():
        up = tile.repeat(10, 0).repeat(10, 1)
        up[..., :3] = pattern
        art[key] = up
    write_pack(art, detailed, 10)
    del art
    broken = work / 'broken'; broken.mkdir()
    meta = json.loads((nearest / 'pack.json').read_text())
    meta['tile_size'] = 33
    (broken / 'pack.json').write_text(json.dumps(meta))

    folder = work / 'game'
    exe = sciv.prepare(folder, build, {'Graphics': {'Widescreen': 1}, 'General': {'DisableFrameDelay': 1}})
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    env = sciv.clean_env(SNESRECOMP_LUA_PORT=port, SNESRECOMP_LUA_PAUSED=1)
    log = (folder / 'game.log').open('w')
    proc = subprocess.Popen([str(exe), str(Path(args.rom).resolve())], cwd=folder, env=env,
                            stdout=log, stderr=log, startupinfo=sciv.hidden_window())
    lua = None
    try:
        for _ in range(200):
            if proc.poll() is not None:
                raise AssertionError('game exited: ' + (folder / 'game.log').read_text(errors='replace'))
            try:
                lua = play.LuaClient(port=port); lua.command('ping'); break
            except OSError:
                time.sleep(.05)
        assert lua is not None, 'Lua bridge did not start; use build-lua'

        def command(name, arg=''):
            return lua.eval(f'return game.command({json.dumps(name)},{json.dumps(str(arg))})')['values'][0]

        def hd_setting(arg=''):
            return json.loads(command('hd', arg))

        def shot(stem, high=True):
            path = work / f'{stem}.png'
            command('hdshot' if high else 'screenshot', path)
            return image(path)

        def identity(stem, factor):
            n, h = shot(stem + '-native', False), shot(stem)
            assert h.shape == (224 * factor, 342 * factor, 3), h.shape
            assert np.all(h.reshape(224, factor, 342, factor, 3) == n[:, None, :, None, :]), stem
            assert hd_setting()['matched'] > 100, 'no replacements were exercised'

        command('loadfile', marker)
        hd_setting(f'pack {nearest}'); hd_setting('on')
        for factor, buttons in ((4, ()), (10, ('Right',)), (2, ('Left',))):
            hd_setting(f'scale {factor}'); play.advance(lua, 4, buttons)
            identity(f'nearest-{factor}', factor)
        # Replay the same game state with HD disabled/enabled: the native
        # output and all named game-state fields must be exactly identical.
        command('save', 1)
        hd_setting('off'); play.advance(lua, 8, ('Right',))
        before = shot('off', False); state = play.read_state(lua); state.pop('frame')
        command('load', 1); hd_setting('on'); play.advance(lua, 8, ('Right',))
        assert np.array_equal(before, shot('on-native', False))
        after = play.read_state(lua); after.pop('frame')
        assert state == after, (state, after)
        command('load', 1); hd_setting(f'pack {detailed}'); hd_setting('scale 10')
        play.advance(lua, 1); full = shot('detail-full'); n = shot('detail-native', False)
        assert np.any(full.reshape(224, 10, 342, 10, 3) != n[:, None, :, None, :])
        blocks = full.reshape(224, 10, 342, 10, 3)
        assert np.any(blocks != blocks[:, :1, :, :1, :]), 'no detail inside original pixels'
        # Invalid reload keeps the last valid package, dimensions and settings.
        try:
            hd_setting(f'pack {broken}')
            raise AssertionError('accepted malformed pack')
        except RuntimeError:
            pass
        assert hd_setting()['art_scale'] == 10
        assert hd_setting()['tiles'] == len(tiles)
        # Toggle each category off and verify the corresponding on image is
        # different. All categories off must recover the original exactly.
        for mask, label in ((3, 'bg'), (12, 'text'), (16, 'sprites'), (0, 'none')):
            command('load', 1); hd_setting(f'layers {mask}'); play.advance(lua, 1)
            h, n = shot(label), shot(label + '-native', False)
            changed = np.any(h.reshape(224, 10, 342, 10, 3) != n[:, None, :, None, :])
            assert changed == (mask != 0), (label, changed)
        settings = json.loads((folder / 'hd_settings.json').read_text())
        assert settings['scale'] == 10 and settings['layers'] == 0
        assert Path(settings['pack']) == detailed
        hd_setting('off'); play.advance(lua, 1)
        print('PASS: live 2x/4x/10x identity, native state unchanged, true 80x80 subpixel detail, '
              'three independent layer switches, original fallback, invalid reload and saved preferences')
    finally:
        if lua:
            lua.close()
        proc.terminate(); proc.wait(timeout=10); log.close()


if __name__ == '__main__':
    main()
