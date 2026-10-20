"""Import paired native/10x PNG poses using an actually captured Simon template.

The native silhouette identifies a complete pose, not reusable tiles. Artwork
is copied byte-for-byte; only the native preview sheet and mapping are built.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from PIL import Image


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--template',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    manifest=json.loads((a.template/'character.json').read_text())
    sheet=Image.open(a.template/'body.png').convert('RGBA')
    result=dict(manifest);result['name']='Simon HD preview';result['frames']=[]
    preview=Image.new('RGBA',sheet.size);receipt=[]
    for source in sorted(a.source.glob('*_HD_10x_*.png')):
        native=a.source/(source.name.split('_HD_10x_')[0]+'.png')
        sd=Image.open(native).convert('RGBA');hd=Image.open(source).convert('RGBA')
        if hd.size!=(sd.width*10,sd.height*10):raise ValueError(f'{source}: expected exact 10x dimensions')
        native_box=sd.getbbox()
        if not native_box:raise ValueError(f'{native}: empty reference')
        content=sd.crop(native_box);mask=np.array(content.getchannel('A'))>0;choices=[]
        for f in manifest['frames']:
            cell=f['cell'];tile=sheet.crop((cell%8*96,cell//8*96,cell%8*96+96,cell//8*96+96));box=tile.getbbox()
            if box and (box[2]-box[0],box[3]-box[1])==content.size:
                difference=int(np.sum(mask!=(np.array(tile.crop(box).getchannel('A'))>0)))
                choices.append((difference,f['id'],f,box,tile))
        choices.sort(key=lambda c:(c[0],c[1]))
        if not choices or choices[0][0]>mask.size*.01:raise ValueError(f'{native}: no sufficiently close captured native pose')
        if len(choices)>1 and choices[1][0]-choices[0][0]<mask.size*.02:raise ValueError(f'{native}: ambiguous mapping; capture an exact native reference')
        difference,_,frame,box,tile=choices[0];frame=dict(frame);frame['cell']=len(result['frames']);frame['label']=native.stem
        offset=[box[0]-native_box[0],box[1]-native_box[1]]
        if min(offset)<0 or offset[0]+sd.width>96 or offset[1]+sd.height>96:raise ValueError(f'{native}: reference padding exceeds the native 96x96 cell')
        frame['hd']={'image':source.name,'scale':10,'offset':offset}
        result['frames'].append(frame);c=frame['cell'];preview.paste(tile,(c%8*96,c//8*96))
        receipt.append({'native':str(native.resolve()),'image':str(source.resolve()),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                        'pose':frame['id'],'alpha_mismatches':difference,'native_pixels':mask.size,'offset':offset})
    if not result['frames']:raise ValueError('No *_HD_10x_*.png pose files found')
    if len({f['id'] for f in result['frames']})!=len(result['frames']):raise ValueError('Duplicate pose mapping')
    a.out.mkdir(parents=True,exist_ok=False)
    for r in receipt:shutil.copy2(r['image'],a.out/Path(r['image']).name)
    preview.save(a.out/'body.png')
    (a.out/'character.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    (a.out/'import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
