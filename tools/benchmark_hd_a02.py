"""Private deterministic A02 performance replay; never opens captured images."""
import argparse
import configparser
import hashlib
import json
import os
import time
from pathlib import Path
import tempfile
from PIL import Image
from enemy_workshop_native import ROOT, NativeSession, play


def run(build, label, frames, reference=None, scale=4):
    os.environ['SCIV_HD_TIMINGS']='1'
    folder=Path(tempfile.mkdtemp(prefix='a02-perf-'+label+'-',dir=build))
    session=NativeSession(build=build,folder=folder/'game')
    config=configparser.ConfigParser();config.read(session.folder/'config.ini')
    config['Graphics']['Widescreen']='1'
    config['General']['RunAhead']='0'
    with (session.folder/'config.ini').open('w') as f:config.write(f)
    fixture=ROOT/'artwork-local/a02-layer-audit-2026-10-23/user-saves'
    report={'label':label,'frames':frames,'scale':scale,'unthrottled':True,'cases':[]}
    print(folder,flush=True)
    try:
        s=session.start(fixture/'F3.sav');s.command('enemy','workshop off')
        s.command('hd','pack '+str(ROOT/'build/hd_packs/stage-01-user-a02-v3'))
        s.command('hd','scale '+str(scale));s.command('hd','on')
        for name,save,buttons in [('idle','F3',()),('walk','F3',('Right',)),('attack','F3',('Y',)),('entrance','F2',('Right','Y'))]:
            s.command('loadfile',fixture/(save+'.sav'));play.advance(s.lua,1)
            start=time.perf_counter();play.advance(s.lua,frames,buttons);elapsed=time.perf_counter()-start
            row={'name':name,'ms_per_frame':elapsed*1000/frames,'headroom_fps':frames/elapsed}
            for command,suffix in [('hdshot','hd.png'),('screenshot','native.png'),('wram','ram.bin')]:
                file=folder/(name+'-'+suffix);s.command(command,file)
                data=Image.open(file).convert('RGB').tobytes() if suffix.endswith('png') else file.read_bytes()
                row[suffix]=hashlib.sha256(data).hexdigest()
            report['cases'].append(row);print(json.dumps(row),flush=True)
        if reference:
            before=json.loads(reference.read_text())
            assert before['frames']==frames and before['scale']==scale
            assert len(before['cases'])==len(report['cases'])
            for old,new in zip(before['cases'],report['cases']):
                assert old['name']==new['name']
                for key in ('hd.png','native.png','ram.bin'):
                    assert old[key]==new[key],f"{new['name']}: {key} changed"
            report['reference_equal']=True
    finally:
        session.close()
        report['timings']=[line for line in (session.folder/'game.log').read_text(errors='replace').splitlines() if '[HD timing]' in line]
        (folder/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,default=ROOT/'build-lua');p.add_argument('--label',default='check')
    p.add_argument('--frames',type=int,default=240);p.add_argument('--reference',type=Path);p.add_argument('--scale',type=int,default=4)
    a=p.parse_args();run(a.build.resolve(),a.label,a.frames,a.reference,a.scale)
