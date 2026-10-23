"""Install one newly built character/enemy pack with selection backup and rollback.

Called only by the import window's installation button. Importing or reviewing a
pack never changes the selected character. Source PNGs remain byte-for-byte.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import uuid


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def install_pack(pack, targets, backup, kind='character'):
    if kind not in ('character', 'enemy'):
        raise ValueError('Package kind must be character or enemy')
    collection = 'characters' if kind == 'character' else 'enemy_packs'
    manifest_name = 'character.json' if kind == 'character' else 'enemies.json'
    pack, backup = Path(pack).resolve(), Path(backup).resolve()
    targets = [Path(target).resolve() for target in targets]
    if not re.fullmatch(r'[A-Za-z0-9_-]+', pack.name):
        raise ValueError('Package folder name may contain only letters, numbers, underscores and hyphens')
    if not targets or len(set(targets)) != len(targets):
        raise ValueError('Choose distinct game folders')
    if not pack.is_dir() or not (pack/manifest_name).is_file() or (kind == 'character' and not (pack/'body.png').is_file()):
        raise ValueError('A completed package is required')
    manifest = json.loads((pack/manifest_name).read_text(encoding='utf-8-sig'))
    if manifest.get('version') != 1 or not manifest.get('frames'):
        raise ValueError('Invalid or empty character package')
    if backup.exists():
        raise FileExistsError('Choose a new backup folder')
    if pack in backup.parents or any(target in backup.parents for target in targets):
        raise ValueError('Backup must be outside the source package and game folders')
    files = {p.relative_to(pack).as_posix(): sha(p) for p in pack.rglob('*') if p.is_file()}
    for frame in manifest['frames']:
        if 'hd' in frame or kind == 'enemy':
            image = frame['image'] if kind == 'enemy' else frame['hd']['image']
            if Path(image).name != image or image not in files:
                raise ValueError('Package references a missing or nonlocal PNG')
    destinations = []
    # Preflight every destination before creating a backup or writing either game.
    for target in targets:
        characters = target/collection
        destination = characters/pack.name
        if characters.resolve() != characters:
            raise ValueError('Package folder must stay inside the chosen game folder')
        if not target.is_dir() or (characters.exists() and not characters.is_dir()):
            raise FileNotFoundError(f'Game package folder invalid: {characters}')
        if destination.exists():
            raise FileExistsError(f'Package already exists: {destination}')
        if pack == destination or target == pack or pack in target.parents or target in pack.parents:
            raise ValueError('Source package and game folders must be separate')
        selected = characters/'selected.txt'
        if selected.exists() and not selected.is_file():
            raise ValueError(f'Invalid character selection file: {selected}')
        destinations.append({'characters': characters, 'destination': destination, 'selected': selected,
                             'before': selected.read_bytes() if selected.exists() else None,
                             'staging': characters/('.'+pack.name+'.install-'+uuid.uuid4().hex),
                             'collection_existed': characters.exists(),
                             'published': False, 'selection_changed': False})
    backup.mkdir(parents=True)
    (backup/'before.json').write_text(json.dumps({'pack': str(pack), 'targets': [
        {'selection_file': str(item['selected']), 'backup_file': f'{index:02d}-selected.txt',
         'previous_selection_existed': item['before'] is not None}
        for index, item in enumerate(destinations)]}, ensure_ascii=False, indent=2), encoding='utf-8')
    for index, item in enumerate(destinations):
        if item['before'] is not None:
            (backup/f'{index:02d}-selected.txt').write_bytes(item['before'])
    report = {'pack': str(pack), 'kind': kind, 'package_files_sha256': files, 'targets': []}
    try:
        for item in destinations:
            item['characters'].mkdir(exist_ok=True)
            shutil.copytree(pack, item['staging'])
            if any(sha(item['staging']/name) != checksum for name, checksum in files.items()):
                raise IOError('Package changed while copying; installation cancelled')
        # Verify the artist's source pack too before publishing either copy.
        if any(sha(pack/name) != checksum for name, checksum in files.items()):
            raise IOError('Source package changed during installation')
        for item in destinations:
            item['staging'].rename(item['destination'])
            item['published'] = True
        for item in destinations:
            pending = item['characters']/('.selected-'+uuid.uuid4().hex+'.tmp')
            try:
                pending.write_text(pack.name+'\n', encoding='utf-8')
                pending.replace(item['selected'])
                item['selection_changed'] = True
            finally:
                pending.unlink(missing_ok=True)
        for item in destinations:
            report['targets'].append({'characters': str(item['characters']),
                                      'destination': str(item['destination']),
                                      'previous_selection_existed': item['before'] is not None,
                                      'selected_pack': pack.name})
        (backup/'install.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    except BaseException:
        for item in reversed(destinations):
            if item['selection_changed']:
                if item['before'] is None:
                    item['selected'].unlink(missing_ok=True)
                else:
                    item['selected'].write_bytes(item['before'])
            if item['published']:
                if item['destination'].resolve().parent != item['characters']:
                    raise RuntimeError('Rollback path escaped the package folder')
                shutil.rmtree(item['destination'])
            if item['staging'].exists():
                if item['staging'].resolve().parent != item['characters']:
                    raise RuntimeError('Staging path escaped the package folder')
                shutil.rmtree(item['staging'])
            if not item['collection_existed'] and item['characters'].exists():
                item['characters'].rmdir()
        raise
    return report


def install_character_pack(pack, targets, backup):
    return install_pack(pack, targets, backup, kind='character')
