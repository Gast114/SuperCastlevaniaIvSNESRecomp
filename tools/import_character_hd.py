"""Import complete PNG poses at any working resolution, preserving source bytes.

--native: matching filenames in separate reference/artwork folders.
--workspace: automatically mapped references exported from the captured template.
Legacy *_HD_10x_* pairs remain supported. Game profiles are never changed.
"""
import argparse
import copy
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import quote

import numpy as np
from PIL import Image

CELL, COLS, ROWS = 96, 8, 32


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def png(path):
    with Image.open(path) as source:
        if source.format != 'PNG':
            raise ValueError(f'{path}: PNG required')
        if source.width > 8192 or source.height > 8192 or source.width * source.height > 32*1024*1024:
            raise ValueError(f'{path}: maximum 32 megapixels / 8192 pixels per axis')
        return source.convert('RGBA')


def read_template(template):
    manifest = json.loads((template/'character.json').read_text(encoding='utf-8-sig'))
    if manifest.get('version') != 1 or manifest.get('cell_size') != CELL:
        raise ValueError('Unsupported captured character template')
    sheet = png(template/'body.png')
    if sheet.size != (CELL*COLS, CELL*ROWS):
        raise ValueError('Captured body.png must be 768 x 3072')
    if not manifest.get('frames'):
        raise ValueError('No poses captured yet; play with character workshop capture enabled first')
    return manifest, sheet


def make_workspace(template, output):
    """Export actually captured poses and retain their exact template identity."""
    template, output = Path(template).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError('Choose a new workspace folder')
    manifest, sheet = read_template(template)
    output.mkdir(parents=True)
    (output/'Original').mkdir()
    (output/'HD').mkdir()
    records = []
    for i, frame in enumerate(manifest['frames']):
        cell = frame['cell']
        tile = sheet.crop((cell%COLS*CELL, cell//COLS*CELL, cell%COLS*CELL+CELL, cell//COLS*CELL+CELL))
        box = tile.getbbox()
        if not box:
            continue
        safe_id = re.sub(r'[^A-Za-z0-9_-]', '_', frame['id'])
        name = f'{i+1:03d}_{safe_id}.png'
        reference = output/'Original'/name
        tile.crop(box).save(reference)
        records.append({'file': name, 'pose': frame['id'], 'native_sha256': sha(reference)})
    mapping = {'version': 1, 'template': str(template), 'poses': records}
    (output/'workspace.json').write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')
    write_workspace_index(output, mapping)
    (output/'BITTE_LESEN.txt').write_text(
        'Original enthält die aufgenommenen Spielposen.\n'
        'Das passende PNG in Photoshop öffnen, beliebig vergrößern und darüber gestalten.\n'
        'PNG mit gleichem Dateinamen in HD speichern. Transparente Ränder proportional erhalten.\n'
        '4,03125×, 10× oder andere Arbeitsauflösung sind erlaubt; keine DPI-Vorgabe.\n'
        'Nur fertige Bilder exportieren. Fehlende Posen bleiben im Spiel original.\n'
        'HD_Import_starten.cmd öffnen, diesen Arbeitsordner wählen und Paket erstellen.\n'
        'Original und workspace.json unverändert aufbewahren: Sie speichern die Zuordnung.\n', encoding='utf-8')
    return output


def write_workspace_index(output, mapping):
    """Visual selection avoids asking the artist to understand pose hashes."""
    cards = []
    for number, record in enumerate(mapping['poses'], 1):
        reference = Path(output)/'Original'/record['file']
        with Image.open(reference) as image:
            width, height = image.size
        url = 'Original/'+quote(record['file'])
        cards.append(f'<article><a href="{url}"><img src="{url}" alt="Pose {number}"></a>'
                     f'<strong>Pose {number:03d}</strong><p>{width} × {height} native Pixel<br>'
                     f'4,03125×: ca. {round(width*4.03125)} × {round(height*4.03125)} PNG-Pixel</p>'
                     f'<a href="{url}" download>Original-PNG öffnen / speichern</a></article>')
    (Path(output)/'VORLAGEN.html').write_text('<!doctype html><meta charset="utf-8"><title>Simon-Vorlagen</title>'
        '<style>body{font:16px system-ui;background:#20232a;color:#eee;padding:2rem}a{color:#9cdaff}'
        'main{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}'
        'article{padding:16px;background:#30343d;border-radius:8px}img{display:block;width:100%;height:180px;'
        'object-fit:contain;image-rendering:pixelated;margin-bottom:12px}</style>'
        '<h1>Aufgenommene Simon-Posen</h1><p>Ein Original-PNG in Photoshop öffnen, proportional vergrößern '
        'und darüber gestalten. Mit gleichem Namen in HD speichern. Nur fertige Bilder liefern.</p>'
        '<p>Gleich aussehende Posen können verschiedene Spielzustände sein. Die gespeicherte Zuordnung '
        'bleibt für jeden Eintrag erhalten.</p><main>'+''.join(cards)+'</main>', encoding='utf-8')


def discover(source, native=None, workspace=None):
    known = {}
    if workspace:
        workspace = Path(workspace)
        data = json.loads((workspace/'workspace.json').read_text(encoding='utf-8-sig'))
        if data.get('version') != 1:
            raise ValueError('Unsupported workspace format')
        known = {p['file'].casefold(): p for p in data['poses']}
        source, native = workspace/'HD', workspace/'Original'
    source = Path(source)
    pairs = []
    if native:
        references = {p.name.casefold(): p for p in Path(native).iterdir() if p.suffix.lower() == '.png'}
        for image in sorted(source.iterdir()):
            if image.suffix.lower() != '.png':
                continue
            reference = references.get(image.name.casefold())
            if not reference:
                raise ValueError(f'{image.name}: no matching PNG in Original/reference folder')
            record = known.get(image.name.casefold())
            if workspace and not record:
                raise ValueError(f'{image.name}: no captured pose mapping in workspace.json')
            if record and sha(reference) != record['native_sha256']:
                raise ValueError(f'{reference.name}: original reference was modified; restore it before importing')
            pairs.append((reference, image, record['pose'] if record else None))
    else:
        for image in sorted(source.iterdir()):
            if image.suffix.lower() != '.png':
                continue
            match = re.match(r'(.+)_HD(?:_[0-9.,]+x)?(?:_.*)?$', image.stem, re.IGNORECASE)
            if match:
                reference = source/(match.group(1)+'.png')
                if not reference.is_file():
                    raise ValueError(f'{image.name}: native reference {reference.name} missing')
                pairs.append((reference, image, None))
    if not pairs:
        raise ValueError('No artwork found. Put finished PNGs in HD with the same names as their Original references.')
    return pairs


def import_poses(template, source, output, native=None, workspace=None, name='Simon HD import'):
    template, output = Path(template).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError('Choose a new output folder; existing packs are never overwritten')
    manifest, sheet = read_template(template)
    result = copy.deepcopy(manifest)
    result.update(name=name, frames=[])
    preview = Image.new('RGBA', sheet.size)
    receipt = []
    for reference, source_image, mapped_id in discover(source, native, workspace):
        sd, hd = png(reference), png(source_image)
        if reference.resolve() == source_image.resolve():
            raise ValueError('Original and HD artwork must be separate files')
        if min(sd.size) < 1 or max(sd.size) > CELL:
            raise ValueError(f'{reference}: native reference must fit a 96 x 96 cell')
        native_box = sd.getbbox()
        if not native_box or not hd.getbbox():
            raise ValueError(f'{source_image.name}: reference/artwork is empty')
        # Permit integer rounding during export, never silently stretch artwork
        # with independently cropped or otherwise changed canvas proportions.
        if abs(hd.width*sd.height-hd.height*sd.width) > max(sd.size):
            raise ValueError(f'{source_image.name}: aspect ratio differs from reference; retain proportional canvas bounds')
        content = sd.crop(native_box)
        mask = np.array(content.getchannel('A')) > 0
        choices = []
        for candidate in manifest['frames']:
            if mapped_id and candidate['id'] != mapped_id:
                continue
            cell = candidate['cell']
            tile = sheet.crop((cell%COLS*CELL, cell//COLS*CELL, cell%COLS*CELL+CELL, cell//COLS*CELL+CELL))
            box = tile.getbbox()
            if box and (box[2]-box[0], box[3]-box[1]) == content.size:
                difference = int(np.sum(mask != (np.array(tile.crop(box).getchannel('A')) > 0)))
                choices.append((difference, candidate['id'], candidate, box, tile))
        choices.sort(key=lambda c: (c[0], c[1]))
        if not choices or choices[0][0] > mask.size*.01:
            raise ValueError(f'{reference.name}: no sufficiently close captured native pose')
        if len(choices) > 1 and choices[1][0]-choices[0][0] < mask.size*.02:
            raise ValueError(f'{reference.name}: ambiguous native poses; use an exported workspace with exact captured identities')
        difference, _, frame, box, tile = choices[0]
        frame = copy.deepcopy(frame)
        frame.update(cell=len(result['frames']), label=reference.stem)
        offset = [box[0]-native_box[0], box[1]-native_box[1]]
        if min(offset) < 0 or offset[0]+sd.width > CELL or offset[1]+sd.height > CELL:
            raise ValueError(f'{reference.name}: transparent reference padding exceeds captured native cell')
        frame['hd'] = {'image': source_image.name, 'scale': 10, 'offset': offset, 'display_size': list(sd.size)}
        result['frames'].append(frame)
        cell = frame['cell']
        preview.paste(tile, (cell%COLS*CELL, cell//COLS*CELL))
        receipt.append({'native': str(reference.resolve()), 'image': str(source_image.resolve()),
                        'native_sha256': sha(reference), 'sha256': sha(source_image), 'pose': frame['id'],
                        'alpha_mismatches': difference, 'native_pixels': mask.size, 'offset': offset,
                        'source_size': list(hd.size), 'display_size': list(sd.size),
                        'working_scale': [hd.width/sd.width, hd.height/sd.height]})
    if len({f['id'] for f in result['frames']}) != len(result['frames']):
        raise ValueError('Two artwork PNGs map to the same captured pose; import only one version')
    reserved = {'body.png', 'character.json', 'import.json', 'preview.html'}
    if any(Path(r['image']).name.casefold() in reserved for r in receipt):
        raise ValueError('Artwork filename conflicts with package metadata; rename it and its reference')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Validate everything before publishing a usable output folder.
    with tempfile.TemporaryDirectory(prefix='.hd-import-', dir=output.parent) as temporary:
        staging = Path(temporary)/'pack'
        staging.mkdir()
        rows = []
        for record in receipt:
            target = staging/Path(record['image']).name
            shutil.copy2(record['image'], target)
            if sha(target) != record['sha256']:
                raise IOError('Artwork checksum changed while copying')
            escaped = html.escape(quote(target.name), quote=True)
            rows.append(f'<tr><td>{html.escape(record["pose"])}</td><td><img src="{escaped}" alt="HD"></td>'
                        f'<td>{record["source_size"]} → native {record["display_size"]}<br>Offset {record["offset"]}</td></tr>')
        preview.save(staging/'body.png')
        (staging/'character.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
        (staging/'import.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
        (staging/'preview.html').write_text('<!doctype html><meta charset="utf-8"><title>HD-Importprüfung</title>'
            '<style>body{font:17px system-ui;background:#20232a;color:#eee;padding:2rem}table{border-collapse:collapse}'
            'td{border:1px solid #667;padding:1rem}img{max-width:320px;max-height:240px;'
            'background:repeating-conic-gradient(#555 0% 25%,#444 0% 50%) 0/16px 16px}</style>'
            '<h1>HD-Paket vorbereitet</h1><p>PNG-Dateien wurden unverändert kopiert. Arbeitsauflösung und Spielgröße sind getrennt.</p>'
            '<p>Die Vorschau zeigt die gelieferten Bilder; die tatsächliche Verankerung folgt dem aufgenommenen Original. '
            'Das Paket wurde noch nicht im Spiel ausgewählt.</p><table>'+''.join(rows)+'</table>', encoding='utf-8')
        staging.rename(output)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', type=Path, required=True)
    parser.add_argument('--source', type=Path, help='Artwork folder (legacy paired folder also supported)')
    parser.add_argument('--native', type=Path, help='Native reference folder with matching filenames')
    parser.add_argument('--workspace', type=Path, help='Prepared Original/HD workspace')
    parser.add_argument('--create-workspace', action='store_true')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--name', default='Simon HD import')
    args = parser.parse_args()
    try:
        if args.create_workspace:
            print(make_workspace(args.template, args.out))
        else:
            if not args.source and not args.workspace:
                parser.error('--source or --workspace is required')
            result = import_poses(args.template, args.source, args.out, args.native, args.workspace, args.name)
            print(json.dumps({'poses': len(result), 'output': str(args.out.resolve()), 'artwork_unchanged': True}, indent=2))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'Import stopped: {error}\n')


if __name__ == '__main__':
    main()
