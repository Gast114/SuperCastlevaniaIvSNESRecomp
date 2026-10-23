"""Render actual 4K/small-window menus and exercise the shortcut widgets."""
import argparse
import json
import re
from PIL import Image
import sciv_test_support as sciv

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--rom',required=True)
sciv.add_build_arg(p)
a=p.parse_args();build=sciv.build_dir(a);work=sciv.work_dir(build,'menu-scale-')
report=[]
for name,size,shortcuts,preference in (
    ('small','800x600',True,0),
    ('small-settings','800x600',False,0),
    ('4k-shortcuts','3840x2160',True,0),
    ('4k-settings','3840x2160',False,0),
    ('4k-manual','3840x2160',False,150),
    ('4k-size-click','3840x2160',False,150),
):
    folder=work/name
    sciv.prepare(folder,build,{'Graphics':{'WindowScale':1},'General':{'DisableFrameDelay':1}})
    if preference and name!='4k-size-click':(folder/'ui_settings.json').write_text(json.dumps({'menu_scale':preference}))
    log=sciv.run(folder,'widescreen_smoke.input',a.rom,sciv.clean_env(
        SNESRECOMP_RUN_FRAMES=1310,SNESRECOMP_SETTINGS_SELFTEST=1295,
        SNESRECOMP_UI_SCALE_SELFTEST=size,
        **({'SNESRECOMP_UI_SCALE_PICK':150} if name=='4k-size-click' else {}),
        **({'SNESRECOMP_SHORTCUT_UI_SELFTEST':1} if shortcuts else {})))
    match=re.search(r'menu layout display=(\d+x\d+) scale=([\d.]+) font=([\d.]+) nav_bottom=([\d.]+) fits=(\d)',log)
    assert match,log[-3000:]
    actual,scale,font,bottom,fits=match.groups()
    assert actual==size and fits=='1',match.group(0)
    assert float(bottom)<int(size.split('x')[1])*.4,match.group(0)
    expected=1 if size=='800x600' else 1.5 if preference else 2
    assert float(scale)==expected and float(font)==18*expected,match.group(0)
    if preference:assert json.loads((folder/'ui_settings.json').read_text())=={'menu_scale':150}
    if shortcuts:
        for check in ('conflict retained','rebound','cancel retained','cleared','final'):
            assert f'shortcut {check}=1' in log,(check,log[-3000:])
    pictures=sorted((folder/'screenshots').glob('*.bmp'))
    assert pictures,'No composited menu screenshot'
    for i,path in enumerate(pictures):
        image=Image.open(path)
        assert image.size==tuple(map(int,size.split('x'))),(path,image.size)
        image.save(folder/f'menu-{i}.png')
    report.append({'case':name,'display':actual,'scale':float(scale),'font':float(font),'navigation_fits':True})
(work/'report.json').write_text(json.dumps({'passed':True,'cases':report},indent=2))
print('PASS: real 800x600 and 3840x2160 menus, crisp 18/36px fonts, wrapped navigation, shortcut clicks, menu-size dropdown click/save/read')
