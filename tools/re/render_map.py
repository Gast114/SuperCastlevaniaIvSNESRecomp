"""Render a whole BG tilemap from a `sciv_play.py dump` file to PNG.

  render_map.py <dump.bin> <out.png> --map 0x1000 --tiles 0x2000 [--wide] [--tall] [--bpp 4]
                [--scale 2] [--grid]

Addresses are VRAM word addresses, exactly as `sciv_play.py ppu` reports them.
Colour 0 (transparent) is drawn as a dark checkerboard. With --grid every map
column and row is outlined and labelled, which is what you need to pick source
columns when designing widescreen margin columns (src/widescreen_fill.c).
"""
import argparse
import struct

from PIL import Image, ImageDraw


def rgb(c):
    return ((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dump')
    ap.add_argument('out')
    ap.add_argument('--map', type=lambda v: int(v, 0), required=True)
    ap.add_argument('--tiles', type=lambda v: int(v, 0), required=True)
    ap.add_argument('--wide', action='store_true')
    ap.add_argument('--tall', action='store_true')
    ap.add_argument('--bpp', type=int, default=4, choices=(2, 4))
    ap.add_argument('--scale', type=int, default=1)
    ap.add_argument('--grid', action='store_true')
    a = ap.parse_args()

    data = open(a.dump, 'rb').read()
    vram = struct.unpack('<32768H', data[:0x10000])
    cgram = struct.unpack('<256H', data[0x10000:0x10200])
    cols, rows = (64 if a.wide else 32), (64 if a.tall else 32)
    img = Image.new('RGB', (cols * 8, rows * 8))
    px = img.load()
    words = 16 if a.bpp == 4 else 8
    for row in range(rows):
        for col in range(cols):
            entry = vram[(a.map + ((col >> 5) << 10) + ((row >> 5) << (11 if a.wide else 10))
                          + ((row & 31) << 5) + (col & 31)) & 0x7fff]
            tile, pal = entry & 0x3ff, entry >> 10 & 7
            hflip, vflip = entry & 0x4000, entry & 0x8000
            base = (a.tiles + tile * words) & 0x7fff
            for y in range(8):
                ty = 7 - y if vflip else y
                p01 = vram[(base + ty) & 0x7fff]
                p23 = vram[(base + ty + 8) & 0x7fff] if a.bpp == 4 else 0
                for x in range(8):
                    bit = 7 - x
                    c = (p01 >> bit & 1) | (p01 >> (bit + 8) & 1) << 1
                    if a.bpp == 4:
                        c |= (p23 >> bit & 1) << 2 | (p23 >> (bit + 8) & 1) << 3
                    tx = 7 - x if hflip else x
                    X, Y = col * 8 + tx, row * 8 + y
                    if c:
                        px[X, Y] = rgb(cgram[(pal * (16 if a.bpp == 4 else 4) + c) & 255])
                    else:
                        px[X, Y] = (24, 24, 32) if ((X >> 2) + (Y >> 2)) & 1 else (16, 16, 20)
    if a.scale > 1:
        img = img.resize((img.width * a.scale, img.height * a.scale), Image.NEAREST)
    if a.grid:
        d = ImageDraw.Draw(img)
        s = 8 * a.scale
        for col in range(cols + 1):
            d.line([(col * s, 0), (col * s, img.height)], fill=(80, 80, 0) if col % 4 else (200, 200, 0))
        for row in range(rows + 1):
            d.line([(0, row * s), (img.width, row * s)], fill=(80, 80, 0) if row % 4 else (200, 200, 0))
        for col in range(0, cols, 4):
            d.text((col * s + 1, 1), str(col), fill=(255, 255, 255))
        for row in range(4, rows, 4):
            d.text((1, row * s + 1), str(row), fill=(255, 255, 255))
    img.save(a.out)


if __name__ == '__main__':
    main()
