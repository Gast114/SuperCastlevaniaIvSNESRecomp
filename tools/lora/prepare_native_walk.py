"""Derive each walking shape directly from its native atlas cell, without body locking.

One common transform preserves native shoulder/arm motion, root, and phase height.
Native RGB, smoothed Canny guides and alpha masks are retained for review.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-pack', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--canvas', type=int, default=512, choices=(512, 768, 1024))
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('Use a new guide directory')
    args.out.mkdir(parents=True)
    for folder in ('native', 'color', 'alpha'):
        (args.out / folder).mkdir()
    manifest_path = args.native_pack / 'character.json'
    atlas_path = args.native_pack / 'body.png'
    data = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    atlas = Image.open(atlas_path).convert('RGBA')
    cell_size = data['cell_size']
    cols = atlas.width // cell_size
    rows = {f['label']: f for f in data['frames']}
    poses = []
    size = args.canvas
    ratio = size / 512
    scale = 10 * ratio
    review = Image.new('RGB', (1024, 1536), '#555555')
    for i in range(1, 7):
        name = f'Walking-{i:02d}'
        row = rows[name]
        x = row['cell'] % cols * cell_size
        y = row['cell'] // cols * cell_size
        native = atlas.crop((x, y, x + cell_size, y + cell_size))
        native.save(args.out / 'native' / f'{name}.png')
        # x'=(x-48)*10+256; y'=(y-27)*10. No per-frame centering.
        enlarged = native.transform((size, size), Image.Transform.AFFINE,
            (1/scale, 0, 22.4, 0, 1/scale, 27), Image.Resampling.BICUBIC)
        alpha = enlarged.getchannel('A').filter(ImageFilter.GaussianBlur(1.5 * ratio))
        alpha.save(args.out / 'alpha' / f'{name}.png')
        composite = Image.new('RGBA', enlarged.size, (128, 128, 128, 255))
        composite.alpha_composite(enlarged)
        composite = composite.convert('RGB')
        composite.save(args.out / 'color' / f'{name}.png')
        # Suppress per-pixel texture while retaining limb/armor boundaries.
        softened = composite.filter(ImageFilter.GaussianBlur(4.0 * ratio))
        edges = cv2.Canny(np.asarray(softened), 65, 140)
        # Gray background can match a limb's luminance. Always retain the
        # complete silhouette independently of internal palette contrast.
        silhouette = cv2.Canny(np.asarray(alpha), 65, 140)
        edges = np.maximum(edges, silhouette)
        guide = Image.fromarray(edges).convert('RGB')
        guide.save(args.out / f'{name}.png')
        poses.append({'name': name, 'native_id': row['id'], 'cell': row['cell'],
            'native_bbox': native.getbbox(),
            'description': 'Precise shoulders, arms and legs following the contour guide.'})
        pos = ((i - 1) % 2 * 512, (i - 1) // 2 * 512)
        review.paste(composite.resize((512, 512), Image.Resampling.LANCZOS), pos)
        ImageDraw.Draw(review).text((pos[0] + 12, pos[1] + 12), name, fill='white')
    recipe = {'canvas': [size, size], 'root': [256 * ratio, 210 * ratio], 'ground_y': 500 * ratio,
        'origin': 'Native atlas body contours. No guessed skeleton, torso locking or per-frame normalization.',
        'native_pack': str(args.native_pack.resolve()),
        'atlas_sha256': hashlib.sha256(atlas_path.read_bytes()).hexdigest(),
        'transform': {'scale': scale, 'source_origin': [22.4, 27]},
        'edge_preprocess': {'gaussian_radius': 4 * ratio, 'canny_low': 65, 'canny_high': 140,
                            'include_alpha_contour': True},
        'poses': poses}
    (args.out / 'poses.json').write_text(json.dumps(recipe, indent=2), encoding='utf-8')
    review.save(args.out / 'Native_Phasen.png')
    print(args.out.resolve(), flush=True)


if __name__ == '__main__':
    main()
