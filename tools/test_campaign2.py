"""Isolated smoke checks for NEW GAME+; never writes the installed character pack."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import re
from PIL import Image

import sciv_test_support as sciv

parser = argparse.ArgumentParser()
parser.add_argument('--rom', required=True)
sciv.add_build_arg(parser)
args = parser.parse_args()
build = sciv.build_dir(args)
work = sciv.work_dir(build, 'campaign-check-')


def run(case):
    name, script, frames, shot_frame = case
    folder = work / name
    sciv.prepare(folder, build, {'Graphics': {'Widescreen': 1}})
    log = sciv.run(folder, script, args.rom, sciv.clean_env(
        SNESRECOMP_RUN_FRAMES=frames, SNESRECOMP_SCREENSHOT_FRAME=shot_frame,
        SNESRECOMP_SCREENSHOT=folder / 'frame.ppm', SNESRECOMP_CAMPAIGN_PROBE=1))
    shot = Image.open(folder / 'frame.ppm').convert('RGB')
    shot.save(folder / 'frame.png')
    assert shot.getbbox(), f'{name}: black screen'
    if name == 'room':
        # NEW GAME+ (entry 3) starts like START once confirmed, with the tag set.
        assert 'choice=3' in log and 'choice=0 pending=0 active=1' in log
        positions = [tuple(map(int, p)) for p in re.findall(
            r'\[campaign_room\] frame=(\d+) x=(\d+) y=(\d+)', log)]
        assert any(y < 150 for _, _, y in positions), 'jump did not leave floor'
        assert positions[-1][2] == 165, 'player did not land'
        assert max(x for _, x, _ in positions) == 240, 'right boundary failed'
        # No inherited scenery above or left of the player at the right wall.
        assert shot.crop((0, 0, shot.width, 120)).getbbox() is None
        assert shot.crop((0, 120, shot.width // 2, 192)).getbbox() is None
        assert all(shot.getpixel((x, 200)) != (0, 0, 0)
                   for x in range(shot.width)), 'missing widescreen floor'
    elif name == 'original':
        assert 'phase=4/5' in log and 'active=1' not in log
        assert len(shot.getcolors(100000)) > 30, 'original scenery missing'
    elif name == 'options':
        assert 'phase=5/0' in log and 'active=1' not in log
    print(f'{name}: PASS', flush=True)


with ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(run, [
        ('room', 'campaign2_smoke.input', 1320, 1300),
        ('original', 'widescreen_smoke.input', 1320, 1300),
        ('options', 'campaign2_options_smoke.input', 680, 650),
        ('menu', 'campaign2_smoke.input', 330, 325),
    ]))
