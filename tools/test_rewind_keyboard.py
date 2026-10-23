"""Open rewind with real F8 SDL events, select history, accept/cancel and resume."""
import argparse
import re
from pathlib import Path
import sciv_test_support as sciv

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--rom',type=Path,required=True)
sciv.add_build_arg(p);args=p.parse_args()
build=sciv.build_dir(args);work=sciv.work_dir(build,'rewind-key-check-')
for action in ('cancel','commit'):
    folder=work/action
    sciv.prepare(folder,build,{'General':{'DisableFrameDelay':1},'KeyMap':{'Rewind':'F8'},
                               'Graphics':{'WindowScale':1}})
    log=sciv.run(folder,'widescreen_smoke.input',args.rom,sciv.clean_env(
        SNESRECOMP_RUN_FRAMES=1340,SNESRECOMP_REWIND_KEY_SELFTEST=action,
        SNESRECOMP_DEBUG_MARKER_AT=1330,SNESRECOMP_DEBUG_MARKER_NOTE='Rewind resumed'),timeout=60)
    assert '[rewind_key_selftest] FAIL' not in log,log[-4000:]
    opened=re.findall('rewind filmstrip OPEN',log)
    assert len(opened)==1,(action,len(opened),log[-3000:])
    assert 'rewind filmstrip CLOSED' in log,log[-3000:]
    assert re.search(r'selected 0\.100s; '+action,log),log[-3000:]
    assert list((folder/'debug_markers').glob('*/marker.json')),'Game did not advance after closing rewind'
    print(action+': PASS: F8, select older point, close once and continue frames',flush=True)
