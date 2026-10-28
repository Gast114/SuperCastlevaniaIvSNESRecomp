"""Back up and install the verified entrance/A02 collection in both player folders."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
EXE = 'SuperCastlevaniaIvSNESRecomp.exe'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protected(folder):
    paths = [folder / n for n in ('config.ini','keybinds.ini','rom.cfg','performance_settings.json')]
    for name in ('saves','debug_markers','characters','enemy_packs'):
        paths += [p for p in (folder / name).rglob('*') if p.is_file()]
    return {str(p.relative_to(folder)): sha(p) for p in paths if p.is_file()}


def install(pack, exe, backup):
    pack, exe, backup = Path(pack).resolve(), Path(exe).resolve(), Path(backup).resolve()
    if backup.exists():
        raise FileExistsError('Use a new backup directory')
    receipt = json.loads((pack / 'import.json').read_text(encoding='utf-8'))
    # Older receipts hardcoded a 10x presentation even for 4x A02 artwork.
    presentation_scale = int(receipt['art_scale'])
    if not 1 <= presentation_scale <= 10:
        raise ValueError('Invalid artwork scale')
    for source in receipt['sources']:
        if sha(source['source']) != source['sha256']:
            raise ValueError('Artwork changed after import: ' + source['source'])
    targets = [ROOT / 'build-play/game', ROOT / 'build']
    for folder in targets:
        if not (folder / EXE).is_file():
            raise FileNotFoundError(folder / EXE)
        if (folder / 'hd_packs' / pack.name).exists():
            raise FileExistsError('Pack already installed: ' + str(folder))
    backup.mkdir(parents=True)
    report = {'pack': str(pack), 'exe_sha256': sha(exe), 'targets': [], 'sources': receipt['sources']}
    for source in receipt['sources']:
        base = backup / 'source-pngs'
        if source.get('kind') == 'registered-manual-correction':
            base /= 'Manuelle-Korrekturen'
        dst = base / Path(source['source']).name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source['source'], dst)
        assert sha(dst) == source['sha256']
    for folder in targets:
        label = folder.relative_to(ROOT).as_posix().replace('/', '-')
        before = protected(folder)
        saved = backup / label
        saved.mkdir()
        shutil.copy2(folder / EXE, saved / EXE)
        settings_path = folder / 'hd_settings.json'
        settings = json.loads(settings_path.read_text(encoding='utf-8-sig')) if settings_path.exists() else {}
        if settings_path.exists():
            shutil.copy2(settings_path, saved / settings_path.name)
        if folder / EXE != exe:
            pending = folder / (EXE + '.a02-new')
            shutil.copy2(exe, pending)
            pending.replace(folder / EXE)
        destination = folder / 'hd_packs' / pack.name
        shutil.copytree(pack, destination)
        copied = {str(p.relative_to(pack)): sha(p) for p in pack.rglob('*') if p.is_file()}
        assert all(sha(destination / name) == checksum for name, checksum in copied.items())
        settings.update(enabled=1, scale=presentation_scale, layers=31, pack='hd_packs/' + pack.name)
        settings_path.write_text(json.dumps(settings, indent=2) + '\n')
        assert sha(folder / EXE) == report['exe_sha256']
        after = protected(folder)
        item = {'folder': str(folder), 'pack_files_sha256': copied,
                'protected_files_before': before, 'protected_files_after': after,
                'protected_files_unchanged': before == after, 'settings': settings}
        report['targets'].append(item)
        if before != after:
            raise RuntimeError('Protected data changed during installation; inspect report')
    (backup / 'install.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'installed': [t['folder'] for t in report['targets']], 'backup': str(backup),
                      'protected_files_unchanged': all(t['protected_files_unchanged'] for t in report['targets'])}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    args = parser.parse_args()
    install(args.pack, args.exe, args.backup)
