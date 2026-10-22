"""Compare local generated walking phases with native shapes at identical coordinates.

No automatic bbox alignment: that would hide incorrect hand or foot positions.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--guides', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    sources = sorted(args.source.glob('Walking-[0-9][0-9].png'))
    if not sources:
        raise ValueError('No rendered walking phase found')
    if args.out.exists():
        raise FileExistsError('Use a new review directory')
    args.out.mkdir(parents=True)
    panels = []
    for path in sources:
        native = Image.open(args.guides / 'color' / path.name).convert('RGB')
        rendered = Image.open(path).convert('RGB')
        if native.size != rendered.size:
            raise ValueError('Native guide and generated frame must share coordinates')
        alpha = np.asarray(Image.open(args.guides / 'alpha' / path.name)) > 127
        core = alpha.copy()
        core[1:-1, 1:-1] &= (alpha[2:, 1:-1] & alpha[:-2, 1:-1]
                                  & alpha[1:-1, 2:] & alpha[1:-1, :-2])
        border = alpha & ~core
        overlay = np.asarray(rendered).copy()
        overlay[border] = (40, 255, 80)
        panel = Image.new('RGB', (1536, 552), '#343434')
        for i, image in enumerate((native, rendered, Image.fromarray(overlay))):
            panel.paste(image.resize((512, 512), Image.Resampling.LANCZOS), (i * 512, 40))
        draw = ImageDraw.Draw(panel)
        for i, title in enumerate(('Original ' + path.stem, 'HD: gleiche Koordinaten', 'Gruen: Originalkontur')):
            draw.text((i * 512 + 12, 12), title, fill='white')
        panel.save(args.out / (path.stem + '-Vergleich.png'))
        panels.append(panel)
    if len(panels) > 1:
        panels[0].save(args.out / 'Originalvergleich.webp', save_all=True,
            append_images=panels[1:], duration=110, loop=0, lossless=True)
    (args.out / 'review.json').write_text(json.dumps({
        'source': str(args.source.resolve()), 'guides': str(args.guides.resolve()),
        'frames': [p.name for p in sources], 'per_frame_alignment': False,
        'note': 'Visual geometry review, not automatic approval of anatomy or design.'}, indent=2), encoding='utf-8')
    print(args.out.resolve(), flush=True)


if __name__ == '__main__':
    main()
