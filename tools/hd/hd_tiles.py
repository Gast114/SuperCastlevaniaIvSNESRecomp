"""Export a pack to editable KEY.png tiles, or pack those PNGs again.

An 80x80 RGBA PNG replaces one original 8x8 tile at 10x. Artists can replace
individual files without altering the ROM or any other graphics pack.
No resizing or AI processing is performed here.
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np
import hd_common as hd


def write_pack(tiles, output, scale):
    """Validate the complete input before writing any output."""
    size = 8 * scale
    if not 1 <= scale <= 10 or not tiles:
        raise ValueError('need tiles at scale 1..10')
    for key, tile in tiles.items():
        if not re.fullmatch(r'[0-9a-f]{16}', key) or tile.shape != (size, size, 4):
            raise ValueError(f'{key}: expected {size}x{size} RGBA and a 16-digit lowercase hex key')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    per_row = hd.ATLAS // size
    index = {}
    atlas = None
    for n, key in enumerate(sorted(tiles)):
        a, slot = divmod(n, per_row ** 2)
        if slot == 0:
            if atlas is not None:
                hd.save_rgba(atlas, output / f'atlas_{a - 1:03d}.png')
            atlas = np.zeros((hd.ATLAS, hd.ATLAS, 4), np.uint8)
        y, x = divmod(slot, per_row)
        atlas[y*size:(y+1)*size, x*size:(x+1)*size] = tiles[key]
        index[key] = [a, slot]
    hd.save_rgba(atlas, output / f'atlas_{a:03d}.png')
    (output / 'pack.json').write_text(json.dumps({
        'version': 1, 'scale': scale, 'tile_size': size, 'atlas_size': hd.ATLAS,
        'tiles': index,
    }))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    export = sub.add_parser('export')
    export.add_argument('--pack', type=Path, required=True)
    export.add_argument('--out', type=Path, required=True)
    build = sub.add_parser('build')
    build.add_argument('--tiles', type=Path, required=True)
    build.add_argument('--pack', type=Path, required=True)
    build.add_argument('--scale', type=int, choices=range(1, 11), default=10)
    args = parser.parse_args()
    if args.action == 'export':
        scale, _, tiles = hd.load_pack(args.pack)
        # Avoid replacing artwork that the artist may have edited already.
        if args.out.exists() and any(args.out.iterdir()):
            parser.error('--out must be empty; preserve your edited PNGs')
        for key, tile in tiles.items():
            hd.save_rgba(tile, args.out / f'{key}.png')
        print(f'Exported {len(tiles)} tiles at {scale}x to {args.out}')
    else:
        tiles = {p.stem: hd.load_rgba(p) for p in args.tiles.glob('*.png')}
        write_pack(tiles, args.pack, args.scale)
        print(f'Built {len(tiles)} tiles at {args.scale}x in {args.pack}')


if __name__ == '__main__':
    main()
