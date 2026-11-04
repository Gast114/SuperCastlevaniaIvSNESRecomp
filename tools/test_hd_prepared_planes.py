"""Verify complete user planes and localized motifs, including the live BG1 image."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import configparser

import numpy as np
from PIL import Image
from enemy_workshop_native import ROOT,NativeSession,play
sys.path.insert(0,str(ROOT/'tools/hd'))
from hd_common import load_pack


def check(pack,source,audit):
    work=Path(tempfile.mkdtemp(prefix='prepared-plane-',dir=ROOT/'build-lua'));print(work,flush=True)
    s=NativeSession(folder=work/'game');cfg=configparser.ConfigParser();cfg.read(s.folder/'config.ini');cfg['Graphics']['Widescreen']='1'
    with (s.folder/'config.ini').open('w') as f:cfg.write(f)
    report=[]
    try:
        s.start(ROOT/'build-play/game/saves/save2.sav');s.command('enemy','workshop off');s.command('hd','pack '+str(pack));s.command('hd','on');s.command('hd','scale 4');s.command('layers',1)
        for stage,slot in [('A03',2),('A04',3),('A05',4)]:
            im=Image.open(source/stage/'HD/Spielebene.png').convert('RGBA')
            normalized=np.array(im.resize((round(im.width*128/129),round(im.height*128/129)),Image.Resampling.LANCZOS))
            final=np.array(Image.open(audit/(stage+'-complete.png')).convert('RGBA'))
            mask=np.array(Image.open(audit/(stage+'-object-mask.png')))>0
            assert np.array_equal(final[~mask],normalized[~mask]),stage+' wall pixels altered'
            if stage=='A03':assert not mask.any() and np.array_equal(final,normalized),'A03 complete plane altered'
            meta=json.loads((pack/stage.lower()/'pack.json').read_text())
            regions=[r for r in meta['regions'] if r['layer']==0]
            assert not any(r.get('native_fallback',0) or r.get('overlay',0) for r in regions)
            x=min(r['x'] for r in regions);y=min(r['y'] for r in regions)
            width=max(r['x']+Image.open(pack/stage.lower()/r['image']).width//4 for r in regions)-x
            height=Image.open(pack/stage.lower()/regions[0]['image']).height
            registered=Image.new('RGBA',(width*4,height))
            for r in regions:registered.paste(Image.open(pack/stage.lower()/r['image']),((r['x']-x)*4,(r['y']-y)*4))
            assert np.array_equal(np.array(registered)[0:final.shape[0],3:3+final.shape[1]],final)
            # Only prior shared OBJ and moon keys may remain in this scene atlas.
            _,_,tiles=load_pack(pack/stage.lower());assert len(tiles)==len(set(meta['shared_objects']))+4
            s.command('loadfile',ROOT/f'build-play/game/saves/save{slot}.sav');play.advance(s.lua,1)
            ppu=json.loads(s.command('ppu'));path=work/(stage+'-bg1.png');s.command('hdshot',path)
            actual=np.array(Image.open(path).convert('RGB'));margin=actual.shape[1]//4//2-128
            h=ppu['layers'][0]['h'];v=ppu['layers'][0]['v'];v=v-1024 if v>=512 else v
            expected=np.array(registered.crop(((h-margin-x)*4,(v+1-y)*4,(h+256+margin-x)*4,(v+225-y)*4)))
            assert actual.shape[:2]==expected.shape[:2]
            expected=((expected[:,:,:3].astype(np.uint32)*expected[:,:,3,None]+127)//255).astype(np.uint8)
            changed=int(np.count_nonzero(np.any(actual!=expected,axis=2)))
            assert changed==0,(stage,'runtime BG1 differs from complete prepared plane',changed)
            report.append(dict(stage=stage,wall_pixels_exact=True,live_bg1_exact=True,sprite_pixels=int(mask.sum())))
    finally:s.close()
    (work/'report.json').write_text(json.dumps(dict(passed=True,cases=report),indent=2));print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['pack','source','audit']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();check(a.pack.resolve(),a.source.resolve(),a.audit.resolve())
