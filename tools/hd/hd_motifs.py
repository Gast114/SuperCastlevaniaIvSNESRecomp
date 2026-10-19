"""Register painted motif crops to captured game tiles without altering sources.

The recipe records full-layer PNG/TSV references, original crop coordinates and
the painted crop. Only complete captured tiles inside each crop are imported.
Artwork must have at least the requested pixel density; it is never upscaled.
Occurrences retain neighborhood guards and can reference one shared artwork
source per original key. Identical images share storage; different painted
variants remain separate. Disagreement is reported for review.
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


def context_neighbors(positions, x, y):
    offsets = [(dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy]
    offsets += [(d, 0) for d in (-4, -2, 2, 4)] + [(0, d) for d in (-4, -2, 2, 4)]
    return [[dx, dy, *positions[x+dx*8, y+dy*8]] for dx, dy in offsets
            if (x+dx*8, y+dy*8) in positions]


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
    definitions = {}
    if recipe.get('shared_library'):
        library = (root / recipe['shared_library']).resolve()
        definitions.update({key: (library.parent / filename, str((library.parent / filename).resolve()))
                            for key, filename in json.loads(library.read_text(encoding='utf-8')).items()})
    definitions.update({key: (root / filename, str(filename))
                        for key, filename in recipe.get('shared_tiles', {}).items()})
    shared = {}
    for key, (path, filename) in definitions.items():
        tile = hd.load_rgba(path)
        if not re.fullmatch(r'[0-9a-f]{16}', key) or tile.shape != (8*scale, 8*scale, 4):
            raise ValueError(f'{path}: shared tile needs a valid original key and {8*scale}x{8*scale} pixels')
        shared[key] = (tile, str(filename), digest(path))
    tiles, sources, records, comparisons, contexts, first = {}, {}, [], [], {}, {}
    for motif in recipe['motifs']:
        reference = (root / motif['reference']).resolve()
        mapping = reference.with_suffix('.tsv')
        artwork = (root / motif['artwork']).resolve() if motif.get('artwork') else None
        original = hd.load_rgba(reference)
        if original.shape != (224, 256, 4):
            raise ValueError(f'{reference}: expected a 256x224 layer capture')
        rect = motif['rect']
        if len(rect) != 4 or any(type(v) is not int for v in rect):
            raise ValueError('rect must contain integer x, y, width, height')
        x0, y0, width, height = rect
        if min(x0, y0) < 0 or min(width, height) < 8 or x0 + width > 256 or y0 + height > 224:
            raise ValueError(f'{reference}: crop is outside layer')
        art = Image.open(artwork).convert('RGBA') if artwork else None
        if art and (art.width < width * scale or art.height < height * scale):
            raise ValueError(f'{artwork}: need at least {width*scale}x{height*scale}; got {art.size}')
        # A generated image can differ by one rounding pixel, never by framing.
        if art and abs(art.width / art.height / (width / height) - 1) > .005:
            raise ValueError(f'{artwork}: aspect ratio differs from the registered crop')
        art_size = art.size if art else None
        # This is atlas resampling/registration, not generative artwork editing.
        normalized = np.array(art.resize((width * scale, height * scale), Image.Resampling.LANCZOS)) if art else None
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
            tile = normalized[py:py+8*scale, px:px+8*scale].copy() if normalized is not None else None
            # Keep generated alpha, bounded to the native silhouette for today's
            # detail compositor. Never force a matte/background to be visible.
            if tile is not None:
                tile[..., 3] = (tile[..., 3].astype(np.uint16) *
                           native[..., 3].repeat(scale, 0).repeat(scale, 1) // 255).astype(np.uint8)
            if flip & 1:
                tile, native = tile[:, ::-1].copy() if tile is not None else None, native[:, ::-1]
            if flip & 2:
                tile, native = tile[::-1].copy() if tile is not None else None, native[::-1]
            if key in shared:
                # Shared images are authored once in the tile's unflipped pose.
                tile = shared[key][0].copy()
                tile[..., 3] = (tile[..., 3].astype(np.uint16) *
                               native[..., 3].repeat(scale, 0).repeat(scale, 1) // 255).astype(np.uint8)
            if tile is None:
                raise ValueError(f'{key}: missing shared tile and no motif artwork provided')
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
            neighbors = context_neighbors(positions, x, y)
            if not neighbors:
                raise ValueError(f'{key}: no neighbors to guard motif placement')
            # Identical pixels share one editable image and one atlas slot,
            # regardless of how many motifs or placement guards reference it.
            image_key = hashlib.sha256(tile.tobytes()).hexdigest()[:16]
            if image_key in tiles and not np.array_equal(tiles[image_key], tile):
                raise ValueError('Image key collision')
            tiles[image_key] = tile
            contexts.setdefault(key, []).append({'image': image_key, 'flip': flip, 'neighbors': neighbors})
            records.append({'key': key, 'image': image_key, 'motif': motif['name'], 'x': x, 'y': y, 'flip': flip,
                            'shared_source': shared[key][1] if key in shared else None})
            accepted += 1
        if not accepted:
            raise ValueError(f"{motif['name']}: no complete mapped tiles in crop")
        motif['input'] = {'reference_sha256': digest(reference), 'mapping_sha256': digest(mapping),
                          'artwork_sha256': digest(artwork) if artwork else None, 'artwork_pixels': art_size,
                          'source_pixels_per_native_pixel': min(art_size[0]/width, art_size[1]/height) if art_size else None}
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
               'shared_sources': {k: {'path': v[1], 'sha256': v[2]} for k, v in shared.items()},
               'reuse': {'placements': len(records), 'unique_images': len(tiles),
                         'reused_images': len(records)-len(tiles),
                         'original_keys': len(contexts)},
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
