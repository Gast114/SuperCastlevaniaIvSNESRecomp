"""Replay the real A04 pit save: retain its picture through death phase 12/6."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tempfile

import numpy as np
from PIL import Image
from enemy_workshop_native import ROOT, NativeSession, play


def foreground(pack, stage):
    folder=pack/stage
    regions=[r for r in json.loads((folder/'pack.json').read_text())['regions'] if r['layer']==0 and not r.get('overlay')]
    left=min(r['x'] for r in regions);top=min(r['y'] for r in regions)
    right=max(r['x']+Image.open(folder/r['image']).width//4 for r in regions)
    bottom=max(r['y']+Image.open(folder/r['image']).height//4 for r in regions)
    image=Image.new('RGBA',((right-left)*4,(bottom-top)*4))
    for r in regions:image.paste(Image.open(folder/r['image']),((r['x']-left)*4,(r['y']-top)*4))
    return image,left,top


def check(pack, fixture, build):
    work=Path(tempfile.mkdtemp(prefix='hd-death-picture-',dir=ROOT/'build-lua'));print(work,flush=True)
    source_sha=hashlib.sha256(fixture.read_bytes()).hexdigest()
    images={stage:foreground(pack,stage) for stage in ('a03','a04')}
    session=NativeSession(build=build,folder=work/'game');cases=[]
    try:
        session.start(fixture);session.command('enemy','workshop off')
        session.command('hd','pack '+str(pack));session.command('hd','scale 4');session.command('layers',1)
        for label,buttons in [('idle',()),('right',('Right',))]:
            runs=[];outgoing=0;restarted=False
            for enabled in (False,True):
                session.command('hd','on' if enabled else 'off');session.command('loadfile',fixture)
                states=[]
                for frame in range(1,141):
                    play.advance(session.lua,1,buttons)
                    state=play.read_state(session.lua);state.pop('frame');state.pop('paused');states.append(state)
                    phase,block=state['level_phase'],state['block']
                    if enabled and ((phase in (12,6) and frame%4==0) or (phase==5 and block==2 and not restarted)):
                        stage='a03' if phase==5 else 'a04'
                        if stage=='a03':restarted=True
                        image,left,top=images[stage]
                        path=work/f'{label}-{frame:03d}.png';session.command('hdshot',path)
                        actual=np.array(Image.open(path).convert('RGB'));ppu=json.loads(session.command('ppu'))
                        h,v=ppu['layers'][0]['h'],ppu['layers'][0]['v'];v=v-1024 if v>=512 else v
                        margin=actual.shape[1]//4//2-128
                        crop=np.array(image.crop(((h-margin-left)*4,(v+1-top)*4,(h+256+margin-left)*4,(v+225-top)*4)))
                        expected=(crop[:,:,:3].astype(np.uint32)*crop[:,:,3,None]+127)//255
                        lines=work/'lines.bin';session.command('lines',lines);raw=lines.read_bytes()
                        brightness=np.array([struct.unpack_from('<12BH4H4HH',raw,i*32)[1]&15 for i in range(1,225)],np.uint32).repeat(4)
                        expected=(expected*brightness[:,None,None]//15).astype(np.uint8)
                        diff=int(np.count_nonzero(np.any(actual!=expected,axis=2)))
                        assert diff==0,(label,frame,phase,block,stage,'wrong picture',diff)
                        if stage=='a04' and brightness.max()>0:outgoing+=1
                runs.append(states)
            assert runs[0]==runs[1],label+' native logic changed'
            assert outgoing>=5 and restarted,(label,outgoing,restarted)
            cases.append(dict(action=label,outgoing_visible_frames_checked=outgoing,checkpoint_a03_loaded=True,native_states_identical=True))
    finally:session.close()
    assert hashlib.sha256(fixture.read_bytes()).hexdigest()==source_sha
    report=dict(passed=True,fixture_sha256=source_sha,cases=cases)
    (work/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('pack','fixture'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--build',type=Path,default=ROOT/'build-lua')
    a=p.parse_args();check(a.pack.resolve(),a.fixture.resolve(),a.build.resolve())
