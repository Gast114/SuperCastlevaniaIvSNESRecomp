"""Real performance-menu clicks, all timing modes, persistence and small-window navigation."""
import argparse
import json
import sciv_test_support as sciv

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--rom',required=True)
sciv.add_build_arg(p);a=p.parse_args()
build=sciv.build_dir(a);work=sciv.work_dir(build,'performance-ui-')
sciv.prepare(work,build,{'Graphics':{'WindowScale':1},'General':{'DisableFrameDelay':1}})
initial=2
for selected in (0,1,2,0):
    log=sciv.run(work,'widescreen_smoke.input',a.rom,sciv.clean_env(
        SNESRECOMP_RUN_FRAMES=1310,SNESRECOMP_SETTINGS_SELFTEST=1295,
        SNESRECOMP_PERFORMANCE_UI_SELFTEST=selected),log_name=f'click-{initial}-{selected}.log')
    assert f'performance initial={initial}' in log,log[-3000:]
    assert f'performance selected={selected}' in log,log[-3000:]
    assert 'performance navigation fits=1' in log,log[-3000:]
    assert json.loads((work/'performance_settings.json').read_text())=={'cpu_timing':selected}
    initial=selected
(work/'report.json').write_text(json.dumps({'passed':True,'selected':[0,1,2,0]}))
print('PASS: real menu selection, modes 0/1/2 persist across restart, navigation fits the small-window menu')
