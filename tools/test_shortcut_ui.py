"""Real ImGui clicks, binding capture/conflicts and SDL HD toggle dispatch."""
import argparse
import json
from pathlib import Path
import sciv_test_support as sciv

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--rom',required=True)
p.add_argument('--pack',required=True,type=Path)
sciv.add_build_arg(p);args=p.parse_args()
build=sciv.build_dir(args);work=sciv.work_dir(build,'shortcut-ui-')
for name,edit,key in [('default',False,'Ctrl'),('editor',True,'Alt')]:
    folder=work/name;sciv.prepare(folder,build,{'Graphics':{'Widescreen':1,'WindowScale':1}})
    for run,expected in enumerate((1,0)):
        old=set((folder/'debug_markers').glob('*'))
        log=sciv.run(folder,'widescreen_smoke.input',args.rom,sciv.clean_env(
            SNESRECOMP_RUN_FRAMES=1310,SNESRECOMP_HD_PACK=args.pack.resolve(),
            **({'SNESRECOMP_SHORTCUT_UI_SELFTEST':1,'SNESRECOMP_SETTINGS_SELFTEST':1295} if edit and run==0 else {}),
            SNESRECOMP_HD_KEY_SELFTEST=key,SNESRECOMP_DEBUG_MARKER_AT=1300,
            SNESRECOMP_DEBUG_MARKER_NOTE='HD shortcut regression'),log_name=f'run-{run}.log')
        if edit and run==0:
            assert 'settings menu hit-test normal=1' in log
            for check in ('conflict retained','rebound','cancel retained','cleared','final'):
                assert f'shortcut {check}=1' in log,(check,log[-3000:])
            assert 'ToggleHD=Alt+H' in (folder/'config.ini').read_text().replace(' ','')
        settings=json.loads((folder/'hd_settings.json').read_text());assert settings['enabled']==expected,settings
        marker,=set((folder/'debug_markers').glob('*'))-old
        meta=json.loads((marker/'marker.json').read_text());assert meta['hd']['enabled']==expected
print('PASS: default/rebound HD hotkey, repeat suppressed, persisted restart; real capture/conflict/cancel/clear widgets in small window')
