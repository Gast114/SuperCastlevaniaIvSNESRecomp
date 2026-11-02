"""Golden comparison against the pre-optimization renderer, including mixed alpha."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np
from PIL import Image
from enemy_workshop_native import ROOT, NativeSession, play


def run(pack, reference_exe):
    out=Path(tempfile.mkdtemp(prefix='tile-opacity-',dir=ROOT/'build-lua'));print(out,flush=True)
    # Private test copies only: replace atlas pixels with a diagnostic pattern
    # that includes opaque, translucent and invisible native cells in every tile.
    diagnostic=out/'diagnostic';shutil.copytree(pack/'a05',diagnostic)
    meta=json.loads((diagnostic/'pack.json').read_text())
    size=meta['tile_size'];per=meta['atlas_size']//size
    atlases={}
    for index,slot in meta['tiles'].values():
        if index not in atlases:atlases[index]=np.array(Image.open(diagnostic/f'atlas_{index:03d}.png').convert('RGBA'))
        y,x=divmod(slot,per);yy,xx=np.indices((size,size))
        tile=atlases[index][y*size:(y+1)*size,x*size:(x+1)*size]
        tile[:,:,0]=(xx*19+yy*3)%256;tile[:,:,1]=(yy*23+xx*7)%256;tile[:,:,2]=107
        tile[:,:,3]=np.where((xx//4)%3==0,255,np.where((xx//4)%3==1,(xx%4)*50+25,0)).astype(np.uint8)
    for index,data in atlases.items():Image.fromarray(data).save(diagnostic/f'atlas_{index:03d}.png')
    old=out/'reference-build';old.mkdir();shutil.copy2(reference_exe,old/'SuperCastlevaniaIvSNESRecomp.exe')
    results=[]
    for name,build in [('reference',old),('optimized',ROOT/'build-lua')]:
        s=NativeSession(build=build,folder=out/name);samples=[]
        try:
            s.start(ROOT/'build-play/game/saves/save4.sav');s.command('enemy','workshop off')
            s.command('hd','pack '+str(diagnostic));s.command('hd','on')
            for scale in (2,4,6):
                s.command('hd','scale '+str(scale))
                for frames,buttons in [(1,()),(35,('Right','Y'))]:
                    s.command('loadfile',ROOT/'build-play/game/saves/save4.sav');play.advance(s.lua,frames,buttons)
                    file=out/f'{name}-{scale}-{frames}.png';s.command('hdshot',file)
                    samples.append(hashlib.sha256(np.array(Image.open(file)).tobytes()).hexdigest())
        finally:s.close()
        results.append(samples)
    assert results[0]==results[1],'Opaque/mixed/transparent or flipped HD texels changed'
    (out/'report.json').write_text(json.dumps(dict(passed=True,matching_captures=len(results[0]),scales=[2,4,6],alpha=['opaque','mixed','transparent']),indent=2))
    print('PASS: six HD captures pixel-identical to the reference renderer',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pack',type=Path,required=True);p.add_argument('--reference-exe',type=Path,required=True)
    a=p.parse_args();run(a.pack.resolve(),a.reference_exe.resolve())
