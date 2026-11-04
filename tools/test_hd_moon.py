"""Verify the A01 HD moon and constrain live changes to its native OBJ bounds."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile

import numpy as np
from PIL import Image
from enemy_workshop_native import ROOT, NativeSession, play

sys.path.insert(0, str(ROOT/'tools/hd'))
from hd_common import load_pack
from build_stage01_later import Assets, tile_indices
from hd_preview import fnv_key


def check(pack, prior, a01):
    work=Path(tempfile.mkdtemp(prefix='hd-moon-',dir=ROOT/'build-lua'))
    print(work,flush=True)
    # The A01 PNG has a measured 20px transparent border, not a larger moon.
    with Image.open(a01) as source:
        assert source.size==(190,190) and source.getbbox()==(20,20,170,170)
        golden=Image.new('RGBA',(64,64))
        golden.paste(source.crop((20,20,170,170)).resize((60,60),Image.Resampling.LANCZOS),(0,0))
    for stage,index in [('a03',2),('a04',3),('a05',4)]:
        _,_,tiles=load_pack(pack/stage);_,_,before=load_pack(prior/stage)
        a=Assets(ROOT/'artwork-local/level-editor/rooms'/f'{index:02d}')
        assembled=Image.new('RGBA',(64,64));keys=set()
        for y in range(2):
            for x in range(2):
                px=tile_indices(a,170+x+y*16,0x6000).ravel().tolist()
                key=fnv_key(4,px,list(a.colors[240:256]));keys.add(key)
                assembled.paste(Image.fromarray(tiles[key]),(x*32,y*32))
        assert np.array_equal(np.array(assembled),np.array(golden)),stage+' differs from A01 moon'
        assert set(tiles)==set(before)
        assert all(np.array_equal(v,before[k]) for k,v in tiles.items() if k not in keys)
    changed=[]
    for p in prior.rglob('*'):
        if p.is_file() and hashlib.sha256(p.read_bytes()).digest()!=hashlib.sha256((pack/p.relative_to(prior)).read_bytes()).digest():
            changed.append(p.relative_to(prior).as_posix())
    assert set(changed)=={'import.json',*(f'{stage}/atlas_000.png' for stage in ('a03','a04','a05'))},changed
    session=NativeSession(folder=work/'game');cases=[]
    try:
        session.start(ROOT/'build-play/game/saves/save2.sav')
        session.command('enemy','workshop off');session.command('hd','on');session.command('hd','scale 4')
        # Isolate native OBJs so a wall in the saved camera view cannot hide
        # the moon under test. This affects only this private test session.
        session.command('layers',16)
        for stage,slot in [('A03',2),('A04',3),('A05',4)]:
            for frames,buttons in [(1,()),(60,('Right',))]:
                captures=[];native=[]
                for label,path in [('old',prior),('new',pack)]:
                    session.command('hd','pack '+str(path))
                    session.command('loadfile',ROOT/f'build-play/game/saves/save{slot}.sav')
                    play.advance(session.lua,frames,buttons)
                    hd=work/f'{stage}-{frames}-{label}.png';nat=work/f'{stage}-{frames}-{label}-native.png'
                    session.command('hdshot',hd);session.command('screenshot',nat)
                    captures.append(np.array(Image.open(hd).convert('RGB')))
                    native.append(np.array(Image.open(nat).convert('RGB')))
                assert np.array_equal(*native),stage+' native image changed'
                dump=work/'video.bin';session.command('dump',dump);data=dump.read_bytes()
                oam=struct.unpack('<256H',data[0x10200:0x10400]);high=data[0x10400:0x10420]
                bounds=[]
                for i in range(128):
                    w0,w1=oam[i*2:i*2+2]
                    if w1&255!=170 or w1>>9&7!=7:continue
                    hi=high[i//4]>>((i%4)*2)&3
                    x=(w0&255)|((hi&1)<<8);x=x-512 if x>=256 else x;y=w0>>8
                    if 0<=y<224 and -16<x<256:bounds.append((x,y))
                assert len(bounds)==1,(stage,bounds)
                x,y=bounds[0];margin=captures[0].shape[1]//4//2-128
                allowed=np.zeros(captures[0].shape[:2],bool)
                # One native row of allowance covers the PPU field's row origin.
                allowed[max(0,(y-1)*4):min(896,(y+17)*4),(x+margin)*4:(x+margin+16)*4]=True
                diff=np.any(captures[0]!=captures[1],axis=2)
                assert int(diff.sum())>30,(stage,'HD moon not visible')
                assert not diff[~allowed].any(),(stage,'pixels outside moon changed')
                cases.append(dict(stage=stage,frames=frames,moon_changed_pixels=int(diff.sum()),native_unchanged=True,outside_moon_exact=True))
    finally:session.close()
    report=dict(passed=True,a01_moon_exact=True,changed_files=changed,cases=cases)
    (work/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('pack','prior','a01'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();check(a.pack.resolve(),a.prior.resolve(),a.a01.resolve())
