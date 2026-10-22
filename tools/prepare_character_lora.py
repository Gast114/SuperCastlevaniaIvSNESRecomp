"""Prepare existing RGBA character art for a small LoRA trial, entirely locally.

No training, network requests, purchases, upscaling, or game-pack installation.
Writes a new output directory and a ZIP containing only training PNG/TXT pairs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from PIL import Image, ImageDraw


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    recipe = json.loads(args.recipe.read_text(encoding='utf-8'))
    if args.out.exists():
        raise FileExistsError('Use a new output folder: ' + str(args.out))
    size = recipe['canvas']
    if size != [512, 512]:
        raise ValueError('This pilot uses an unscaled 512x512 training canvas')
    records = []
    seen = set()
    for row in recipe['images']:
        path = Path(row['source'])
        with Image.open(path) as opened:
            image = opened.convert('RGBA')
        pixel_hash = sha(image.tobytes())
        if pixel_hash in seen:
            raise ValueError('Duplicate image, including possible holdout leakage: ' + str(path))
        seen.add(pixel_hash)
        alpha = image.getchannel('A')
        box = alpha.getbbox()
        if box is None or alpha.getextrema()[0] != 0:
            raise ValueError('Expected a visible character with a transparent background: ' + str(path))
        width, height = image.size
        if width > size[0] - 32 or height > size[1] - 32:
            raise ValueError('Source does not fit without rescaling: ' + str(path))
        # Align each training example by its opaque foot/bottom; this is dataset
        # padding only, NOT an installation offset for a jumping game sprite.
        offset = ((size[0] - box[2] + box[0]) // 2 - box[0], 488 - box[3])
        rgba = Image.new('RGBA', tuple(size), (0, 0, 0, 0))
        rgba.alpha_composite(image, offset)
        matte = Image.new('RGBA', tuple(size), tuple(recipe['background']) + (255,))
        rgb = Image.alpha_composite(matte, rgba).convert('RGB')
        caption = recipe['trigger_word'] + ', ' + row['caption']
        if row['split'] not in ('train', 'holdout'):
            raise ValueError('Invalid split')
        records.append((row, path, image, rgba, rgb, caption, offset, pixel_hash))
    if sum(r[0]['split'] == 'train' for r in records) < 4:
        raise ValueError('At least four training examples required for this pilot')
    args.out.mkdir(parents=True)
    for folder in ('train', 'holdout', 'originals', 'alpha'):
        (args.out / folder).mkdir()
    report = {'status': 'prepared_not_trained', 'uploaded': False,
              'recipe': str(args.recipe.resolve()), 'canvas': size,
              'background': recipe['background'], 'trigger_word': recipe['trigger_word'],
              'preparation_rescaled_images': False, 'images': []}
    sheet = Image.new('RGB', (960, 1620), '#ddd9d0')
    draw = ImageDraw.Draw(sheet)
    with zipfile.ZipFile(args.out / 'Simon-LoRA-Training.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for i, (row, path, image, rgba, rgb, caption, offset, pixel_hash) in enumerate(records):
            stem = row['name']
            if Path(stem).name != stem or not stem.isascii():
                raise ValueError('Use simple ASCII output names')
            split = row['split']
            png = args.out / split / (stem + '.png')
            txt = png.with_suffix('.txt')
            rgb.save(png)
            txt.write_text(caption + '\n', encoding='utf-8')
            rgba.getchannel('A').save(args.out / 'alpha' / (stem + '.png'))
            shutil.copy2(path, args.out / 'originals' / (stem + '.png'))
            if split == 'train':
                archive.write(png, png.name)
                archive.write(txt, txt.name)
            x, y = (i % 3) * 320, (i // 3) * 540
            sheet.paste(image, (x + (320 - image.width) // 2, y + 20), image)
            color = '#a92525' if split == 'holdout' else '#246438'
            draw.text((x + 12, y + 490), stem + ' - ' + split, fill=color)
            report['images'].append({'name': stem, 'split': split, 'source': str(path.resolve()),
                'source_sha256': sha(path.read_bytes()), 'rgba_sha256': pixel_hash,
                'source_size': list(image.size), 'padding_offset': list(offset),
                'prepared_sha256': sha(png.read_bytes()), 'caption': caption})
    sheet.save(args.out / 'Bildauswahl.jpg', quality=93)
    report['train_count'] = sum(r[0]['split'] == 'train' for r in records)
    report['holdout_count'] = len(records) - report['train_count']
    report['archive_sha256'] = sha((args.out / 'Simon-LoRA-Training.zip').read_bytes())
    (args.out / 'dataset.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'train': report['train_count'],
                      'holdout': report['holdout_count'], 'out': str(args.out.resolve())}))


if __name__ == '__main__':
    main()
