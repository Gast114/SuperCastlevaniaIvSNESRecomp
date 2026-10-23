"""Prepare an enemy art folder from automatically collected native references.

The game assigns complete poses. Artists only edit the named PNGs in artwork/;
tile addresses, OAM slots and mirroring never need manual mapping.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def prepare(source, destination):
    from PIL import Image
    manifest = json.loads((source / 'enemies.json').read_text(encoding='utf-8'))
    if manifest.get('version') != 1 or not manifest.get('frames'):
        raise ValueError('No captured enemy references yet. Play until a pilot enemy appears first.')
    if destination.exists():
        raise ValueError('Destination already exists; choose a new folder to preserve existing artwork.')
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
            shutil.copy2(original, destination / 'artwork' / name)
        mapping = dict(frame)
        # Images are copied into the pack root when assembling, so the runtime
        # only accepts safe local filenames and no arbitrary filesystem paths.
        mapping['image'] = name
        mapping['reference'] = name
        frames.append(mapping)
    (destination / 'project.json').write_text(json.dumps({
        'version': 1, 'name': destination.name, 'frames': frames,
    }, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (destination / 'HIER_STARTEN.txt').write_text(
        'GEGNER IN HD\n\n'
        '1. Originale liegen in references/. Bitte diese unverändert lassen.\n'
        '2. PNGs in artwork/ überarbeiten. Die ganze transparente Bildfläche behalten.\n'
        '   Beliebige Auflösung ist erlaubt, auch 4,031x. Keine exakt 10x nötig.\n'
        '   Position und Proportionen über dem Original beibehalten.\n'
        '3. Den Ordner mit enemy_hd.py pack zusammenstellen.\n'
        '   Spiegelung, Pose und Position übernimmt das Spiel automatisch.\n'
        '   Nicht überarbeitete PNGs bleiben original.\n', encoding='utf-8')
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
    p = commands.add_parser('pack', help='Copy changed PNGs at their exact export resolution into a new pack')
    p.add_argument('project', type=Path)
    p.add_argument('destination', type=Path)
    p.add_argument('--include-references', action='store_true', help='Explicit diagnostic: replace native frames with native reference PNGs')
    args = parser.parse_args()
    count = prepare(args.references, args.project) if args.command == 'prepare' else pack(args.project, args.destination, args.include_references)
    print(f'{count} poses: {args.project if args.command == "prepare" else args.destination}')


if __name__ == '__main__':
    main()
