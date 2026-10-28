"""Import the user's completed A02 PNGs and retain the entrance in one collection.

Only working copies are resized slightly downward to the calibrated four-pixel
source density. Presentation uses the artwork density. Source artwork is never changed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(source, entrance, output, recipe_path=ROOT / 'assets/hd/stage_01_a02.recipe.json'):
    source, entrance, output = Path(source), Path(entrance), Path(output)
    if output.exists():
        raise FileExistsError('Use a new output folder')
    recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
    scale = recipe['scale']
    ratio = scale * recipe['source_pixels_per_native'][1] / recipe['source_pixels_per_native'][0]
    if not 0 < ratio <= 1:
        raise ValueError('The importer only downsamples artwork')
    output.mkdir(parents=True)
    shutil.copytree(entrance, output / 'entrance')
    target = output / 'a02'
    target.mkdir()
    regions, receipts = [], []

    def manual(image, name):
        # Registered game PNGs already include density conversion and padding.
        # Stable source names survive region renumbering in later builds.
        options = recipe.get('registered_overrides')
        if not options:
            return image
        path = source / options['directory'] / name
        if not path.is_file():
            return image
        if options['scale'] != scale:
            raise ValueError('Manual corrections use a different artwork scale')
        with Image.open(path) as replacement:
            if replacement.mode != 'RGBA' or replacement.size != image.size:
                raise ValueError(f'{path}: registered RGBA canvas {image.size} required')
            result = replacement.copy()
        receipts.append({'source': str(path.resolve()), 'sha256': sha(path),
                         'size': list(result.size), 'kind': 'registered-manual-correction',
                         'replaces': name})
        return result

    def load(name):
        path = source / name
        with Image.open(path) as im:
            if im.mode != 'RGBA':
                raise ValueError(f'{name}: RGBA required')
            pixels = im.copy()
        receipts.append({'source': str(path.resolve()), 'sha256': sha(path), 'size': list(pixels.size)})
        return pixels

    def emit(image, spec):
        # The native compositor uses integer origins; preserve the remaining
        # high-resolution offset as transparent padding inside the image.
        for left in range(0, image.width, 4096):
            part = image.crop((left, 0, min(left+4096, image.width), image.height))
            name = f'region_{len(regions):02d}.png'
            part.save(target / name)
            regions.append({**spec, 'image': name, 'x': spec['x']+left//scale})

    def register(image, origin):
        resized = image.resize((round(image.width*ratio), round(image.height*ratio)), Image.Resampling.LANCZOS)
        gx, gy = [round(n*ratio) for n in origin]
        px, py = gx % scale, gy % scale
        canvas = Image.new('RGBA', (((px+resized.width+scale-1)//scale)*scale,
                                    ((py+resized.height+scale-1)//scale)*scale))
        canvas.paste(resized, (px, py))
        return canvas, gx//scale, gy//scale

    for plane in recipe['planes']:
        image = load(plane['image'])
        # The reference sheet includes a repeated 64-pixel castle bay absent
        # from the runtime map. Register the following art without stretching.
        for left, right in reversed(plane.get('remove_native_x', [])):
            density = recipe['source_pixels_per_native'][0] / recipe['source_pixels_per_native'][1]
            a, b = round(left*density), round(right*density)
            joined = Image.new('RGBA', (image.width-(b-a), image.height))
            joined.paste(image.crop((0,0,a,image.height)), (0,0))
            joined.paste(image.crop((b,0,image.width,image.height)), (a,0))
            image = joined
        canvas, x, y = register(image, plane['origin_px'])
        canvas = manual(canvas, plane['image'])
        spec = {'layer': plane['layer'], 'x': x, 'y': y,
                'coordinates': 'world', 'wrap_x': 0, 'wrap_y': 0, 'modes': [1],
                'priority': plane['priority'], 'overlay': plane['overlay']}
        if 'a02_kind' in plane:
            spec['a02_kind'] = plane['a02_kind']
        emit(canvas, spec)

    def fit(image, size, right=False):
        width, height = (n*scale for n in size)
        factor = min(width/image.width, height/image.height, 1)
        resized = image.resize((round(image.width*factor), round(image.height*factor)), Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA', (width, height))
        canvas.paste(resized, (width-resized.width if right else (width-resized.width)//2, height-resized.height))
        return canvas

    door = recipe['doors']
    for phase, name in enumerate(door['images']):
        frame = fit(load(name), door['size'], right=True)
        frame = manual(frame, name)
        for x, y in door['origins']:
            emit(frame, {'layer': 0, 'x': x, 'y': y, 'coordinates': 'world',
                         'wrap_x': 0, 'wrap_y': 0, 'modes': [1], 'overlay': 1,
                         'priority': 49151, 'a02_kind': 2, 'phase': phase})

    statue = recipe['gargoyle']
    for phase, name in enumerate(statue['images']):
        frame, x, y = register(load(name), statue['origin_px'])
        frame = manual(frame, name)
        dx, dy = statue.get('offset_native', [0, 0])
        x += dx; y += dy
        emit(frame, {'layer': 1, 'x': x, 'y': y,
             'coordinates': 'world', 'wrap_x': 0, 'wrap_y': 0, 'modes': [1],
             'overlay': 1, 'priority': 28929, 'a02_kind': 3, 'phase': phase,
             'phase_probe': statue['phase_probe']})

    pack = {'version': 1, 'scale': scale, 'tile_size': scale*8, 'atlas_size': 2048, 'tiles': {},
            'requires': ['scene-regions-v1', 'scene-overlays-v1'], 'sciv_a02': 1,
            'scene_block': recipe['scene_block'], 'native_maps': recipe['native_maps'], 'regions': regions}
    (target / 'pack.json').write_text(json.dumps(pack, indent=2))
    (output / 'pack.json').write_text(json.dumps({'version': 1, 'name': 'Stage 01 entrance + A02 user artwork', 'scenes': ['entrance', 'a02']}, indent=2))
    receipt = {'recipe_sha256': sha(recipe_path), 'builder_sha256': sha(__file__),
               'source_pixels_per_native': recipe['source_pixels_per_native'], 'art_scale': scale,
               'presentation_scale': scale, 'resampling': 'slight downsampling; no image generation or source modifications',
               'sources': receipts, 'regions': regions}
    (output / 'import.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(output.resolve()), 'source_images': len(receipts), 'a02_regions': len(regions)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--entrance', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build(args.source, args.entrance, args.out)
