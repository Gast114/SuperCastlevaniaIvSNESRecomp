"""Check native workshop motion, a live single-part edit and guest-state purity."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import numpy as np
from PIL import Image,ImageFilter
from enemy_workshop_native import NativeSession

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,default=ROOT/'artwork-local/enemy-hd-2026-10-23/a02-enemy-probe/saves/save9.sav')
    args=parser.parse_args()
    parent=ROOT/'artwork-local/enemy-workshop-review';parent.mkdir(exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='live-render-',dir=parent));report={'passed':False,'native_full_playthrough':False,'checks':[]}
    session=NativeSession(folder=work/'game')
    try:
        session.start(args.fixture)
        entry=next(e for e in session.catalog if e['type']==18 and e['room']==1)
        session.spawn(entry)
        recordings=[]
        for _ in range(36):recordings.append(session.step(1))
        # Like the workshop's Collect sequence, begin each action from its
        # fresh native spawn. Walking into Simon first can cause retail hit
        # pauses and interrupt a short fixed-duration throw observation.
        session.spawn(entry)
        session.action('Werfen')
        for _ in range(70):recordings.append(session.step(1))
        types={a['type'] for shot in recordings for a in shot['actors']}
        poses={a['pose'] for shot in recordings for a in shot['actors'] if a['type']==18}
        assert 2 in types and any(p in poses for p in (0x8b1b,0x8b30,0x8b4d)),(types,poses)
        session.command('enemy','flush')
        (work/'native-motion.json').write_text(json.dumps(recordings))
        report['checks'].append('Native skeleton walk/throw AI produces actual bone projectile actors')
        session.spawn(entry);session.step(8)
        session.command('save',8);fixture=session.folder/'saves/save8.sav'
        session.command('enemy','flush')
        data=json.loads((session.references/'enemies.json').read_text())
        # In the true placement/camera context the lower-leg component is
        # completely behind the foreground ground. Use the torso, which has
        # both exposed texels and texels covered by the fence in this scene.
        component_index=2
        parts=[f for f in data['frames'] if f['actor_type']==18 and f['id'].endswith(f'__teil-{component_index}')]
        assert len(parts)>=2
        pack=session.folder/'enemy_packs/part-diagnostic';pack.mkdir();mapped=[]
        for frame in parts:
            with Image.open(session.references/frame['reference']) as native:
                image=native.convert('RGBA').resize((387,387),Image.Resampling.NEAREST)
            alpha=image.getchannel('A');image.paste((255,0,255,255),(0,0,image.width,image.height));image.putalpha(alpha);image.save(pack/frame['reference'])
            mapped.append(dict(frame,image=frame['reference']))
        (pack/'enemies.json').write_text(json.dumps({'version':1,'frames':mapped}))
        def ram_hash():
            full=bytearray()
            for a in range(0,0x20000,128):
                text=session.lua.eval(f'local t={{}} for i={a},{a+127} do t[#t+1]=mainmemory.read_u8(i) end return table.concat(t,",")')['values'][0]
                full.extend(map(int,text.split(',')))
            return hashlib.sha256(full).hexdigest()
        samples=[]
        for custom in (False,True):
            session.command('enemy','pack part-diagnostic' if custom else 'off')
            session.command('hd','scale 10');session.command('hd','on' if custom else 'off')
            # The first restored field may still contain the save's queued
            # OAM from before the actor update. Let the exact matcher settle.
            session.command('loadfile',fixture);snapshot=session.step(3)
            label='part' if custom else 'native'
            session.command('screenshot',work/(label+'.png'));session.command('dump',work/(label+'-video.bin'))
            if custom:session.command('hdshot',work/'part-hd.png')
            samples.append({'ram':ram_hash(),'video':hashlib.sha256((work/(label+'-video.bin')).read_bytes()).hexdigest()})
        assert samples[0]==samples[1],samples
        native=np.array(Image.open(work/'native.png').convert('RGB'));changed=np.array(Image.open(work/'part.png').convert('RGB'))
        actor=next(a for a in snapshot['actors'] if a['type']==18);piece=next(p for p in actor['parts'] if p['index']==component_index)
        reference=Image.open(session.references/(piece['id']+'.png')).convert('RGBA')
        if actor['flip']&1:reference=reference.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if actor['flip']&2:reference=reference.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        allowed=Image.new('L',(256,224));allowed.paste(reference.getchannel('A'),(actor['x']-actor['anchor'],actor['y']-actor['anchor']))
        allowed=np.array(allowed.filter(ImageFilter.MaxFilter(3)))>0
        difference=np.any(native!=changed,axis=2)
        assert int(difference.sum())>5,'No live native-sized component replacement'
        assert not np.any(difference&~allowed),'A component edit changed its untouched native neighbours/background'
        hd=np.array(Image.open(work/'part-hd.png').convert('RGB'))
        assert hd.shape==(2240,2560,3),hd.shape
        magenta=(hd[:,:,0]>230)&(hd[:,:,1]<20)&(hd[:,:,2]>230)
        assert int(magenta.sum())>500,'Fine source part was not sampled by HD compositor'
        # Independently isolate native backgrounds at the very same field.
        # Opaque source texels which remain equal to those backgrounds prove
        # the component still goes behind the fence, not above the scene.
        session.command('enemy','off');session.command('hd','off');session.command('layers','15')
        session.command('loadfile',fixture);session.step(3)
        session.command('screenshot',work/'background-only.png')
        backgrounds=np.array(Image.open(work/'background-only.png').convert('RGB'))
        raw_coverage=Image.new('L',(256,224));raw_coverage.paste(reference.getchannel('A'),(actor['x']-actor['anchor'],actor['y']-actor['anchor']))
        hidden=(np.array(raw_coverage)>128)&~difference&np.all(native==backgrounds,axis=2)
        assert int(hidden.sum())>=3,'No independent evidence of native fence occlusion'
        report['checks']+=['One native ROM component visibly changes while untouched neighbouring parts/background remain exact',
                           '387px single-part artwork renders through real winner-aware HD composition',
                           'Opaque component texels behind the native fence remain equal to independently rendered backgrounds',
                           'Full 128KiB WRAM plus VRAM/CGRAM/OAM hashes match with and without part artwork']
        report.update(passed=True,native_actor_types=sorted(types),native_actor_poses=sorted(poses),component_id=piece['id'],changed_native_pixels=int(difference.sum()),magenta_hd_pixels=int(magenta.sum()),native_fence_occluded_source_pixels=int(hidden.sum()),identity=samples[0])
        print(work);print('PASS:','; '.join(report['checks']))
    finally:
        (work/'report.json').write_text(json.dumps(report,indent=2)+'\n');session.close()

if __name__=='__main__':main()
