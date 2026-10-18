"""Preview a debug marker with an HD pack: the frozen frame rebuilt from its
VRAM and per-line registers, once with the original tiles and once with the
pack's HD tiles, side by side.

  python tools/hd/hd_preview.py [marker dir | id prefix] [--pack build/hd_pack] [--out preview.png]

Without a marker argument the newest one in build/debug_markers is used.
This is a still-image approximation of what in-game HD rendering will do
(docs/HD_PIPELINE.md, phase B): mode 1 BG layers and sprites with their
priorities on the main screen, at the frame's brightness. Colour math
(transparency, shadows), windows and the widescreen margins are left out.
Tiles the pack does not have are drawn enlarged from the original.
"""
import argparse
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hd_common as hd  # noqa: E402

W, H = hd.FIELD_W, hd.FIELD_H
OBJ_W = [(8, 16), (8, 32), (8, 64), (16, 32), (16, 64), (32, 64), (16, 32), (16, 32)]
OBJ_H = [(8, 16), (8, 32), (8, 64), (16, 32), (16, 64), (32, 64), (32, 64), (32, 32)]


def fnv_key(bpp, pixels, palette):
    h = 1469598103934665603
    def mix(b):
        nonlocal h
        h = ((h ^ b) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    mix(bpp)
    for v in pixels:
        mix(v)
    for c in palette[1:]:
        mix(c & 0xFF)
        mix(c >> 8)
    return f'{h:016x}'


class Machine:
    def __init__(self, marker):
        data = (marker / 'video.bin').read_bytes()
        if len(data) != 0x10420:
            raise ValueError('video.bin has an unsupported size')
        self.vram = struct.unpack('<32768H', data[:0x10000])
        self.cgram = struct.unpack('<256H', data[0x10000:0x10200])
        self.oam = struct.unpack('<256H', data[0x10200:0x10400])
        self.high = data[0x10400:0x10420]
        raw = (marker / 'lines.bin').read_bytes()
        if len(raw) != 225 * 32:
            raise ValueError('lines.bin has an unsupported size (expected 225 x 32 bytes)')
        self.lines = [struct.unpack('<12BH4H4HH', raw[i * 32:(i + 1) * 32]) for i in range(225)]
        modes = {r[3] & 7 for r in self.lines[1:] if r[0] and not r[1] & 0x80}
        if modes - {1}:
            raise ValueError(f'preview currently supports mode 1 only; found {sorted(modes)}')
        if not any(r[0] for r in self.lines[1:]):
            raise ValueError('marker has no recorded scanlines; capture a new marker after a frame runs')

    def line(self, y):
        """Registers of screen row y (ppu_runLine(y + 1))."""
        r = self.lines[y + 1]
        return dict(valid=r[0], inidisp=r[1], obsel=r[2], bgmode=r[3], bgxsc=r[4:8], main=r[8],
                    sub=r[9], tileadr=r[12], hs=r[13:17], vs=r[17:21])

    def decode(self, addr, bpp):
        px = []
        for y in range(8):
            p01 = self.vram[(addr + y) & 0x7FFF]
            p23 = self.vram[(addr + 8 + y) & 0x7FFF] if bpp == 4 else 0
            for x in range(8):
                b = 7 - x
                v = (p01 >> b & 1) | (p01 >> (b + 8) & 1) << 1
                if bpp == 4:
                    v |= (p23 >> b & 1) << 2 | (p23 >> (b + 8) & 1) << 3
                px.append(v)
        return px


class Tiles:
    """Every distinct tile on screen, native and HD."""

    def __init__(self, machine, pack_tiles, scale):
        self.m, self.pack, self.s = machine, pack_tiles, scale
        self.ids, self.native, self.hd, self.hit = {}, [], [], []

    def get(self, addr, bpp, pal_base):
        ident = (addr & 0x7FFF, bpp, pal_base)
        if ident in self.ids:
            return self.ids[ident]
        px = self.m.decode(addr, bpp)
        palette = [self.m.cgram[(pal_base + i) & 255] for i in range(1 << bpp)]
        key = fnv_key(bpp, px, palette)
        native = hd.TileInfo(bpp, palette, px).rgba()
        hd_tile = self.pack.get(key)
        self.hit.append(hd_tile is not None)
        if hd_tile is None:
            hd_tile = native.repeat(self.s, 0).repeat(self.s, 1)
        self.native.append(native)
        self.hd.append(hd_tile)
        self.ids[ident] = len(self.native) - 1
        return self.ids[ident]


def layer_maps():
    return dict(tid=np.full((H, W), -1, np.int32), tx=np.zeros((H, W), np.int32),
                ty=np.zeros((H, W), np.int32), hf=np.zeros((H, W), bool),
                vf=np.zeros((H, W), bool), prio=np.zeros((H, W), np.int32))


def build_bg(m, tiles, layer):
    L = layer_maps()
    for y in range(H):
        r = m.line(y)
        mode = r['bgmode'] & 7
        bpp = {0: 2, 1: 4 if layer < 2 else 2}.get(mode)
        if not r['valid'] or not bpp or r['inidisp'] & 0x80 or not (r['main'] >> layer & 1):
            continue
        big = r['bgmode'] >> (4 + layer) & 1
        tsize = 16 if big else 8
        xsc = r['bgxsc'][layer]
        base = (xsc & 0xFC) << 8
        wide, tall = xsc & 1, xsc & 2
        tbase = (r['tileadr'] >> (layer * 4) & 0xF) << 12
        mw, mh = (64 if wide else 32) * tsize, (64 if tall else 32) * tsize
        hs, vs = r['hs'][layer] & 0x3FF, r['vs'][layer] & 0x3FF
        my = (y + 1 + vs) % mh
        region = layer * 32 if mode == 0 else 0
        for x in range(W):
            mx = (x + hs) % mw
            col, row = mx // tsize, my // tsize
            addr = base + ((col & 31) | (row & 31) << 5)
            if col & 32:
                addr += 0x400
            if row & 32:
                addr += 0x800 if wide else 0x400
            e = m.vram[addr & 0x7FFF]
            hf, vf = bool(e & 0x4000), bool(e & 0x8000)
            tx, ty = mx % tsize, my % tsize
            if hf:
                tx = tsize - 1 - tx
            if vf:
                ty = tsize - 1 - ty
            tile = ((e & 0x3FF) + (tx >> 3) + (ty >> 3) * 16) & 0x3FF if big else e & 0x3FF
            taddr = tbase + tile * (16 if bpp == 4 else 8)
            L['tid'][y, x] = tiles.get(taddr, bpp, region + (e >> 10 & 7) * (1 << bpp))
            L['tx'][y, x], L['ty'][y, x] = tx & 7, ty & 7
            L['hf'][y, x], L['vf'][y, x] = hf, vf
            L['prio'][y, x] = e >> 13 & 1
    return L


def build_obj(m, tiles):
    L = layer_maps()
    r = m.line(112)
    if not r['valid'] or r['inidisp'] & 0x80 or not (r['main'] & 0x10):
        return L
    sel = r['obsel'] >> 5
    base1 = (r['obsel'] & 7) << 13
    base2 = base1 + (((r['obsel'] & 0x18) + 8) << 9)
    for i in range(127, -1, -1):                 # index 0 ends on top
        w0, w1 = m.oam[i * 2], m.oam[i * 2 + 1]
        hi = m.high[i >> 2] >> ((i & 3) * 2) & 3
        x = (w0 & 0xFF) | (hi & 1) << 8
        if x >= 256:
            x -= 512
        y = (w0 >> 8)
        big = hi >> 1 & 1
        w, h = OBJ_W[sel][big], OBJ_H[sel][big]
        if y >= H or x + w <= 0 or x >= W:
            continue
        name, table, pal = w1 & 0xFF, w1 >> 8 & 1, w1 >> 9 & 7
        hf, vf, prio = bool(w1 & 0x4000), bool(w1 & 0x8000), w1 >> 12 & 3
        for cy in range(h // 8):
            for cx in range(w // 8):
                sx = w // 8 - 1 - cx if hf else cx
                sy = h // 8 - 1 - cy if vf else cy
                ch = (((name & 0xF) + sx) & 0xF) | ((((name >> 4) + sy) & 0xF) << 4)
                tid = tiles.get((base2 if table else base1) + ch * 16, 4, 128 + pal * 16)
                nat = tiles.native[tid]
                for py in range(8):
                    for px in range(8):
                        X, Y = x + cx * 8 + px, y + cy * 8 + py
                        if not (0 <= X < W and 0 <= Y < H):
                            continue
                        tx, ty = (7 - px if hf else px), (7 - py if vf else py)
                        if nat[ty, tx, 3] == 0 and L['tid'][Y, X] >= 0:
                            continue                     # keep the lower sprite's pixel
                        L['tid'][Y, X], L['tx'][Y, X], L['ty'][Y, X] = tid, tx, ty
                        L['hf'][Y, X], L['vf'][Y, X], L['prio'][Y, X] = hf, vf, prio
    return L


def render(tables, layers, scale, bg3prio, backdrop, brightness):
    """Composite at `scale` (tables are native tiles for 1, HD tiles for scale)."""
    tsize = 8 * scale
    stack = np.stack(tables) if tables else np.zeros((1, tsize, tsize, 4), np.uint8)
    Y, X = np.mgrid[0:H * scale, 0:W * scale]
    y, x, sy, sx = Y // scale, X // scale, Y % scale, X % scale
    out = np.empty((H * scale, W * scale, 3), np.float32)
    out[:] = backdrop
    planes = [('bg3', 0), ('obj', 0), ('bg3', 1) if not bg3prio else None, ('obj', 1),
              ('bg2', 0), ('bg1', 0), ('obj', 2), ('bg2', 1), ('bg1', 1), ('obj', 3),
              ('bg3', 1) if bg3prio else None]
    for plane in planes:
        if plane is None or plane[0] not in layers:
            continue
        L = layers[plane[0]]
        tid = L['tid'][y, x]
        on = (tid >= 0) & (L['prio'][y, x] == plane[1])
        if not on.any():
            continue
        tx, ty = L['tx'][y, x], L['ty'][y, x]
        u = np.where(L['hf'][y, x], tx * scale + (scale - 1 - sx), tx * scale + sx)
        v = np.where(L['vf'][y, x], ty * scale + (scale - 1 - sy), ty * scale + sy)
        rgba = stack[np.maximum(tid, 0), v, u].astype(np.float32)
        a = (rgba[..., 3:4] / 255.0) * on[..., None]
        out = out * (1 - a) + rgba[..., :3] * a
    out *= brightness / 15.0
    return np.clip(out, 0, 255).astype(np.uint8)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('marker', nargs='?')
    p.add_argument('--markers', type=Path, default=hd.ROOT / 'build' / 'debug_markers')
    p.add_argument('--pack', type=Path, default=hd.ROOT / 'build' / 'hd_pack')
    p.add_argument('--out', type=Path)
    args = p.parse_args()
    marker = Path(args.marker) if args.marker and Path(args.marker).is_dir() else None
    if marker is None:
        found = sorted((d for d in args.markers.iterdir() if (d / 'lines.bin').exists()),
                       key=lambda d: d.name, reverse=True) if args.markers.is_dir() else []
        if args.marker:
            found = [d for d in found if d.name.startswith(args.marker)]
        if not found:
            raise SystemExit('no debug marker with lines.bin found')
        marker = found[0]
    scale, _size, pack_tiles = hd.load_pack(args.pack) if (args.pack / 'pack.json').exists() else (4, 32, {})
    m = Machine(marker)
    tiles = Tiles(m, pack_tiles, scale)
    layers = {'bg1': build_bg(m, tiles, 0), 'bg2': build_bg(m, tiles, 1),
              'bg3': build_bg(m, tiles, 2), 'obj': build_obj(m, tiles)}
    r = m.line(112)
    backdrop = np.array(hd.rgb15(m.cgram[0]), np.float32)
    bright = r['inidisp'] & 0xF
    native = render(tiles.native, layers, 1, r['bgmode'] & 8, backdrop, bright)
    hd_img = render(tiles.hd, layers, scale, r['bgmode'] & 8, backdrop, bright)
    out = args.out or marker / 'hd_preview.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    big_native = Image.fromarray(native).resize((W * scale, H * scale), Image.NEAREST)
    side = Image.new('RGB', (W * scale * 2 + 16, H * scale), (32, 32, 32))
    side.paste(big_native, (0, 0))
    side.paste(Image.fromarray(hd_img), (W * scale + 16, 0))
    side.save(out)
    Image.fromarray(hd_img).save(out.with_name(out.stem + '_hd.png'))
    Image.fromarray(native).save(out.with_name(out.stem + '_native.png'))
    hits = sum(tiles.hit)
    print(f'{out}: {len(tiles.hit)} distinct tiles on screen, {hits} from the pack')
    print('Preview scope: native 256x224 field, mode 1; windows, colour math, mosaic, '
          'sprite limits/rotation and mid-frame graphics/palette writes are not reproduced.')


if __name__ == '__main__':
    main()
