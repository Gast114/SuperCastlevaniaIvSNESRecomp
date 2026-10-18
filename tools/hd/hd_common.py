"""Shared formats of the HD pipeline (docs/HD_PIPELINE.md).

hd_dump/   written by the game while "Collect graphics" is on (src/hd_collect.cpp)
  tiles.tsv                         key  bpp  palette(4 hex per colour)  64 pixel indices
  captures/<scene>/<layer>_<frame>.png / .tsv   layer picture + clean tile occurrences
hd_work/   intermediate files of tools/hd/hd_upscale.py
  up/<scene>/<layer>_<frame>.png    the upscaled pictures (RGBA, scale x 256 wide)
hd_pack/   tools/hd/hd_build_pack.py
  pack.json + atlas_NNN.png         per key: one tile_size x tile_size RGBA image
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
FIELD_W, FIELD_H = 256, 224
ATLAS = 2048
EXTERNAL = ROOT.parent / 'tools-external'


def rgb15(c):
    """5 to 8 bits exactly as the PPU expands them."""
    x = lambda v: v << 3 | v >> 2
    return (x(c & 31), x(c >> 5 & 31), x(c >> 10 & 31))


class TileInfo:
    __slots__ = ('bpp', 'palette', 'pixels')

    def __init__(self, bpp, palette, pixels):
        self.bpp, self.palette, self.pixels = bpp, palette, pixels

    def rgba(self):
        """Native 8x8 RGBA, colour 0 transparent."""
        out = np.zeros((8, 8, 4), np.uint8)
        for i, v in enumerate(self.pixels):
            if v:
                out[i // 8, i % 8] = (*rgb15(self.palette[v]), 255)
        return out


def load_tiles(dump):
    tiles = {}
    path = Path(dump) / 'tiles.tsv'
    for line in path.read_text().splitlines():
        key, bpp, pal, px = line.split('\t')
        n = 1 << int(bpp)
        tiles[key] = TileInfo(int(bpp), [int(pal[i * 4:i * 4 + 4], 16) for i in range(n)],
                              [int(c, 16) for c in px])
    return tiles


def captures(dump):
    """(scene, stem, png, tsv) for every collected layer picture."""
    for png in sorted((Path(dump) / 'captures').rglob('*.png')):
        yield png.parent.name, png.stem, png, png.with_suffix('.tsv')


def occurrences(tsv):
    for line in Path(tsv).read_text().splitlines():
        x, y, key, flip = line.split('\t')
        yield int(x), int(y), key, int(flip)


def load_rgba(path):
    return np.asarray(Image.open(path).convert('RGBA'))


def save_rgba(array, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.ascontiguousarray(array), 'RGBA').save(path)


def load_pack(pack):
    """(scale, tile_size, {key: tile RGBA array})."""
    pack = Path(pack)
    meta = json.loads((pack / 'pack.json').read_text())
    size = meta['tile_size']
    if meta['version'] != 1 or meta['scale'] not in range(1, 11) or size != 8 * meta['scale']:
        raise ValueError('unsupported HD pack format or scale')
    atlas_size = meta['atlas_size']
    per_row = atlas_size // size
    if per_row < 1:
        raise ValueError('invalid atlas size')
    atlases = {}
    tiles = {}
    for key, (atlas, slot) in meta['tiles'].items():
        if atlas < 0 or not 0 <= slot < per_row * per_row:
            raise ValueError(f'{key}: invalid atlas position')
        if atlas not in atlases:
            atlases[atlas] = load_rgba(pack / f'atlas_{atlas:03d}.png')
            if atlases[atlas].shape[:2] != (atlas_size, atlas_size):
                raise ValueError('atlas dimensions do not match pack.json')
        y, x = divmod(slot, per_row)
        tiles[key] = atlases[atlas][y * size:(y + 1) * size, x * size:(x + 1) * size]
    return meta['scale'], size, tiles


def find_realesrgan():
    exe = EXTERNAL / 'realesrgan' / 'realesrgan-ncnn-vulkan.exe'
    return exe if exe.is_file() else None
