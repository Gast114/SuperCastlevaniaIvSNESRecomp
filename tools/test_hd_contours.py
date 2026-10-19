"""Offline proof for composing HD alpha BEFORE native visibility decisions.

Exercises the existing reference compositor, not the live PPU/presenter. Optional
--marker checks a real native scene and writes a diagnostic contour study. This
does not enable new game artwork, sprite stacking, windows or color math.
"""
import argparse
from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent/'hd'))
import hd_preview as preview


def check_composition():
    # BG1 above BG2, with a higher-priority sprite crossing both. The native
    # foreground only covers its left half; HD has a diagonal antialiased edge.
    scale = 10
    layers = {name: preview.layer_maps() for name in ('bg1','bg2','obj')}
    for name, tid in (('bg2',0),('bg1',1)):
        layer=layers[name]; layer['tid'][:8,:8]=tid
        yy,xx=np.indices((8,8)); layer['tx'][:8,:8]=xx; layer['ty'][:8,:8]=yy
    obj=layers['obj']; obj['tid'][3:5,:8]=2; obj['prio'][3:5,:8]=3
    back=np.full((80,80,4),(0,0,255,255),np.uint8)
    front=np.full((80,80,4),(255,0,0,0),np.uint8)
    yy,xx=np.indices((80,80)); alpha=np.clip((40+(yy-40)*.8-xx)*64+128,0,255).astype(np.uint8)
    front[...,3]=alpha
    sprite=np.full((80,80,4),(0,255,0,255),np.uint8)
    hd=preview.render([back,front,sprite],layers,scale,False,np.array([0,0,0]),15)
    expected=np.zeros((80,80,3),np.uint8)
    expected[...,0]=alpha; expected[...,2]=255-alpha
    expected[30:50]=(0,255,0)
    assert np.max(np.abs(hd[:80,:80].astype(int)-expected.astype(int)))<=1
    assert np.any(alpha[:,40:]>0), 'no extension outside native silhouette'
    assert np.any(alpha[:,:40]<255), 'no cutout exposing background'
    for flip in ('hf','vf'):
        layers['bg1'][flip][:8,:8]=True
        # Flip both native texel coordinates and subpixel orientation.
        coord='tx' if flip=='hf' else 'ty'
        layers['bg1'][coord][:8,:8]=7-layers['bg1'][coord][:8,:8]
        actual=preview.render([back,front,sprite],layers,scale,False,np.array([0,0,0]),15)
        target=expected[:,::-1].copy() if flip=='hf' else expected[::-1].copy()
        # The sprite does not move with the flipped background.
        flipped_alpha=alpha[:,::-1] if flip=='hf' else alpha[::-1]
        target[...,0]=flipped_alpha; target[...,1]=0; target[...,2]=255-flipped_alpha
        target[30:50]=(0,255,0)
        assert np.max(np.abs(actual[:80,:80].astype(int)-target.astype(int)))<=1
        layers['bg1'][flip][:8,:8]=False
        layers['bg1'][coord][:8,:8]=7-layers['bg1'][coord][:8,:8]
    print('PASS: subpixel alpha extends/cuts native edges, reveals underlying BG, respects sprite priority and flips')


def marker_study(marker, output):
    output.mkdir(parents=True,exist_ok=True)
    m=preview.Machine(marker); tiles=preview.Tiles(m,{},10)
    layers={f'bg{i+1}':preview.build_bg(m,tiles,i) for i in range(3)}
    layers['obj']=preview.build_obj(m,tiles)
    r=m.line(112); backdrop=np.array(preview.hd.rgb15(m.cgram[0]),np.float32)
    native=preview.render(tiles.native,layers,1,r['bgmode']&8,backdrop,r['inidisp']&15)
    actual=np.array(Image.open(marker/'screen.png').convert('RGB')); margin=(actual.shape[1]-256)//2
    assert np.array_equal(native,actual[:,margin:margin+256]), 'unsupported marker effects; native reference differs'
    # Pick a frequently used BG1 edge tile with both opaque and transparent pixels.
    candidates=[i for i,t in enumerate(tiles.native) if 0<np.count_nonzero(t[...,3])<64]
    chosen=max(candidates,key=lambda i:np.count_nonzero(layers['bg1']['tid']==i))
    test=tiles.hd[chosen].copy(); yy,xx=np.indices((80,80))
    test[...,:3]=(30,220,220); test[...,3]=np.clip((xx-yy)*64+128,0,255).astype(np.uint8)
    tiles.hd[chosen]=test
    hd=preview.render(tiles.hd,layers,10,r['bgmode']&8,backdrop,r['inidisp']&15)
    assert np.any(hd!=native.repeat(10,0).repeat(10,1))
    Image.fromarray(native).save(output/'native.png')
    Image.fromarray(hd).save(output/'contour-study.png')
    print(f'PASS: native marker reconstructed exactly; offline cyan contour diagnostic in {output}')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--marker',type=Path)
    p.add_argument('--out',type=Path,default=preview.hd.ROOT/'build-audit/hd-contours')
    args=p.parse_args(); check_composition()
    if args.marker: marker_study(args.marker,args.out)


if __name__=='__main__': main()
