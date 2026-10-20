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
    p.add_argument('--stage-fixes',type=Path,help='Stage 01 edge/landed/margin fixture directory')
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
            if a.stage_fixes:
                cases += [('edge',a.stage_fixes/'edge/state.sav',1,()),
                          ('margin',a.fixture,376,('Right',))]
                cases += [('stone-'+str(frame),a.stage_fixes/'landed/state.sav',frame,())
                          for frame in (1,20,40,55,80)]
            states={}
            object_poses={}
            for label,fixture,frames,buttons in cases:
                before,s0=capture(label+'-original',fixture,False,frames,buttons)
                after,s1=capture(label,fixture,True,frames,buttons)
                again,s2=capture(label+'-original-again',fixture,False,frames,buttons)
                assert np.array_equal(before,after) and np.array_equal(before,again) and s0==s1==s2,label
                painted=image(work/(label+'-hd.png'))
                assert not np.array_equal(painted,before.repeat(10,0).repeat(10,1)),label+' did not use HD'
                states[label]=s1
                if a.stage_fixes and (label.startswith('stone-') or label=='margin'):
                    dump=work/(label+'.bin');command('dump',dump);raw=dump.read_bytes()
                    objects=[]
                    for n in range(128):
                        x,y,t,attr=raw[0x10200+n*4:0x10204+n*4]
                        x+=(raw[0x10400+n//4]>>(n%4*2)&1)*256
                        if x>=384:x-=512
                        if attr==0x2e and y<224:objects.append((x,y,t))
                    if label=='margin':
                        assert any(256<=x<299 and t==160 for x,y,t in objects),'Stone still pops at 4:3 edge'
                    else:
                        # OAM is emitted before the final camera update during
                        # the NMI; allow its one-pixel scroll rounding step.
                        stone=next(((x,y,t) for x,y,t in objects if abs(x+s1['camera_x']-672)<=1),None)
                        object_poses[label]=stone
                        if stone:
                            x,y,t=stone
                            receipt=json.loads((a.pack/'scene-receipt.json').read_text())
                            phase=next(f for f in receipt['objects'][0]['frames'] if f['frame']==t)
                            meta=json.loads((a.pack/'pack.json').read_text())
                            atlas,slot=meta['tiles'][phase['keys'][0]]
                            atlas_image=np.array(Image.open(a.pack/f'atlas_{atlas:03d}.png'))
                            row,col=divmod(slot,2048//80)
                            expected=atlas_image[row*80:(row+1)*80,col*80:(col+1)*80]
                            actual=painted[y*10:y*10+80,(margin+x)*10:(margin+x)*10+80]
                            opaque=expected[...,3]==255
                            assert opaque.sum()>100
                            assert np.mean(np.all(actual[opaque]==expected[...,:3][opaque],axis=1))>.98,(label,t,'OBJ tile not replaced')
            assert states['bridge-rotated']['player_y']<states['bridge']['player_y']-10,'Bridge did not rotate'
            first=image(work/'bridge-hd.png')[2080:2200,(margin+60)*10:(margin+90)*10]
            later=image(work/'water-phase-hd.png')[2080:2200,(margin+60)*10:(margin+90)*10]
            assert not np.array_equal(first,later),'HD water did not animate'
            if a.stage_fixes:
                assert [object_poses['stone-'+str(n)][2] for n in (1,20,40,55)]==[160,162,164,166],object_poses
                assert object_poses['stone-55'][1]>176 and object_poses['stone-80'] is None,object_poses
                gone=image(work/'stone-80-hd.png');x=672-states['stone-80']['camera_x']+margin
                native_gone=image(work/'stone-80-original.png');sky=native_gone[40,200]
                clear=np.all(native_gone[176:183,x:x+16]==sky,axis=2)
                # Simon is falling through this area too; test the exposed
                # backdrop, excluding his actual native sprite pixels.
                assert clear.sum()>20
                assert np.all(gone[1760:1830,x*10:(x+16)*10][clear.repeat(10,0).repeat(10,1)]==sky),'Static HD ghost remains after stone fell'
                # A conspicuous test water tint must affect the lake, never
                # the opaque foreground bank at world x615..623, y208..216.
                import shutil
                tint=work/'water-priority';shutil.copytree(a.pack,tint)
                meta=json.loads((tint/'pack.json').read_text())
                for region in meta['regions']:
                    if 'frame_period' in region:
                        f=tint/region['image'];rgba=np.array(Image.open(f));rgba[...,:3]=(255,0,255);Image.fromarray(rgba).save(f)
                command('hd','pack '+str(tint.resolve()));capture('water-tint',a.stage_fixes/'edge/state.sav',True)
                clean=image(work/'edge-hd.png');changed=image(work/'water-tint-hd.png')
                x=615-states['edge']['camera_x']+margin
                assert np.array_equal(clean[2080:2160,x*10:(x+8)*10],changed[2080:2160,x*10:(x+8)*10]),'Water overlays foreground bank'
                assert np.any(clean[2000:]!=changed[2000:]),'Water-priority probe missed lake'
                # Both surfaces must contribute below the waterline: tinting
                # water changes submerged rocks; tinting rocks changes water.
                # The dry bank above remains untouched by the water tint.
                rock_x=700-states['edge']['camera_x']+margin
                patch=(slice(2100,2160),slice(rock_x*10,(rock_x+8)*10))
                assert np.any(clean[patch]!=changed[patch]),'Water is behind submerged rocks'
                submerged=work/'submerged-rocks';shutil.copytree(a.pack,submerged)
                meta=json.loads((submerged/'pack.json').read_text())
                for region in meta['regions']:
                    if region.get('priority')==0x7000:
                        f=submerged/region['image'];rgba=np.array(Image.open(f));rgba[...,:3]=(0,255,255);Image.fromarray(rgba).save(f)
                command('hd','pack '+str(submerged.resolve()));capture('submerged-rocks',a.stage_fixes/'edge/state.sav',True)
                assert np.any(clean[patch]!=image(work/'submerged-rocks-hd.png')[patch]),'Water is opaque over submerged rocks'
                command('hd','pack '+str(a.pack.resolve()))
                shared=work/'shared-object-guard';shutil.copytree(a.pack,shared)
                meta=json.loads((shared/'pack.json').read_text());meta['scene_block']=9
                (shared/'pack.json').write_text(json.dumps(meta))
                command('hd','pack '+str(shared.resolve()));base,_=capture('shared-only',a.stage_fixes/'edge/state.sav',True)
                command('dump',work/'shared-only.bin');raw=(work/'shared-only.bin').read_bytes()
                allowed=np.zeros((2240,3420),bool)
                for n in range(128):
                    x,y,t,attr=raw[0x10200+n*4:0x10204+n*4]
                    if attr==0x2e and t in (160,162,164,166) and x<256 and y<208:
                        allowed[y*10:(y+16)*10,(margin+x)*10:(margin+x+16)*10]=True
                actual=image(work/'shared-only-hd.png');changed=np.any(actual!=base.repeat(10,0).repeat(10,1),axis=2)
                assert changed.any() and not changed[~allowed].any(),'Shared OBJ escaped its tile keys or drew scene planes in another block'
                command('hd','pack '+str(a.pack.resolve()))
                capture('extension',a.fixture,True)
                original=np.array(Image.open(sciv.ROOT/'artwork-local/stage01-user-v2/source/HD/03_HINTERGRUND_HD_LINKS_3390x1920.png'))
                expected=original[400:1400,110:540];actual=image(work/'extension-hd.png')[400:1400,:430]
                opaque=expected[...,3]==255
                assert opaque.sum()>10000 and np.array_equal(actual[opaque],expected[...,:3][opaque]),'Authored left background was reflected or wrapped'
                native=image(work/'edge-original.png')
                x=660-states['edge']['camera_x']+margin
                assert np.array_equal(native[191,x:x+8],native[190,x:x+8]),'Earth stripe at water transition'
                report['checks'].append('Stage 01: water behind bank, native stripe removed, authored left extension; live shared stone material in all four poses, falling/disappearance without static ghosts, fresh OAM entry beyond 4:3; shared object keys work outside scene without scene-plane leakage')
                report['object_poses']=object_poses
            report.update(checks=report['checks']+['User pack: original/HD/original state and native images identical at start, scroll and rotating bridge; HD water changes phase'],states=states,passed=True)
            (work/'report.json').write_text(json.dumps(report,indent=2));print('PASS:', '; '.join(report['checks']),flush=True)
        finally:
            if lua:lua.close()
            proc.terminate();proc.wait(timeout=10)


if __name__=='__main__':main()
