"""Replay three native poses in both directions with a partial 10x character pack."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
import time
import numpy as np
from PIL import Image
import sciv_play as play
import sciv_test_support as sciv


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('rom','character','pack','fixture'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--all-scales',action='store_true',help='Explicit developer diagnostic; default tests 10x only')
    sciv.add_build_arg(p);a=p.parse_args();build=sciv.build_dir(a);work=sciv.work_dir(build,'character-hd-')
    manifest=json.loads((a.character/'character.json').read_text());frames={f['id']:f for f in manifest['frames']}
    runs=[];found=set();native_off=[]
    for custom in (False,True):
        folder=work/('custom' if custom else 'native');exe=sciv.prepare(folder,build,{'Graphics':{'Widescreen':1},'General':{'DisableFrameDelay':1}})
        if custom:
            shutil.copytree(a.character,folder/'characters/hd-preview');(folder/'characters/selected.txt').write_text('hd-preview')
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        samples={};lua=None
        with (folder/'game.log').open('w') as log:
            proc=subprocess.Popen([str(exe),str(a.rom.resolve())],cwd=folder,env=sciv.clean_env(SNESRECOMP_LUA_PORT=port,SNESRECOMP_LUA_PAUSED=1),stdout=log,stderr=log,startupinfo=sciv.hidden_window())
            try:
                for _ in range(200):
                    try:lua=play.LuaClient(port=port);lua.command('ping');break
                    except OSError:assert proc.poll() is None;time.sleep(.05)
                assert lua
                def cmd(n,arg=''):return lua.eval(f'return game.command({json.dumps(n)},{json.dumps(str(arg))})')['values'][0]
                cmd('hd','pack '+str(a.pack.resolve()));cmd('hd','scale 10');cmd('hd','on')
                def check_pixels(shot,pose,facing,scale,image_file=None):
                    image=np.array(Image.open(image_file or a.character/frames[pose['pose']]['hd']['image']).convert('RGBA'))
                    display=frames[pose['pose']]['hd'].get('display_size')
                    if display:
                        yy=np.arange(display[1]*10)*image.shape[0]//(display[1]*10);xx=np.arange(display[0]*10)*image.shape[1]//(display[0]*10)
                        image=image[yy[:,None],xx[None,:]]
                    if facing=='left':image=image[:,::-1]
                    yy=np.arange(image.shape[0]//10*scale)*10//scale;xx=np.arange(image.shape[1]//10*scale)*10//scale
                    image=image[yy[:,None],xx[None,:]]
                    actual=np.array(Image.open(shot).convert('RGB'))
                    margin=(actual.shape[1]//scale-256)//2
                    x=(pose['x']+margin)*scale;y=pose['y']*scale
                    crop=actual[y:y+image.shape[0],x:x+image.shape[1]]
                    opaque=image[...,3]==255
                    assert crop.shape==image[...,:3].shape,(crop.shape,image.shape)
                    exact=np.all(crop==image[...,:3],axis=2)&opaque
                    assert exact.sum()>opaque.sum()*.98,('HD detail/alignment lost',scale,exact.sum(),opaque.sum())
                def inspect(facing,label):
                    pose=json.loads(cmd('characterhd'));state=play.read_state(lua);state.pop('frame');state.pop('paused')
                    key=facing+'-'+pose['pose']
                    if pose['pose'] in frames and key not in samples:
                        shot=folder/(facing+'-'+frames[pose['pose']]['label']+'.png');cmd('hdshot',shot)
                        samples[key]={'state':state,'pose':pose,'shot':str(shot)}
                        if custom:
                            assert pose['active']==1,pose
                            check_pixels(shot,pose,facing,10)
                            found.add((facing,frames[pose['pose']]['label']))
                    return pose
                for facing in ('right','left'):
                    cmd('loadfile',a.fixture.resolve());play.advance(lua,1)
                    if facing=='left':play.advance(lua,1,('Left',));play.advance(lua,10)
                    inspect(facing,'idle')
                    for _ in range(8):play.advance(lua,1,('Down',));inspect(facing,'duck')
                    play.advance(lua,3)
                    for i in range(42):play.advance(lua,1,('B',) if i<4 else ());inspect(facing,'jump')
                if custom:
                    for scale in ((2,4,6,10) if a.all_scales else (10,)):
                        cmd('hd','scale '+str(scale));cmd('loadfile',a.fixture.resolve());play.advance(lua,1)
                        pose=json.loads(cmd('characterhd'));shot=folder/f'scale-{scale}.png';cmd('hdshot',shot);check_pixels(shot,pose,'right',scale)
                    cmd('hd','layers 15');play.advance(lua,1);assert not json.loads(cmd('characterhd'))['active']
                    cmd('hd','layers 31');play.advance(lua,1);assert json.loads(cmd('characterhd'))['active']
                    # Reload only the isolated copy. A new immutable image
                    # must invalidate composed cells; a partial PNG keeps the
                    # last valid pack until the artist finishes saving.
                    pose=json.loads(cmd('characterhd'));target=folder/'characters/hd-preview'/frames[pose['pose']]['hd']['image']
                    original=target.read_bytes();duck=next(f for f in frames.values() if f['label']=='Ducking-01')
                    replacement=a.character/duck['hd']['image'];shutil.copyfile(replacement,target)
                    play.advance(lua,30);pose=json.loads(cmd('characterhd'))
                    display=frames[pose['pose']]['hd'].get('display_size')
                    assert (pose['width'],pose['height'])==(tuple(v*10 for v in display) if display else Image.open(replacement).size)
                    shot=folder/'reloaded.png';cmd('hdshot',shot);check_pixels(shot,pose,'right',10,replacement)
                    valid_width=pose['width'];target.write_bytes(b'incomplete PNG');play.advance(lua,30)
                    assert json.loads(cmd('characterhd'))['width']==valid_width,'incomplete save replaced the valid pack'
                    target.write_bytes(original);play.advance(lua,30)
                    pose=json.loads(cmd('characterhd'));shot=folder/'restored.png';cmd('hdshot',shot);check_pixels(shot,pose,'right',10)
                # Original mode must restore the same native picture, even
                # though the partial HD pack remains selected.
                cmd('hd','off');cmd('loadfile',a.fixture.resolve());play.advance(lua,2)
                cmd('screenshot',folder/'original.png');native_off.append(hashlib.sha256((folder/'original.png').read_bytes()).hexdigest())
                assert not json.loads(cmd('characterhd'))['active']
                cmd('hd','on');cmd('loadfile',a.fixture.resolve());play.advance(lua,4,('Right',))
                assert not json.loads(cmd('characterhd'))['active'],'missing walking pose must fall back'
            finally:
                if lua:lua.close()
                proc.terminate();proc.wait(timeout=10)
        runs.append(samples)
    assert native_off[0]==native_off[1],'HD off changed native Simon'
    assert len(found)==6,found
    assert runs[0].keys()==runs[1].keys()
    for key in runs[0]:assert runs[0][key]['state']==runs[1][key]['state'],key
    (work/'report.json').write_text(json.dumps({'passed':True,'poses':sorted(found),'runs':runs},indent=2))
    print('PASS: all three full-resolution poses and mirrors; selected scale(s); positions/gameplay unchanged; original/sprite toggle, missing-pose fallback, reload and incomplete-file recovery')


if __name__=='__main__':main()
