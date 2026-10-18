"""HD export/pack checks. With --rom, also collect from a real play session,
compare presented CRCs and reconstruct a block 1-1 marker pixel for pixel.
All generated graphics stay in the ignored test build directory.
"""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import sciv_test_support as sciv

sys.path.insert(0, str(Path(__file__).parent / 'hd'))
import hd_common as hd
from hd_preview import fnv_key


def run_tool(name, *args, success=True):
    result = subprocess.run([sys.executable, str(hd.ROOT / 'tools/hd' / name), *map(str, args)],
                            text=True, capture_output=True)
    assert (result.returncode == 0) == success, result.stdout + result.stderr
    return result.stdout


def check_tools(folder):
    dump, work, pack = (folder / name for name in ('hd_dump', 'hd_work', 'hd_pack'))
    capture = dump / 'captures/synthetic/bg1_test.png'
    capture.parent.mkdir(parents=True)
    palette = [0, 0x001f, 0x03e0, 0x7c00]
    pixels = [(x + 2 * y) % 4 for y in range(8) for x in range(8)]
    tile = hd.TileInfo(2, palette, pixels).rgba()
    key = fnv_key(2, pixels, palette)
    (dump / 'tiles.tsv').write_text(f'{key}\t2\t' + ''.join(f'{p:04x}' for p in palette)
                                   + '\t' + ''.join(f'{p:x}' for p in pixels) + '\n')
    layer = np.zeros((224, 256, 4), np.uint8)
    occurrences = []
    for flip in range(4):
        image = tile[:, ::-1] if flip & 1 else tile
        image = image[::-1] if flip & 2 else image
        x, y = 16 * flip, 16
        layer[y:y + 8, x:x + 8] = image
        occurrences.append(f'{x}\t{y}\t{key}\t{flip}\n')
    hd.save_rgba(layer, capture)
    capture.with_suffix('.tsv').write_text(''.join(occurrences))
    up_args = ('--dump', dump, '--work', work, '--method', 'nearest')
    run_tool('hd_upscale.py', *up_args)
    assert '0 pictures to upscale' in run_tool('hd_upscale.py', *up_args)
    run_tool('hd_build_pack.py', '--dump', dump, '--work', work, '--pack', pack)
    scale, _, tiles = hd.load_pack(pack)
    expected = tile.repeat(scale, 0).repeat(scale, 1)
    # RGB behind transparent pixels may be filled; visible RGBA must match.
    assert np.array_equal(tiles[key][..., 3], expected[..., 3])
    mask = expected[..., 3] != 0
    assert np.array_equal(tiles[key][mask], expected[mask]), 'flips/crops changed visible pixels'
    layer[100:108, 100:108] = tile
    hd.save_rgba(layer, capture)
    assert '1 pictures to upscale' in run_tool('hd_upscale.py', *up_args), 'changed input was cached'
    old_manifest = (pack / 'pack.json').read_bytes()
    Image.new('RGBA', (1025, 896)).save(work / 'up/synthetic/bg1_test.png')
    run_tool('hd_build_pack.py', '--dump', dump, '--work', work, '--pack', pack, success=False)
    assert (pack / 'pack.json').read_bytes() == old_manifest, 'invalid input replaced a good pack'
    print('PASS: tile flips, transparency, pack roundtrip, cache invalidation and invalid dimensions')


def check_game(folder, build, rom):
    baseline, collected = folder / 'baseline', folder / 'collected'
    rows = []
    for directory, enabled in ((baseline, 0), (collected, 1)):
        sciv.prepare(directory, build, {'Graphics': {'Widescreen': 1}})
        sciv.run(directory, 'widescreen_smoke.input', rom, sciv.clean_env(
            SNESRECOMP_RUN_FRAMES=1320, SNESRECOMP_HD_COLLECT=enabled,
            SNESRECOMP_DEBUG_MARKER_AT=1300, SNESRECOMP_DEBUG_MARKER_NOTE='HD regression',
            SNESRECOMP_PRESENT_LOG=directory / 'presents.csv'))
        with (directory / 'presents.csv').open() as stream:
            rows.append({r['frame']: r['crc32'] for r in csv.DictReader(stream)})
    assert rows[0] == rows[1] and len(rows[0]) >= 1300, 'collection changed the presented frames'
    dump = collected / 'hd_dump'
    catalogue = hd.load_tiles(dump)
    assert len(catalogue) > 100
    count = 0
    for _, _, png, tsv in hd.captures(dump):
        layer = hd.load_rgba(png)
        for x, y, key, flip in hd.occurrences(tsv):
            expected = catalogue[key].rgba()
            if flip & 1:
                expected = expected[:, ::-1]
            if flip & 2:
                expected = expected[::-1]
            assert np.array_equal(layer[y:y + 8, x:x + 8], expected), f'bad occurrence in {png}'
            count += 1
    run_tool('hd_pipeline.py', '--build', collected, '--method', 'nearest')
    marker = next((collected / 'debug_markers').glob('*_level'))
    real = np.asarray(Image.open(marker / 'screen.png').convert('RGB'))
    extra = (real.shape[1] - 256) // 2
    native = np.asarray(Image.open(marker / 'hd_preview_native.png'))
    assert np.array_equal(native, real[:, extra:extra + 256]), 'marker reconstruction differs'
    enlarged = np.asarray(Image.open(marker / 'hd_preview_hd.png'))
    assert np.array_equal(enlarged, native.repeat(4, 0).repeat(4, 1)), 'nearest pack differs from native'
    old = {p: hashlib.sha256(p.read_bytes()).digest() for p in dump.rglob('*.png')}
    # Launch again in the same directory: retain the previous session's files.
    sciv.run(collected, 'widescreen_smoke.input', rom, sciv.clean_env(
        SNESRECOMP_RUN_FRAMES=365, SNESRECOMP_HD_COLLECT=1), log_name='second-run.log')
    assert len(list(dump.rglob('*.png'))) > len(old)
    assert all(hashlib.sha256(p.read_bytes()).digest() == digest for p, digest in old.items())
    print(f'PASS: {count} clean occurrences; {len(rows[0])} frames unchanged; '
          'marker reconstructed exactly; second session preserved captures')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom')
    sciv.add_build_arg(parser)
    args = parser.parse_args()
    build = sciv.build_dir(args)
    folder = sciv.work_dir(build, 'hd-check-')
    check_tools(folder / 'synthetic')
    if args.rom:
        check_game(folder, build, args.rom)


if __name__ == '__main__':
    main()
