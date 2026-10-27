"""Click the HD checkbox through ImGui, persist/reload it, capture HD markers."""
import argparse
import json
from pathlib import Path
from PIL import Image
import sciv_test_support as sciv

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--rom', required=True)
p.add_argument('--pack', type=Path, required=True)
sciv.add_build_arg(p)
args = p.parse_args()
build = sciv.build_dir(args)
work = sciv.work_dir(build, 'hd-ui-check-')
sciv.prepare(work, build, {'Graphics': {'Widescreen': 1}})
(work / 'hd_settings.json').write_text(json.dumps(dict(enabled=0,scale=4,layers=31,pack=str(args.pack.resolve()))))
for expected in (1, 0):
    old = set((work / 'debug_markers').glob('*'))
    log = sciv.run(work, 'widescreen_smoke.input', args.rom, sciv.clean_env(
        SNESRECOMP_RUN_FRAMES=1310,
        SNESRECOMP_HD_PACK=args.pack.resolve(), SNESRECOMP_HD_UI_SELFTEST=1,
        SNESRECOMP_SETTINGS_SELFTEST=1295,
        SNESRECOMP_DEBUG_MARKER_AT=1300, SNESRECOMP_DEBUG_MARKER_NOTE='HD UI toggle'),
        log_name=f'click-{expected}.log')
    saved = json.loads((work / 'hd_settings.json').read_text())
    assert saved['enabled'] == expected, saved
    assert saved['scale'] == 4, 'Opening the HD panel must preserve the saved render resolution'
    marker, = set((work / 'debug_markers').glob('*')) - old
    meta = json.loads((marker / 'marker.json').read_text())
    assert meta['hd']['enabled'] == expected, meta['hd']
    if expected:
        assert Image.open(marker / 'hd_screen.png').size == (1368, 896)
    else:
        assert not (marker / 'hd_screen.png').exists()
    assert Image.open(marker / 'screen.png').size == (342, 224)
print('PASS: mouse checkbox on/off, persisted across relaunch; HD and native marker images')
