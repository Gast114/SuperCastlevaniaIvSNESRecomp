"""Cut every tile occurrence out of the upscaled pictures and merge them into
one HD image per tile key, for hd_preview.py and the future in-game renderer.

  python tools/hd/hd_build_pack.py [--dump build/hd_dump] [--work build/hd_work]
        [--pack build/hd_pack] [--combine median|mean|first]

A key is the tile's pixels plus its palette, so the same brick seen in fifty
places gets fifty HD candidates; the median of them keeps what the upscaler
agreed on and drops what only one neighbourhood suggested. Occurrences are
stored flipped back to the tile's own orientation.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hd_common as hd  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--dump', type=Path, default=hd.ROOT / 'build' / 'hd_dump')
    p.add_argument('--work', type=Path, default=hd.ROOT / 'build' / 'hd_work')
    p.add_argument('--pack', type=Path, default=hd.ROOT / 'build' / 'hd_pack')
    p.add_argument('--combine', choices=('median', 'mean', 'first'), default='median')
    p.add_argument('--max-candidates', type=int, default=24)
    args = p.parse_args()
    if args.max_candidates < 1:
        p.error('--max-candidates must be positive')

    tiles = hd.load_tiles(args.dump)
    candidates = defaultdict(list)
    scale = None
    for scene, stem, _png, tsv in hd.captures(args.dump):
        up_path = args.work / 'up' / scene / f'{stem}.png'
        if not up_path.exists():
            continue
        up = hd.load_rgba(up_path)
        s = up.shape[1] // hd.FIELD_W
        if scale is None:
            scale = s
        if s not in range(1, 11) or s != scale or up.shape[:2] != (hd.FIELD_H * s, hd.FIELD_W * s):
            raise SystemExit(f'{up_path}: scale {s} does not match {scale}')
        for x, y, key, flip in hd.occurrences(tsv):
            if key not in tiles or flip not in range(4) or not (0 <= x <= hd.FIELD_W - 8 and 0 <= y <= hd.FIELD_H - 8):
                raise SystemExit(f'{tsv}: invalid occurrence {x}, {y}, {key}, {flip}')
            if len(candidates[key]) >= args.max_candidates:
                continue
            tile = up[y * s:(y + 8) * s, x * s:(x + 8) * s]
            if flip & 1:
                tile = tile[:, ::-1]
            if flip & 2:
                tile = tile[::-1]
            candidates[key].append(tile)
    if scale is None:
        raise SystemExit('nothing upscaled yet: run tools/hd/hd_upscale.py first')

    size = 8 * scale
    per_row = hd.ATLAS // size
    per_atlas = per_row * per_row
    args.pack.mkdir(parents=True, exist_ok=True)
    index, atlas, n = {}, None, 0
    for key in sorted(candidates):
        stack = np.stack(candidates[key])
        if args.combine == 'median':
            tile = np.median(stack, axis=0)
        elif args.combine == 'mean':
            tile = stack.mean(axis=0)
        else:
            tile = stack[0]
        a, slot = divmod(n, per_atlas)
        if slot == 0:
            if atlas is not None:
                hd.save_rgba(atlas, args.pack / f'atlas_{a - 1:03d}.png')
            atlas = np.zeros((hd.ATLAS, hd.ATLAS, 4), np.uint8)
        y, x = divmod(slot, per_row)
        atlas[y * size:(y + 1) * size, x * size:(x + 1) * size] = np.clip(tile, 0, 255).astype(np.uint8)
        index[key] = [a, slot]
        n += 1
    if atlas is not None:
        hd.save_rgba(atlas, args.pack / f'atlas_{(n - 1) // per_atlas:03d}.png')
    upscale = args.work / 'upscale.json'
    meta = {
        'version': 1, 'scale': scale, 'tile_size': size, 'atlas_size': hd.ATLAS,
        'combine': args.combine,
        'upscale': json.loads(upscale.read_text()) if upscale.exists() else None,
        'tiles': index,
    }
    (args.pack / 'pack.json').write_text(json.dumps(meta))
    missing = len(tiles) - len(index)
    print(f'{len(index)} HD tiles at {scale}x in {args.pack} '
          f'({missing} collected keys had no clean occurrence)')


if __name__ == '__main__':
    main()
