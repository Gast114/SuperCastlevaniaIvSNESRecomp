"""Import registered tile sheets once; reuse their editable sources across captures.

extract: cut a grid of explicitly named, unflipped original keys, never upscale.
pack: register those sources in selected scenes/layers, retaining context guards.
An optional context-only base pack preserves other painted motifs. Sources and
outputs are versioned directories; existing files are never overwritten.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from PIL import Image

import hd_common as hd
from hd_motifs import context_neighbors, digest
from hd_tiles import write_pack


def empty_output(path):
    path = Path(path)
    if path.exists() and any(path.iterdir()):
        raise ValueError(f'{path}: output must be empty; use a new version')
    return path


def compact_contexts(choices):
    """Remove guards already covered by a weaker guard for the same source.

    This is an OR of neighbor conjunctions. Dropping a superset changes no
    accepted neighborhood, including when the live renderer reflects it.
    Never apply this to competing motif images: their search order matters.
    """
    if len({c['image'] for c in choices}) > 1:
        raise ValueError('Context compaction requires one shared image')
    retained, sets = [], []
    for choice in sorted(choices, key=lambda c: len(c['neighbors'])):
        neighbors = frozenset(tuple(n) for n in choice['neighbors'])
        if not neighbors:
            raise ValueError('Cannot compact unguarded contexts')
        if any(flip == choice['flip'] and subset <= neighbors for flip, subset in sets):
            continue
        retained.append(choice)
        sets.append((choice['flip'], neighbors))
    return retained


def extract(recipe_path, dump, output):
    output = empty_output(output)
    recipe_path = Path(recipe_path).resolve()
    recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
    scale = recipe['scale']
    if recipe['version'] != 1 or type(scale) is not int or not 1 <= scale <= 10:
        raise ValueError('Expected version 1, scale 1..10')
    native = hd.load_tiles(dump)
    tiles, sources = {}, []
    for sheet in recipe['sheets']:
        path = recipe_path.parent / sheet['image']
        keys, cols = sheet['keys'], sheet['columns']
        if not keys or type(cols) is not int or cols < 1 or len(keys) % cols:
            raise ValueError('Sheet needs a complete rectangular grid of keys')
        rows = len(keys) // cols
        art = hd.load_rgba(path)
        if sheet.get('opaque_material') and np.any(art[..., 3] != 255):
            raise ValueError(f'{path}: material atlas must be fully opaque; native cutout is applied separately')
        height, width = art.shape[:2]
        if width * rows != height * cols:
            raise ValueError(f'{path}: grid cells must be square')
        cell = width / cols
        if cell < 8*scale:
            raise ValueError(f'{path}: insufficient pixels per tile; refusing to upscale')
        # Generated atlases can place cell edges at half pixels (e.g. 1774x887
        # for a 4x2 grid). Register that exact aspect as a whole before cutting.
        normalized = None if cell.is_integer() else np.array(Image.fromarray(art).resize(
            (cols*8*scale, rows*8*scale), Image.Resampling.LANCZOS))
        reference = None
        reference_path = recipe_path.parent / sheet['reference'] if sheet.get('reference') else None
        if reference_path:
            with Image.open(reference_path) as ref:
                if ref.width * rows != ref.height * cols:
                    raise ValueError(f'{reference_path}: reference grid aspect differs')
                reference = np.array(ref.convert('RGBA').resize((cols*8, rows*8), Image.Resampling.NEAREST))
        for n, key in enumerate(keys):
            if key is None:  # Explicit unused atlas cell, never an implicit alias.
                continue
            if not re.fullmatch('[0-9a-f]{16}', key) or key not in native or key in tiles:
                raise ValueError(f'{key}: unknown, invalid or duplicate original key')
            y, x = divmod(n, cols)
            original = native[key].rgba()
            if reference is not None:
                ref_tile = reference[y*8:(y+1)*8, x*8:(x+1)*8]
                visible = original[..., 3] > 0
                if not np.array_equal(ref_tile[..., 3], original[..., 3]) or not np.array_equal(ref_tile[visible], original[visible]):
                    raise ValueError(f'{key}: reference does not match unflipped original tile')
            if normalized is None:
                c = int(cell)
                crop = art[y*c:(y+1)*c, x*c:(x+1)*c]
                tile = np.array(Image.fromarray(crop).resize((8*scale, 8*scale), Image.Resampling.LANCZOS))
            else:
                tile = normalized[y*8*scale:(y+1)*8*scale, x*8*scale:(x+1)*8*scale].copy()
            # Same native silhouette contract as the current live compositor.
            alpha = original[..., 3].repeat(scale, 0).repeat(scale, 1)
            tile[..., 3] = (tile[..., 3].astype(np.uint16) * alpha // 255).astype(np.uint8)
            tiles[key] = tile
        sources.append({'image': str(path.resolve()), 'sha256': digest(path),
                        'reference_sha256': digest(reference_path) if reference_path else None,
                        'pixels': [width, height], 'pixels_per_tile': cell, 'keys': keys})
    if not tiles:
        raise ValueError('No artwork in recipe')
    for key, tile in tiles.items():
        hd.save_rgba(tile, output/'shared'/f'{key}.png')
    (output/'shared_tiles.json').write_text(json.dumps({k: f'shared/{k}.png' for k in tiles}, indent=2))
    (output/'sources.json').write_text(json.dumps({'recipe': recipe, 'recipe_sha256': digest(recipe_path),
                                                 'tiles_sha256': digest(Path(dump)/'tiles.tsv'),
                                                 'sources': sources}, indent=2))
    print(f'{len(tiles)} shared sources at {scale}x: {output}')
    return tiles


def register(library, dumps, scene, layers, output, base=None):
    output = empty_output(output)
    library = Path(library).resolve()
    entries = json.loads(library.read_text(encoding='utf-8'))
    shared = {key: hd.load_rgba(library.parent/path) for key, path in entries.items()}
    if not shared:
        raise ValueError('Empty library')
    size = next(iter(shared.values())).shape[0]
    if size % 8 or not 1 <= size//8 <= 10:
        raise ValueError('Expected tile dimensions 8..80 in multiples of eight')
    scale = size//8
    for key, tile in shared.items():
        if not re.fullmatch('[0-9a-f]{16}', key) or tile.shape != (size, size, 4):
            raise ValueError(f'{key}: invalid library key or dimensions')
    images, contexts, base_files = {}, {}, {}
    if base:
        base = Path(base)
        base_meta = json.loads((base/'pack.json').read_text())
        bs, _, images = hd.load_pack(base)
        if bs != scale or not base_meta.get('contexts') or base_meta.get('requires') != ['tile-context-v1']:
            raise ValueError('Base must be a context-only pack at the same scale')
        used = {c['image'] for choices in base_meta['contexts'].values() for c in choices}
        if set(images) != used:
            raise ValueError('Base contains unguarded images; explicit migration required')
        contexts = {k: v for k, v in base_meta['contexts'].items() if k not in shared}
        base_files = {p.name: digest(p) for p in base.glob('*') if p.suffix in ('.json', '.png')}
    # Shared image identifiers are content-addressed, just like motif images.
    ids = {}
    for key, tile in shared.items():
        ident = hashlib.sha256(tile.tobytes()).hexdigest()[:16]
        if ident in images and not np.array_equal(tile, images[ident]):
            raise ValueError('Image identifier collision')
        images[ident] = tile; ids[key] = ident
    counts, unique, inputs, original_inputs = Counter(), {k: {} for k in shared}, [], []
    for dump in dumps:
        native = hd.load_tiles(dump)
        original_inputs.append({'path': str(Path(dump).resolve()), 'tiles_sha256': digest(Path(dump)/'tiles.tsv')})
        for key in shared.keys() & native.keys():
            alpha = native[key].rgba()[..., 3].repeat(scale, 0).repeat(scale, 1)
            if np.any(shared[key][..., 3] > alpha):
                raise ValueError(f'{key}: edited source extends beyond current native silhouette contract')
        for name, stem, _, tsv in hd.captures(dump):
            if name != scene or stem.split('_')[0] not in layers:
                continue
            occurrences = list(hd.occurrences(tsv))
            positions = {(x, y): (key, flip) for x, y, key, flip in occurrences}
            if len(positions) != len(occurrences):
                raise ValueError(f'{tsv}: duplicate positions')
            inputs.append({'mapping': str(tsv.resolve()), 'sha256': digest(tsv)})
            for x, y, key, flip in occurrences:
                if key not in shared:
                    continue
                if key not in native or flip not in range(4) or not 0 <= x <= 248 or not 0 <= y <= 216:
                    raise ValueError(f'{tsv}: invalid original occurrence')
                neighbors = context_neighbors(positions, x, y)
                if not neighbors:
                    continue
                choice = {'image': ids[key], 'flip': flip, 'neighbors': neighbors}
                unique[key][json.dumps(choice, sort_keys=True)] = choice
                counts[key] += 1
    for key in shared:
        if not unique[key]:
            raise ValueError(f'{key}: no guarded occurrence in selected captures')
        contexts[key] = compact_contexts(list(unique[key].values()))
    if sum(map(len, contexts.values())) > 16384:
        raise ValueError('Pack exceeds live context limit')
    used = {c['image'] for choices in contexts.values() for c in choices}
    images = {key: tile for key, tile in images.items() if key in used}
    write_pack(images, output, scale)
    meta = json.loads((output/'pack.json').read_text())
    extra = {'contexts': contexts, 'requires': ['tile-context-v1']}
    meta.update(extra)
    (output/'pack.json').write_text(json.dumps(meta))
    for key, tile in images.items():
        hd.save_rgba(tile, output/'editable'/f'{key}.png')
    (output/'editable/contexts.json').write_text(json.dumps(extra))
    receipt = {'library': str(library), 'library_sha256': digest(library),
               'sources': {k: {'path': str(library.parent/entries[k]),
                               'sha256': digest(library.parent/entries[k])} for k in shared},
               'scene': scene, 'layers': layers, 'base': str(base) if base else None,
               'base_files': base_files, 'captures': inputs, 'original_inputs': original_inputs,
               'recorded_occurrences': dict(counts), 'unique_contexts': {k: len(v) for k, v in unique.items()},
               'registered_contexts': {k: len(contexts[k]) for k in shared},
               'shared_tiles': len(shared), 'pack_images': len(images)}
    (output/'shared-receipt.json').write_text(json.dumps(receipt, indent=2))
    print(f'{len(shared)} shared sources, {sum(counts.values())} captured uses, '
          f'{sum(map(len, unique.values()))} distinct guards, '
          f'{sum(len(contexts[k]) for k in shared)} after compaction: {output}')
    return meta, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('extract')
    p.add_argument('--recipe', type=Path, required=True)
    p.add_argument('--dump', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('pack')
    p.add_argument('--library', type=Path, required=True)
    p.add_argument('--dump', type=Path, action='append', required=True)
    p.add_argument('--scene', required=True)
    p.add_argument('--layers', nargs='+', choices=('bg1', 'bg2', 'bg3'), default=['bg1'])
    p.add_argument('--base', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = parser.parse_args()
    if a.action == 'extract': extract(a.recipe, a.dump, a.out)
    else: register(a.library, a.dump, a.scene, a.layers, a.out, a.base)


if __name__ == '__main__':
    main()
