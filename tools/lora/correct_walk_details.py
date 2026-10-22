"""Reuse smooth knee/shin artwork from another walking phase, entirely locally.

Pixel-preserving composites change only the explicitly marked knee regions.
No diffusion calls, new images from a model, per-frame resizing or game writes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw, ImageFilter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'masks', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    args.out.mkdir(parents=True)
    recipe = json.loads(args.masks.read_text(encoding='utf-8'))
    for source in sorted(args.source.glob('Walking-[0-9][0-9].png')):
        shutil.copy2(source, args.out / source.name)
    records = []
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    for row in recipe['images']:
        source = args.source / row['image']
        donor_path = args.source / row['donor']
        final = Image.open(source).convert('RGB')
        donor = Image.open(donor_path).convert('RGB')
        combined = Image.new('L', final.size, 0)
        for patch in row['patches']:
            mask = Image.new('L', final.size, 0)
            ImageDraw.Draw(mask).polygon([tuple(point) for point in patch['polygon']], fill=255)
            dx, dy = patch['translation']
            translated = donor.transform(final.size, Image.Transform.AFFINE,
                (1, 0, -dx, 0, 1, -dy), Image.Resampling.NEAREST)
            feather = mask.filter(ImageFilter.GaussianBlur(1.2))
            final = Image.composite(translated, final, feather)
            combined = Image.composite(mask, combined, mask)
        target = args.out / source.name
        final.save(target)
        combined.save(args.out / (source.stem + '-detail-mask.png'))
        records.append({'image': source.name, 'donor': row['donor'],
            'source_sha256': sha(source), 'donor_sha256': sha(donor_path),
            'output_sha256': sha(target)})
    (args.out / 'detail-corrections.json').write_text(json.dumps({
        'method': 'local reuse of smooth knee/shin artwork with masked integer translation',
        'per_frame_scaling': False, 'recipe': str(args.masks.resolve()), 'images': records,
        'uploaded': False, 'game_pack_installed': False}, indent=2), encoding='utf-8')
    print('Corrected locally:', len(records), 'frames')


if __name__ == '__main__':
    main()
