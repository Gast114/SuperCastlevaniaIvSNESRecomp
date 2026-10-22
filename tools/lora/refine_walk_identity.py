"""Refine an existing walk locally using shared head artwork and explicit part masks.

No diffusion, uploads, full-torso copies or game-pack writes. Affine/projective
part transforms retain the accepted per-frame shoulder, elbow and leg movement.
The JSON recipe is the editable source of every correction.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def polygon(size, points, feather=0):
    image = Image.new('L', size)
    ImageDraw.Draw(image).polygon([tuple(p) for p in points], fill=255)
    if feather:
        image = image.filter(ImageFilter.GaussianBlur(feather))
    return np.asarray(image, dtype=np.float32) / 255


def premultiply(rgba):
    result = rgba.copy()
    result[..., :3] *= result[..., 3:]
    return result


def unpremultiply(rgba):
    result = rgba.copy()
    np.divide(result[..., :3], result[..., 3:], out=result[..., :3],
              where=result[..., 3:] > 1e-7)
    result[..., :3][result[..., 3] <= 1e-7] = 0
    return np.clip(result, 0, 1)


def over(top, bottom):
    alpha = top[..., 3:] + bottom[..., 3:] * (1 - top[..., 3:])
    rgb = top[..., :3] * top[..., 3:] + bottom[..., :3] * bottom[..., 3:] * (1 - top[..., 3:])
    return np.concatenate([np.divide(rgb, alpha, out=np.zeros_like(rgb), where=alpha > 1e-7), alpha], axis=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Full, common-canvas RGBA frames')
    parser.add_argument('--recipe', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('Use a new refinement directory')
    recipe = json.loads(args.recipe.read_text(encoding='utf-8'))
    originals = {path.name: np.asarray(Image.open(path).convert('RGBA'), dtype=np.float32) / 255
                 for path in sorted(args.source.glob('Walking-[0-9][0-9].png'))}
    if len(originals) != 6:
        raise ValueError('Expected six original walking frames')
    height, width = next(iter(originals.values())).shape[:2]
    if [width, height] != recipe.get('canvas', [1024, 1024]):
        raise ValueError('Recipe and input canvas differ')
    if any(image.shape != (height, width, 4) for image in originals.values()):
        raise ValueError('All frames must share a canvas')
    args.out.mkdir(parents=True)
    records = []
    for name, source in originals.items():
        image = source.copy()
        operations = recipe['frames'].get(name, [])
        for operation in operations:
            kind = operation['kind']
            if kind == 'erase':
                mask = polygon((width, height), operation['polygon'], operation.get('feather', .8))
                image[..., 3] *= 1 - mask
            elif kind == 'head':
                donor = originals[operation['donor']]
                dx, dy = operation['translation']
                moved = cv2.warpAffine(premultiply(donor), np.float32([[1, 0, dx], [0, 1, dy]]),
                    (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                moved = unpremultiply(moved)
                knots = np.asarray(recipe['head_cut'], dtype=np.float32)
                cut = np.interp(np.arange(width) - dx, knots[:, 0], knots[:, 1]) + dy
                weight = np.clip((cut[None, :] + 3 - np.arange(height)[:, None]) / 6, 0, 1)[..., None]
                # Blend the neck join, but select one silhouette at outer edges.
                a, b = premultiply(moved), premultiply(image)
                result = unpremultiply(a * weight + b * (1 - weight))
                contour = np.abs(moved[..., 3] - image[..., 3]) > .1
                selected = np.where(weight >= .5, moved, image)
                result[contour] = selected[contour]
                image = result
            elif kind == 'patch':
                donor = originals[operation['donor']]
                start = np.float32(operation['source_points'])
                end = np.float32(operation['target_points'])
                if len(start) == 3:
                    matrix = cv2.getAffineTransform(start, end)
                    moved = cv2.warpAffine(premultiply(donor), matrix, (width, height),
                        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
                elif len(start) == 4:
                    matrix = cv2.getPerspectiveTransform(start, end)
                    moved = cv2.warpPerspective(premultiply(donor), matrix, (width, height),
                        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
                else:
                    raise ValueError('A patch requires three or four source/target points')
                moved = unpremultiply(moved)
                mask = polygon((width, height), operation['polygon'], operation.get('feather', 2))
                if operation.get('keep_silhouette', True):
                    mask *= source[..., 3] if operation.get('restore_alpha') else image[..., 3]
                mask *= moved[..., 3]
                # A part repaint changes RGB while retaining the approved alpha.
                image[..., :3] = image[..., :3] * (1 - mask[..., None]) + moved[..., :3] * mask[..., None]
                if operation.get('restore_alpha'):
                    image[..., 3] = np.maximum(image[..., 3], mask * source[..., 3])
            elif kind == 'slim':
                left, top, right, bottom = operation['box']
                yy, xx = np.mgrid[top:bottom, left:right].astype(np.float32)
                amount = operation['pixels'] * np.interp(yy, operation['y_knots'], operation['weights'])
                pivot = operation['pivot_x']
                # Move the outer contour inward, tapering to the unchanged hip/knee.
                source_x = pivot - (pivot - xx) * ((pivot - left) / (pivot - left - amount))
                premul = cv2.remap(premultiply(image), source_x.astype(np.float32), yy, cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_CONSTANT)
                image[top:bottom, left:right] = unpremultiply(premul)
            else:
                raise ValueError('Unknown operation: ' + kind)
        image = np.clip(image, 0, 1)
        # Remove detached sub-pixel cut remnants, not connected body artwork.
        count, labels, stats, _ = cv2.connectedComponentsWithStats(np.uint8(image[..., 3] > .08), 8)
        for component in range(1, count):
            if stats[component, cv2.CC_STAT_AREA] < 100:
                fringe = cv2.dilate(np.uint8(labels == component), np.ones((3, 3), np.uint8))
                image[..., 3][fringe != 0] = 0
        removed = (source[..., 3] > .6) & (image[..., 3] < .2)
        if removed.any():
            distance = cv2.distanceTransform(np.uint8(~removed), cv2.DIST_L2, 3)
            shade = np.clip((2.8 - distance) / 2.8, 0, 1) * .9
            # New cut contours need the same narrow ink edge as the source art.
            image[..., :3] *= 1 - shade[..., None]
        target = args.out / name
        pixels = np.uint8(np.rint(image * 255))
        pixels[pixels[..., 3] == 0, :3] = 0
        Image.fromarray(pixels).save(target)
        change = ((np.max(np.abs(image - source), axis=2) > 1/255)
                  & (np.maximum(image[..., 3], source[..., 3]) > .05))
        Image.fromarray(np.uint8(change) * 255).save(args.out / (Path(name).stem + '-changed.png'))
        records.append({'image': name, 'operations': [o['kind'] for o in operations],
            'changed_pixels': int(change.sum()),
            'source_sha256': hashlib.sha256((args.source / name).read_bytes()).hexdigest(),
            'output_sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
    (args.out / 'refinement.json').write_text(json.dumps({
        'status': 'review', 'method': 'local masked artwork reuse and part transforms',
        'recipe': str(args.recipe.resolve()), 'uploaded': False, 'diffusion_calls': 0,
        'recipe_sha256': hashlib.sha256(args.recipe.read_bytes()).hexdigest(),
        'game_pack_installed': False, 'full_torso_locked': False, 'images': records}, indent=2), encoding='utf-8')
    print('Refined six frames locally:', args.out.resolve(), flush=True)


if __name__ == '__main__':
    main()
