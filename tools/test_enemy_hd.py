"""Compile and exercise complete enemy replacement with synthetic ROM data.

All files stay inside a new isolated artifact directory. No player settings,
save states, source artwork or copyrighted ROM are read or changed.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from PIL import Image
import enemy_hd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('artwork-local/enemy-hd-2026-10-23'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='synthetic-', dir=args.output)).resolve()
    compiler = shutil.which('clang++')
    if not compiler:
        raise SystemExit('clang++ is required for the standalone renderer test')
    exe = work / 'enemy_hd_probe.exe'
    command = [compiler, '-std=c++17', str(root / 'tools/enemy_hd_probe.cpp'), str(root / 'src/enemy_pack.cpp'),
               '-I', str(root / 'src'), '-I', str(root / 'snesrecomp/runner/src'),
               '-I', str(root / 'recomp-ui/src'), '-o', str(exe)]
    subprocess.run(command, check=True, capture_output=True)
    capture = subprocess.run([str(exe)], cwd=work, check=True, capture_output=True, text=True).stdout
    references = work / 'enemy_packs/native-template'
    manifest = json.loads((references / 'enemies.json').read_text())
    assert len(manifest['frames']) == 1
    project = work / 'art-project'
    enemy_hd.prepare(references, project)
    source = next((project / 'artwork').glob('*.png'))
    with Image.open(source) as image:
        image.resize((387, 387), Image.Resampling.NEAREST).save(source)
    assert enemy_hd.pack(project, work / 'enemy_packs/diagnostic') == 1
    test = subprocess.run([str(exe), 'verify'], cwd=work, check=True, capture_output=True, text=True).stdout
    # Safe retries never overwrite earlier artist files.
    try:
        enemy_hd.pack(project, work / 'enemy_packs/diagnostic')
    except ValueError:
        pass
    else:
        raise AssertionError('Existing artwork must not be overwritten')
    (work / 'report.json').write_text(json.dumps({'passed': True, 'capture': capture.splitlines(), 'checks': test.splitlines(),
                                                'source_resolution': [387, 387], 'native_canvas': [96, 96],
                                                'real_game_coverage': False}, indent=2) + '\n')
    print(work)
    print(capture + test, end='')


if __name__ == '__main__':
    main()
