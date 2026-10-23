"""Prepare an enemy art folder from automatically collected native references.

The game assigns complete poses. Artists only edit the named PNGs in artwork/;
tile addresses, OAM slots and mirroring never need manual mapping.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import html
from urllib.parse import quote


def pixel_hash(image):
    image = image.convert('RGBA')
    return hashlib.sha256(str(image.size).encode('ascii') + image.tobytes()).hexdigest()


def prepare(source, destination, work_size=0):
    from PIL import Image
    manifest = json.loads((source / 'enemies.json').read_text(encoding='utf-8'))
    if manifest.get('version') != 1 or not manifest.get('frames'):
        raise ValueError('No captured enemy references yet. Play until a pilot enemy appears first.')
    if destination.exists():
        raise ValueError('Destination already exists; choose a new folder to preserve existing artwork.')
    if work_size and not 1 <= work_size <= 4096:
        raise ValueError('Working canvas must be between 1 and 4096 pixels')
    # Validate everything before creating a user-facing partial pack.
    for frame in manifest['frames']:
        reference = frame['reference']
        if Path(reference).name != reference or not (source / reference).is_file():
            raise ValueError(f'Missing local reference PNG: {reference}')
    destination.mkdir(parents=True)
    (destination / 'references').mkdir()
    (destination / 'artwork').mkdir()
    frames = []
    artwork_by_pixels = {}
    numbers = {}
    baselines = {}
    cards = []
    for frame in manifest['frames']:
        original = source / frame['reference']
        family = 'Skelett' if frame['actor_type'] in (17,18) else f'Gegner_{frame["actor_type"]:04x}'
        with Image.open(original) as image:
            identity = (family, image.size, hashlib.sha256(image.convert('RGBA').tobytes()).digest())
        name = artwork_by_pixels.get(identity)
        if name is None:
            numbers[family] = numbers.get(family, 0) + 1
            name = f'{family}_Schritt_{numbers[family]:02d}.png'
            artwork_by_pixels[identity] = name
            shutil.copy2(original, destination / 'references' / name)
            if work_size:
                with Image.open(original) as image:
                    size = tuple(max(1, round(n * work_size / max(image.size))) for n in image.size)
                    working = image.convert('RGBA').resize(size, Image.Resampling.NEAREST)
                    working.save(destination / 'artwork' / name)
                    baselines[name] = pixel_hash(working)
            else:
                shutil.copy2(original, destination / 'artwork' / name)
                size = identity[1]
            safe_name = html.escape(name)
            cards.append(f'<article><img src="artwork/{quote(name)}" alt="{safe_name}">'
                         f'<h2>{safe_name}</h2><p>{size[0]} × {size[1]} Pixel · transparenter Hintergrund</p>'
                         f'<a href="artwork/{quote(name)}">PNG zum Überarbeiten</a> · '
                         f'<a href="references/{quote(name)}">Original zum Abgleichen</a></article>')
        mapping = dict(frame)
        # Images are copied into the pack root when assembling, so the runtime
        # only accepts safe local filenames and no arbitrary filesystem paths.
        mapping['image'] = name
        mapping['reference'] = name
        frames.append(mapping)
    (destination / 'project.json').write_text(json.dumps({
        'version': 1, 'name': destination.name, 'frames': frames, 'work_templates': baselines,
    }, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (destination / 'HIER_STARTEN.txt').write_text(
        'GEGNER IN HD\n\n'
        '1. Originale liegen in references/. Bitte diese unverändert lassen.\n'
        '2. Nur PNGs in artwork/ überarbeiten und unter demselben Namen speichern.\n'
        '   Die ganze transparente Bildfläche behalten; nicht auf das Motiv beschneiden.\n'
        + (f'   Arbeitsvorlagen sind bereits auf {work_size} Pixel vergrößert.\n' if work_size else '') +
        '   Beliebige Auflösung ist erlaubt, auch 4,031x. Keine exakt 10x nötig.\n'
        '   Position und Proportionen über dem Original beibehalten.\n'
        '3. Mir diesen ganzen Ordner oder die fertigen PNGs zurückgeben.\n'
        '   Alternativ im HD-Import den Arbeitsordner wählen und Paket erstellen.\n'
        '   Spiegelung, Pose und Position übernimmt das Spiel automatisch.\n'
        '   Nicht überarbeitete PNGs bleiben original.\n', encoding='utf-8')
    (destination / 'VORLAGEN.html').write_text(
        '<!doctype html><html lang="de"><meta charset="utf-8"><title>Gegner-PNGs zum Redesignen</title>'
        '<style>body{font:18px system-ui;background:#151b22;color:#eef1f5;max-width:1120px;margin:36px auto;padding:0 24px}'
        'h1{font-size:32px}main{display:flex;gap:24px;flex-wrap:wrap}article{background:#242d36;padding:24px;border-radius:12px}'
        'img{width:360px;height:360px;object-fit:contain;image-rendering:pixelated;background:repeating-conic-gradient(#404954 0% 25%,#353f49 0% 50%) 0/24px 24px}'
        'a{color:#a6d9ff}p{line-height:1.5}h2{font-size:18px}</style>'
        '<h1>Deine Gegner-PNGs zum Überarbeiten</h1>'
        '<p>Nur die PNGs in <strong>artwork</strong> bearbeiten. Dateinamen und komplette transparente Bildfläche behalten. '
        'Originale und Zuordnung liegen separat bereit. Beide Blickrichtungen und Spielebenen sind automatisch zugeordnet.</p>'
        f'<p>{len(artwork_by_pixels)} verschiedene PNGs für {len(frames)} aufgenommene Spielzustände. '
        'Diese Sammlung enthält die bereits zugeordneten Posen; sie ist kein vollständiger Gegnerkatalog.</p>'
        '<main>' + ''.join(cards) + '</main></html>', encoding='utf-8')
    return len(frames)


def pack(project, destination, all_references=False):
    from PIL import Image
    data = json.loads((project / 'project.json').read_text(encoding='utf-8'))
    if data.get('version') != 1 or not isinstance(data.get('frames'), list):
        raise ValueError('Unsupported enemy project')
    if destination.exists():
        raise ValueError('Destination already exists; choose a new pack name.')
    pending = []
    ids = set()
    for frame in data['frames']:
        name = frame['image']
        if Path(name).name != name or not name.lower().endswith('.png'):
            raise ValueError('Only local PNG filenames are accepted')
        if frame['id'] in ids:
            raise ValueError('Duplicate enemy pose ID')
        ids.add(frame['id'])
        source = project / 'artwork' / name
        reference = project / 'references' / frame['reference']
        with Image.open(source) as image:
            image.load()
            if max(image.size) > 4096 or min(image.size) < 1:
                raise ValueError(f'PNG size outside 1..4096 pixels: {name}')
            if not all_references:
                if data.get('work_templates', {}).get(name) == pixel_hash(image):
                    continue
                with Image.open(reference) as original:
                    if image.convert('RGBA').size == original.size and image.convert('RGBA').tobytes() == original.convert('RGBA').tobytes():
                        continue
        # Runtime keeps the PNG's exact original resolution, dimensions and
        # transparent canvas. display_size maps the full reference canvas.
        pending.append((source, {k: v for k, v in frame.items() if k != 'reference'}))
    if not pending:
        raise ValueError('No changed artwork. Edit artwork/ PNGs first; --include-references is for renderer diagnostics.')
    destination.mkdir(parents=True)
    for source, mapping in pending:
        shutil.copy2(source, destination / mapping['image'])
    result = {'version': 1, 'name': data.get('name', destination.name), 'frames': [m for _, m in pending]}
    (destination / 'enemies.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return len(pending)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('prepare', help='Create an art project; never overwrite an existing folder')
    p.add_argument('references', type=Path)
    p.add_argument('project', type=Path)
    p.add_argument('--work-size', type=int, default=0, help='Pre-enlarge working PNG canvases, e.g. 387 for a 96px reference')
    p = commands.add_parser('pack', help='Copy changed PNGs at their exact export resolution into a new pack')
    p.add_argument('project', type=Path)
    p.add_argument('destination', type=Path)
    p.add_argument('--include-references', action='store_true', help='Explicit diagnostic: replace native frames with native reference PNGs')
    args = parser.parse_args()
    count = prepare(args.references, args.project, args.work_size) if args.command == 'prepare' else pack(args.project, args.destination, args.include_references)
    print(f'{count} poses: {args.project if args.command == "prepare" else args.destination}')


if __name__ == '__main__':
    main()
