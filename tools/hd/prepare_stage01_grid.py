"""Create registered, exact 4x artist exports without replacing old PNGs/PSDs.

Known source panel boundaries map to explicit native boundaries. Resampling uses
the complete source image as filter context, not independently cropped tiles.
This restores canvas/registration; it cannot infer incorrectly painted geometry.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
RECIPE = ROOT / 'assets/hd/stage01_grid.recipe.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rgba(path, size):
    with Image.open(path) as image:
        if image.mode != 'RGBA' or list(image.size) != size:
            raise ValueError(f'{path}: expected RGBA {size}, got {image.mode} {image.size}')
        return image.copy()


def register_plane(image, spec, recipe):
    """Each authored panel and both margins have exact registered endpoints."""
    scale = 4
    left = recipe['source_margin']
    boundaries = [0, left]
    for width in spec['source_panel_widths']:
        boundaries.append(boundaries[-1] + width)
    boundaries.append(image.width)
    native_widths = [recipe['margin_native'], *spec['native_panel_widths'], recipe['margin_native']]
    assert len(boundaries) == len(native_widths) + 1
    height = recipe['native_height'] * scale
    result = Image.new('RGBA', (sum(native_widths) * scale, height))
    x = 0
    panels = []
    for index, (a, b, width) in enumerate(zip(boundaries, boundaries[1:], native_widths)):
        if b <= a:
            raise ValueError('Nonpositive source panel')
        size = (width * scale, height)
        # Pillow's RGBA resize filters in premultiplied alpha. The box retains
        # neighbouring source pixels as filter context across panel boundaries.
        part = image.resize(size, Image.Resampling.LANCZOS,
                            box=(a, 0, b, recipe['source_height']))
        result.paste(part, (x, 0))
        panels.append(dict(index=index, source_box=[a, 0, b, recipe['source_height']],
                           output_box=[x, 0, x + size[0], height]))
        x += size[0]
    return result, panels


def prepare(source, output, recipe_path=RECIPE):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output:
        raise ValueError('Use a separate output folder (normally Stage 01/Exporte-4x)')
    if output.exists():
        raise FileExistsError('Use a new output directory; existing exports are never overwritten')
    recipe = json.loads(Path(recipe_path).read_text(encoding='utf-8'))
    sources = []
    planes, motifs = {}, {}
    # Load and validate every input before creating the output folder.
    def load(relative, size):
        path = source / relative
        image = read_rgba(path, size)
        sources.append(dict(source=str(path), sha256=sha(path), backup_relative_path=relative))
        return image
    for stage, spec in recipe['stages'].items():
        planes[stage] = load(f'{stage}/HD/Spielebene.png', spec['source_size'])
    for name, spec in recipe['motifs'].items():
        motifs[name] = load(f'HD/Gemeinsame-Teile/{name}', spec['source_size'])
    output.mkdir(parents=True)
    manifest = dict(version=1, kind='registered-stage01-grid', export_scale=4,
                    recipe_sha256=sha(recipe_path), sources=sources, planes={}, motifs={})
    for stage, image in planes.items():
        result, panels = register_plane(image, recipe['stages'][stage], recipe)
        relative = f'{stage}/HD/Spielebene.png'
        path = output / relative
        path.parent.mkdir(parents=True)
        result.save(path)
        extra = np.array(image)[recipe['source_height']:, :, 3]
        manifest['planes'][stage] = dict(image=relative, source_scale=4,
            native_size=[sum(recipe['stages'][stage]['native_panel_widths']) + 2 * recipe['margin_native'], recipe['native_height']],
            origin_native=[-recipe['margin_native'], 0], panels=panels,
            excluded_bottom_rows=image.height-recipe['source_height'], excluded_alpha_pixels=int((extra > 0).sum()),
            initial_sha256=sha(path))
    for name, image in motifs.items():
        spec = recipe['motifs'][name]
        method = 'resampled-complete-image'
        if spec.get('mirror_from') and np.array_equal(np.array(image), np.array(motifs[spec['mirror_from']])):
            image = ImageOps.mirror(motifs[spec['mirror_from']])
            method = 'mirrored-identical-pair-authorized-2026-11-04'
        size = tuple(n * 4 for n in spec['native_size'])
        result = image.resize(size, Image.Resampling.LANCZOS)
        relative = f'HD/Gemeinsame-Teile/{name}'
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        result.save(path)
        manifest['motifs'][name] = dict(image=relative, native_size=spec['native_size'],
            source_scale=4, anchor_native=[0, 0], method=method, initial_sha256=sha(path))
    assert all(sha(item['source']) == item['sha256'] for item in sources), 'Source modified'
    (output / 'raster.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    (output / 'LIES_MICH.txt').write_text(
        'EXAKTE 4x-EXPORTE — A03/A04/A05\n\n'
        'Die bisherigen PNGs und PSDs wurden nicht veraendert.\n'
        'Spielebenen: 224 Originalpixel = 896 Bildpixel hoch; 43 Originalpixel\n'
        '= 172 Bildpixel Rand pro Seite, schon enthalten. Ursprung x=-43, y=0.\n'
        'A03: 5464x896; A04: 4440x896; A05: 3416x896.\n'
        '16x16-Stein/Anschluss: 64x64; 8x8-Stufe: 32x32, einschliesslich Alpha.\n'
        'Die identischen Anschlussdateien wurden fuer Links gespiegelt.\n'
        'A03: eine untere Ueberstandszeile ausserhalb der 903px-Originalhoehe\n'
        'ist im Export entfallen (175 sichtbare Pixel, nur am Rand).\n\n'
        'Hier kannst du weiterarbeiten. PNGs beim Import nicht erneut skalieren.\n'
        'raster.json enthaelt feste Spielmasse und Urspruenge. Die initialen\n'
        'Pruefsummen sind Herkunftsbelege; spaetere PNG-Bearbeitung ist erlaubt.\n'
        'Alte PSDs bleiben in 4,03125x. Ein neuer PSD-Export muss erneut\n'
        'registriert werden; alte/ganzzahlige Raster nicht ungeprueft mischen.\n\n'
        '8x spaeter: 16x16 -> 128x128; 8x8 -> 64x64. Gleiche Spielmasse/Anker.\n'
        'Der Importer akzeptiert in raster.json source_scale 8 fuer Einzelmotive\n'
        'und rechnet sie fuer den aktuellen 4x-Pack einmal herunter. Echte\n'
        'gemischte 8x-Detailausgabe im Landschaftsrenderer ist noch nicht umgesetzt.\n'
        'Nicht bloss auf 8x vergroessern: das erzeugt keine neuen Details.\n\n'
        'Die Umrechnung korrigiert Abmessungen und bekannte Anschluesse, keine\n'
        'innerhalb eines Motivs falsch gezeichneten Steine oder Details.\n', encoding='utf-8')
    print(json.dumps(dict(output=str(output), source_files_unchanged=True,
                          sizes={s: [v['native_size'][0]*4, v['native_size'][1]*4] for s,v in manifest['planes'].items()})))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source, args.out)
