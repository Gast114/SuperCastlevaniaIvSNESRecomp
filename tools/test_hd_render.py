"""Live HD regression using the same Lua control helpers as sciv_play.py.

Requires a Lua build. --capture can reuse a test_hd_pipeline collected folder;
otherwise a fresh collection and block 1-1 marker are recorded first.
"""
import argparse
import json
from pathlib import Path
import socket
import shutil
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
from hd_motifs import build_recipe


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
        # Same tile pixels can appear in different motifs. Context guards are
        # resolved through actual tilemap neighbors, including occluded cells.
        source = next((capture / 'hd_dump/captures/level_b00').glob('bg1_*.png'))
        context_work = work / 'context-source'; context_work.mkdir()
        shutil.copy2(source, context_work / 'layer.png')
        shutil.copy2(source.with_suffix('.tsv'), context_work / 'layer.tsv')
        art = hd.load_rgba(source).repeat(10, 0).repeat(10, 1)
        hd.save_rgba(art, context_work / 'nearest.png')
        recipe = {'version': 1, 'scale': 10, 'motifs': [{'name': 'identity',
                  'reference': 'layer.png', 'rect': [0, 0, 256, 224], 'artwork': 'nearest.png'}]}
        recipe_path = context_work / 'recipe.json'; recipe_path.write_text(json.dumps(recipe))
        context_pack = work / 'context-nearest'
        build_recipe(recipe_path, context_pack)
        command('loadfile', marker); hd_setting('layers 31'); hd_setting(f'pack {context_pack}')
        for buttons in ((), ('Right',), ('Left',)):
            play.advance(lua, 8, buttons); identity('context-nearest', 10)
        # Diagnostic colors reveal any substitution; wrong neighborhoods must
        # give exactly zero replacements, not a global per-key fallback.
        context_meta = json.loads((context_pack / 'pack.json').read_text())
        _, _, context_tiles = hd.load_pack(context_pack)
        context_tiles = {key: tile.copy() for key, tile in context_tiles.items()}
        for tile in context_tiles.values():
            tile[..., :3] = (17, 219, 241)
        colored = work / 'context-colored'; write_pack(context_tiles, colored, 10)
        colored_meta = json.loads((colored / 'pack.json').read_text())
        colored_meta.update(contexts=context_meta['contexts'], requires=['tile-context-v1'])
        (colored / 'pack.json').write_text(json.dumps(colored_meta))
        command('save', 2); hd_setting(f'pack {colored}'); play.advance(lua, 1)
        assert hd_setting()['matched'] > 100
        h, n = shot('context-color'), shot('context-color-native', False)
        assert np.any(h.reshape(224, 10, 342, 10, 3) != n[:, None, :, None, :])
        for choices in colored_meta['contexts'].values():
            for choice in choices:
                choice['neighbors'][0][2] = 'ffffffffffffffff'
        wrong = work / 'context-wrong'; shutil.copytree(colored, wrong)
        (wrong / 'pack.json').write_text(json.dumps(colored_meta))
        command('load', 2); hd_setting(f'pack {wrong}'); play.advance(lua, 1)
        assert hd_setting()['matched'] == 0
        h, n = shot('context-rejected'), shot('context-rejected-native', False)
        assert np.all(h.reshape(224, 10, 342, 10, 3) == n[:, None, :, None, :])
        colored_meta['requires'] = ['unsupported-future-feature']
        (wrong / 'pack.json').write_text(json.dumps(colored_meta))
        try:
            hd_setting(f'pack {wrong}')
            raise AssertionError('accepted unknown feature')
        except RuntimeError:
            pass
        colored_meta['requires'] = ['tile-context-v1']
        next(iter(colored_meta['contexts'].values()))[0]['neighbors'][0][0] = -2147483648
        (wrong / 'pack.json').write_text(json.dumps(colored_meta))
        try:
            hd_setting(f'pack {wrong}')
            raise AssertionError('accepted out-of-range context offset')
        except RuntimeError:
            pass
        hd_setting('off'); play.advance(lua, 1)
        print('PASS: live 2x/4x/10x identity, native state unchanged, true 80x80 subpixel detail, '
              'three independent layer switches, context identity/scroll/guards, original fallback, '
              'invalid reload and saved preferences')
    finally:
        if lua:
            lua.close()
        proc.terminate(); proc.wait(timeout=10); log.close()


if __name__ == '__main__':
    main()
