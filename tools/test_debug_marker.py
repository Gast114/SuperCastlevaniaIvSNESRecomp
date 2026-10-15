"""Debug marker smoke test: opens a marker in block 1-1 via the self-test hooks,
checks every capture file and that the game runs on afterwards."""
import argparse
import json

from PIL import Image

import sciv_test_support as sciv

parser = argparse.ArgumentParser()
parser.add_argument('--rom', required=True)
sciv.add_build_arg(parser)
args = parser.parse_args()
build = sciv.build_dir(args)
folder = sciv.work_dir(build, 'marker-check-')
sciv.prepare(folder, build, {'Graphics': {'Widescreen': 1}})
log = sciv.run(folder, 'widescreen_smoke.input', args.rom, sciv.clean_env(
    SNESRECOMP_RUN_FRAMES=1400, SNESRECOMP_DEBUG_MARKER_AT=1300,
    SNESRECOMP_DEBUG_MARKER_NOTE='smoke test note'))
assert 'debug marker CLOSED after 5 pumps' in log, 'marker panel did not close'
found = list((folder / 'debug_markers').glob('*_level'))
assert len(found) == 1, f'expected one level marker, got {found}'
marker = found[0]
sizes = {p.name: p.stat().st_size for p in marker.iterdir()}
assert sizes.get('wram.bin') == 0x20000, sizes
assert sizes.get('video.bin') == 0x10000 + 0x200 + 0x200 + 0x20, sizes
assert sizes.get('state.sav', 0) > 100000, sizes
assert Image.open(marker / 'screen.png').size == (342, 224)
data = json.loads((marker / 'marker.json').read_text(encoding='utf-8'))
assert data['note'] == 'smoke test note' and data['frame'] == 1300, data
assert data['scene'] == 'level' and data['state']['level_phase'] == 5, data
assert data['ppu']['extra'] == 43, data
print('PASS: marker captured at frame 1300 with all files; game resumed')
