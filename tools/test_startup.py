"""Check boot with saved run-ahead preferences in isolated executable folders."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil
from PIL import Image

import sciv_test_support as sciv

p = argparse.ArgumentParser()
p.add_argument('--rom', required=True)
p.add_argument('--expect-visible', action='store_true')
p.add_argument('--exe', type=Path)
sciv.add_build_arg(p)
args = p.parse_args()
build = sciv.build_dir(args)
work = sciv.work_dir(build, 'startup-check-')

def run(ahead):
    folder = work / str(ahead)
    exe = sciv.prepare(folder, build, {'General': {'RunAhead': ahead}})
    if args.exe:
        shutil.copy2(args.exe, exe)
    sciv.run(folder, 'character_workshop_smoke.input', args.rom,
             sciv.clean_env(SNESRECOMP_RUN_FRAMES=1400, SNESRECOMP_SCREENSHOT_FRAME=1300,
                            SNESRECOMP_SCREENSHOT=folder/'game.ppm'), timeout=160)
    shot = Image.open(folder/'game.ppm').convert('RGB')
    shot.save(folder/'game.png')
    visible = shot.getbbox() is not None
    print(f'RunAhead={ahead}: visible={visible}', flush=True)
    if args.expect_visible:
        assert visible, f'Black screen with RunAhead={ahead}'

with ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(run, [0, 1]))
