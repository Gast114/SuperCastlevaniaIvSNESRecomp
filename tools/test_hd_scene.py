"""Live scene planes: native identity, real alpha, scene guards and bridge state.

Uses isolated Lua processes; no player configuration or saves are touched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time

import numpy as np
from PIL import Image
import sciv_play as play
import sciv_test_support as sciv


def image(path):
    return np.array(Image.open(path).convert('RGB'))


def plane_pack(folder, planes, block=0):
    folder.mkdir()
    regions=[]
    for n,(layer,x,y,rgba) in enumerate(planes):
        name=f'plane{n}.png';Image.fromarray(rgba).save(folder/name)
        regions.append({'layer':layer,'image':name,'x':x,'y':y,'coordinates':'world' if layer==0 else 'map',
                        'wrap_x':0 if layer==0 else 512,'wrap_y':0 if layer==0 else 256})
    (folder/'pack.json').write_text(json.dumps({'version':1,'scale':10,'tile_size':80,'atlas_size':2048,
        'tiles':{},'requires':['scene-regions-v1'],'scene_block':block,'regions':regions}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--pack',type=Path,required=True)
    p.add_argument('--fixture',type=Path,default=sciv.ROOT/'artwork-local/fixtures/block-1-1/state.sav')
    p.add_argument('--bridge',type=Path,default=sciv.ROOT/'artwork-local/stage01-user-v1/fixtures/bridge/state.sav')
    p.add_argument('--workers',type=int,choices=range(1,9))
    sciv.add_build_arg(p);a=p.parse_args();build=sciv.build_dir(a);work=sciv.work_dir(build,'hd-scene-check-')
    # Native captured planes preserve original alpha, not a flattened screenshot.
    source=sciv.ROOT/'artwork-local/pilot-1-1-v1/source'
    fg=np.array(Image.open(sciv.ROOT/'artwork-local/captures/pilot/captures/level_b00/bg1_1792355363108116_000924.png').convert('RGBA'))
    bg=np.array(Image.open(source/'bg2.png').convert('RGBA'))
    plane_pack(work/'identity',[(0,0,0,fg.repeat(10,0).repeat(10,1)),(1,0,0,bg.repeat(10,0).repeat(10,1))])
    yy,xx=np.indices((80,80));alpha=np.clip((xx-yy)*32+128,0,255).astype(np.uint8)
    cyan=np.zeros((80,80,4),np.uint8);cyan[...,:3]=(30,200,220);cyan[...,3]=alpha
    plane_pack(work/'alpha',[(0,232,40,cyan)])
    plane_pack(work/'wrong-scene',[(0,232,40,cyan)],block=1)
    folder=work/'game';exe=sciv.prepare(folder,build,{'Graphics':{'Widescreen':1},'General':{'DisableFrameDelay':1}})
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    report={'checks':[],'pack_sha256':hashlib.sha256((a.pack/'pack.json').read_bytes()).hexdigest()}
    lua=None
    with (folder/'game.log').open('w') as log:
        proc=subprocess.Popen([str(exe),str(a.rom.resolve())],cwd=folder,
            env=sciv.clean_env(SNESRECOMP_LUA_PORT=port,SNESRECOMP_LUA_PAUSED=1,
                **({'SNESRECOMP_RENDER_WORKERS':a.workers} if a.workers else {})),stdout=log,stderr=log,startupinfo=sciv.hidden_window())
        try:
            for _ in range(200):
                if proc.poll() is not None:raise RuntimeError('Game exited; inspect game.log')
                try:lua=play.LuaClient(port=port);lua.command('ping');break
                except OSError:time.sleep(.05)
            assert lua
            def command(n,arg=''):
                return lua.eval(f'return game.command({json.dumps(n)},{json.dumps(str(arg))})')['values'][0]
            def capture(label,fixture,enabled,frames=1,buttons=()):
                command('hd','on' if enabled else 'off');command('loadfile',fixture.resolve());play.advance(lua,frames,buttons)
                command('screenshot',work/(label+'.png'))
                state=play.read_state(lua);state.pop('frame');state.pop('paused')
                if enabled:command('hdshot',work/(label+'-hd.png'))
                return image(work/(label+'.png')),state
            command('hd','scale 10');native,state=capture('original',a.fixture,False)
            command('hd','pack '+str((work/'identity').resolve()))
            for scale in (2,4,10):
                command('hd',f'scale {scale}');actual,s=capture(f'identity-{scale}',a.fixture,True)
                rendered=image(work/f'identity-{scale}-hd.png')
                assert np.array_equal(rendered,native.repeat(scale,0).repeat(scale,1)),f'nearest identity at {scale}x'
                assert np.array_equal(actual,native) and s==state
            report['checks'].append('Scene planes: exact 2/4/10x native identity, native pixels/state unchanged')
            command('hd','scale 10');command('hd','pack '+str((work/'alpha').resolve()))
            _,_=capture('alpha',a.fixture,True)
            rendered=image(work/'alpha-hd.png');margin=(native.shape[1]-256)//2
            original=native[40:48,margin+232:margin+240].repeat(10,0).repeat(10,1).astype(np.uint32)
            expected=(cyan[...,:3].astype(np.uint32)*alpha[...,None]+original*(255-alpha[...,None])+127)//255
            actual=rendered[400:480,(margin+232)*10:(margin+240)*10]
            assert np.array_equal(actual,expected.astype(np.uint8)),'HD alpha over native-transparent BG1'
            command('hd','layers 0');capture('disabled',a.fixture,True)
            assert np.array_equal(image(work/'disabled-hd.png'),native.repeat(10,0).repeat(10,1))
            command('hd','layers 31');command('hd','pack '+str((work/'wrong-scene').resolve()))
            capture('wrong-scene',a.fixture,True)
            assert np.array_equal(image(work/'wrong-scene-hd.png'),native.repeat(10,0).repeat(10,1))
            report['checks'].append('Subpixel alpha outside native silhouette; category and scene guards')
            command('hd','pack '+str(a.pack.resolve()))
            cases=[('start',a.fixture,1,()),('scroll',a.fixture,160,('Right',)),
                   ('bridge',a.bridge,1,()),('water-phase',a.bridge,11,()),('bridge-rotated',a.bridge,97,())]
            states={}
            for label,fixture,frames,buttons in cases:
                before,s0=capture(label+'-original',fixture,False,frames,buttons)
                after,s1=capture(label,fixture,True,frames,buttons)
                again,s2=capture(label+'-original-again',fixture,False,frames,buttons)
                assert np.array_equal(before,after) and np.array_equal(before,again) and s0==s1==s2,label
                painted=image(work/(label+'-hd.png'))
                assert not np.array_equal(painted,before.repeat(10,0).repeat(10,1)),label+' did not use HD'
                states[label]=s1
            assert states['bridge-rotated']['player_y']<states['bridge']['player_y']-10,'Bridge did not rotate'
            first=image(work/'bridge-hd.png')[2080:2200,(margin+60)*10:(margin+90)*10]
            later=image(work/'water-phase-hd.png')[2080:2200,(margin+60)*10:(margin+90)*10]
            assert not np.array_equal(first,later),'HD water did not animate'
            report.update(checks=report['checks']+['User pack: original/HD/original state and native images identical at start, scroll and rotating bridge; HD water changes phase'],states=states,passed=True)
            (work/'report.json').write_text(json.dumps(report,indent=2));print('PASS:', '; '.join(report['checks']),flush=True)
        finally:
            if lua:lua.close()
            proc.terminate();proc.wait(timeout=10)


if __name__=='__main__':main()
