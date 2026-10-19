"""Inventory unique original tiles across captures; keep one editable HD source per key.

Recorded occurrence counts measure capture coverage, not unique world positions.
Palette families are reported separately; they are never automatically merged.
Existing artwork in shared/ is read and validated, never generated or overwritten.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import hd_common as hd


def catalog(dumps, output, scale=10):
    if type(scale) is not int or not 1 <= scale <= 10:
        raise ValueError('scale must be an integer in 1..10')
    output = Path(output)
    tiles, counts, scenes, first = {}, Counter(), defaultdict(set), {}
    for dump in dumps:
        for key, tile in hd.load_tiles(dump).items():
            if key in tiles and (tiles[key].bpp != tile.bpp or tiles[key].pixels != tile.pixels or tiles[key].palette[1:] != tile.palette[1:]):
                raise ValueError(f'{key}: inconsistent original tile')
            tiles[key] = tile
        for scene, stem, png, tsv in hd.captures(dump):
            for x, y, key, flip in hd.occurrences(tsv):
                if key not in tiles: raise ValueError(f'{tsv}: unknown key {key}')
                counts[key] += 1; scenes[key].add(scene)
                first.setdefault(key, {'reference': str(png.resolve()), 'x': x, 'y': y, 'flip': flip})
    if not tiles: raise ValueError('No tiles collected')
    entries, families, shared = {}, defaultdict(list), {}
    (output/'shared').mkdir(parents=True, exist_ok=True)
    for key, tile in sorted(tiles.items()):
        family = hashlib.sha256(bytes([tile.bpp, *tile.pixels])).hexdigest()[:16]
        families[family].append(key)
        original = output/'native'/f'{key}.png'
        if not original.exists(): hd.save_rgba(tile.rgba(), original)
        artwork = output/'shared'/f'{key}.png'
        if artwork.exists():
            if hd.load_rgba(artwork).shape != (8*scale, 8*scale, 4):
                raise ValueError(f'{artwork}: expected {8*scale}x{8*scale}')
            shared[key] = f'shared/{key}.png'
        entries[key] = {'palette_family': family, 'recorded_occurrences': counts[key],
                        'scenes': sorted(scenes[key]), 'first_occurrence': first.get(key),
                        'artwork': shared.get(key)}
    report = {'version': 1, 'scale': scale, 'tiles': entries, 'palette_families': families,
              'summary': {'unique_tiles': len(tiles), 'recorded_occurrences': sum(counts.values()),
                          'shared_artwork_ready': len(shared), 'palette_families': len(families)},
              'note': 'One shared source per key. Palette variants and motif-specific artwork remain explicit.'}
    (output/'catalog.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (output/'shared_tiles.json').write_text(json.dumps(shared, indent=2), encoding='utf-8')
    print(json.dumps(report['summary']))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dump', action='append', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--scale', type=int, choices=range(1,11), default=10)
    a = p.parse_args(); catalog(a.dump, a.out, a.scale)


if __name__ == '__main__': main()
