"""Register painted motif crops to captured game tiles without altering sources.

The recipe records full-layer PNG/TSV references, original crop coordinates and
the painted crop. Only complete captured tiles inside each crop are imported.
Artwork must have at least the requested pixel density; it is never upscaled.
Each occurrence retains its own artwork and a neighborhood signature, so a
shared fragment is never replaced globally. Disagreement is reported for review.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from PIL import Image

import hd_common as hd
from hd_tiles import write_pack


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_recipe(recipe_path, output):
    recipe_path, output = Path(recipe_path).resolve(), Path(output).resolve()
    recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be empty; create a new version to preserve artwork')
    scale = recipe.get('scale', 10)
    if type(scale) is not int or not 1 <= scale <= 10:
        raise ValueError('scale must be an integer in 1..10')
    if recipe.get('version') != 1 or not recipe.get('motifs'):
        raise ValueError('Expected version 1 with nonempty motifs')
    root = recipe_path.parent
    tiles, sources, records, comparisons, contexts, first = {}, {}, [], [], {}, {}
    for motif in recipe['motifs']:
        reference = (root / motif['reference']).resolve()
        mapping = reference.with_suffix('.tsv')
        artwork = (root / motif['artwork']).resolve()
        original = hd.load_rgba(reference)
        if original.shape != (224, 256, 4):
            raise ValueError(f'{reference}: expected a 256x224 layer capture')
        rect = motif['rect']
        if len(rect) != 4 or any(type(v) is not int for v in rect):
            raise ValueError('rect must contain integer x, y, width, height')
        x0, y0, width, height = rect
        if min(x0, y0) < 0 or min(width, height) < 8 or x0 + width > 256 or y0 + height > 224:
            raise ValueError(f'{reference}: crop is outside layer')
        art = Image.open(artwork).convert('RGBA')
        if art.width < width * scale or art.height < height * scale:
            raise ValueError(f'{artwork}: need at least {width*scale}x{height*scale}; got {art.size}')
        # A generated image can differ by one rounding pixel, never by framing.
        if abs(art.width / art.height / (width / height) - 1) > .005:
            raise ValueError(f'{artwork}: aspect ratio differs from the registered crop')
        art_size = art.size
        # This is atlas resampling/registration, not generative artwork editing.
        normalized = np.array(art.resize((width * scale, height * scale), Image.Resampling.LANCZOS))
        accepted = 0
        occurrences = list(hd.occurrences(mapping))
        positions = {(x, y): (key, flip) for x, y, key, flip in occurrences}
        if len(positions) != len(occurrences):
            raise ValueError(f'{mapping}: duplicate tile positions')
        for x, y, key, flip in occurrences:
            if not re.fullmatch(r'[0-9a-f]{16}', key) or flip not in range(4) or not (0 <= x <= 248 and 0 <= y <= 216):
                raise ValueError(f'{mapping}: invalid occurrence')
            if not (x0 <= x and x + 8 <= x0 + width and y0 <= y and y + 8 <= y0 + height):
                continue
            native = original[y:y+8, x:x+8]
            px, py = (x-x0)*scale, (y-y0)*scale
            tile = normalized[py:py+8*scale, px:px+8*scale].copy()
            # Keep generated alpha, bounded to the native silhouette for today's
            # detail compositor. Never force a matte/background to be visible.
            tile[..., 3] = (tile[..., 3].astype(np.uint16) *
                           native[..., 3].repeat(scale, 0).repeat(scale, 1) // 255).astype(np.uint8)
            if flip & 1:
                tile, native = tile[:, ::-1].copy(), native[:, ::-1]
            if flip & 2:
                tile, native = tile[::-1].copy(), native[::-1]
            if key in sources and not np.array_equal(native, sources[key]):
                raise ValueError(f'{key}: reference occurrences disagree; wrong capture/TSV pair')
            sources[key] = native.copy()
            if key in first:
                visible = (first[key][..., 3] > 0) & (tile[..., 3] > 0)
                difference = np.abs(first[key][..., :3].astype(float) - tile[..., :3])
                mae = float(difference[visible].mean()) if visible.any() else 0
                comparisons.append({'key': key, 'motif': motif['name'], 'x': x, 'y': y,
                                    'rgb_mae': round(mae, 3)})
            else:
                first[key] = tile
            offsets = [(dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy]
            offsets += [(d, 0) for d in (-4, -2, 2, 4)] + [(0, d) for d in (-4, -2, 2, 4)]
            neighbors = [[dx, dy, *positions[x+dx*8, y+dy*8]] for dx, dy in offsets
                         if (x+dx*8, y+dy*8) in positions]
            if not neighbors:
                raise ValueError(f'{key}: no neighbors to guard motif placement')
            identity = f"{motif['name']}:{key}:{x}:{y}:{flip}"
            image_key = hashlib.sha256(identity.encode()).hexdigest()[:16]
            if image_key in tiles:
                raise ValueError('Duplicate motif identity; names and occurrences must be unique')
            tiles[image_key] = tile
            contexts.setdefault(key, []).append({'image': image_key, 'flip': flip, 'neighbors': neighbors})
            records.append({'key': key, 'image': image_key, 'motif': motif['name'], 'x': x, 'y': y, 'flip': flip})
            accepted += 1
        if not accepted:
            raise ValueError(f"{motif['name']}: no complete mapped tiles in crop")
        motif['input'] = {'reference_sha256': digest(reference), 'mapping_sha256': digest(mapping),
                          'artwork_sha256': digest(artwork), 'artwork_pixels': list(art_size),
                          'source_pixels_per_native_pixel': min(art_size[0]/width, art_size[1]/height)}
    # Validate every input before creating output; never replace another variant.
    write_pack(tiles, output, scale)
    manifest_path = output / 'pack.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['contexts'] = contexts
    manifest['requires'] = ['tile-context-v1']
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    for key, tile in tiles.items():
        hd.save_rgba(tile, output / 'editable' / f'{key}.png')
    (output / 'editable' / 'contexts.json').write_text(json.dumps({
        'contexts': contexts, 'requires': ['tile-context-v1']}), encoding='utf-8')
    receipt = {'version': 1, 'recipe': recipe, 'recipe_sha256': digest(recipe_path),
               'tiles': records, 'duplicate_occurrences': comparisons,
               'note': 'Context guards per occurrence; geometry and seams still require live review.'}
    (output / 'motifs.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(f'{len(tiles)} tiles at {scale}x; {len(comparisons)} repeated occurrences to review; {output}')
    return tiles, receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--recipe', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    try:
        build_recipe(args.recipe, args.out)
    except (ValueError, KeyError, OSError) as e:
        p.exit(1, f'{e}\n')


if __name__ == '__main__':
    main()
