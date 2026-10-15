"""Build a labelled contact sheet from present_NNNNNN.ppm files using presents.csv frame numbers."""
import csv
import pathlib
import sys

from PIL import Image, ImageDraw

shots = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])
first, last, step = (int(v) for v in sys.argv[3:6])
cols = int(sys.argv[6]) if len(sys.argv) > 6 else 4
scale = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0

by_frame = {}
with open(shots / 'presents.csv', newline='') as f:
    for row in csv.DictReader(f):
        by_frame.setdefault(int(row['frame']), int(row['present']))

frames = [n for n in range(first, last + 1, step) if n in by_frame]
tiles = []
for n in frames:
    img = Image.open(shots / f'present_{by_frame[n]:06d}.ppm').convert('RGB')
    if scale != 1.0:
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.NEAREST)
    ImageDraw.Draw(img).rectangle((0, 0, 70, 12), fill=(0, 0, 0))
    ImageDraw.Draw(img).text((3, 1), f'f{n}', fill=(255, 255, 0))
    tiles.append(img)

w, h = tiles[0].size
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new('RGB', (cols * (w + 4), rows * (h + 4)), (255, 0, 255))
for i, img in enumerate(tiles):
    sheet.paste(img, ((i % cols) * (w + 4), (i // cols) * (h + 4)))
sheet.save(out)
print(f'{len(tiles)} frames -> {out} ({sheet.width}x{sheet.height})')
