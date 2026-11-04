"""Import complete artist planes and explicitly identified gameplay motifs.

The prior collection supplies backgrounds, native water phases and OBJ art.
No wall texture is inferred, sampled into tiles or replaced by palette.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import shutil
import sys
import numpy as np
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from level_assets import Assets
from hd_common import load_pack
from hd_preview import fnv_key
from hd_tiles import write_pack

SCALE=4
DENSITY=129/32
LEFT_RESERVE=174
WIDTHS={'A03':1280,'A04':1024,'A05':768}
BLOCK_QUAD=(0x2801,0x2802,0x2803,0x2804)
JUNCTION_QUAD=(0x2801,0x2802,0x2805,0x2804)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rgba(path):
    with Image.open(path) as im:
        if im.mode!='RGBA':raise ValueError(f'{path}: RGBA PNG required')
        return im.copy()


def tile_indices(assets,word,base=8192):
    at=base+(word&1023)*16;rows=[]
    for y in range(8):
        a,b=assets.vram[at+y],assets.vram[at+y+8]
        rows.append([(a>>bit&1)|(a>>(bit+8)&1)<<1|(b>>bit&1)<<2|(b>>(bit+8)&1)<<3 for bit in range(7,-1,-1)])
    result=np.array(rows,np.uint8)
    if word&0x4000:result=result[:,::-1]
    if word&0x8000:result=result[::-1]
    return result


def normalize(plane):
    ratio=SCALE/DENSITY
    size=(round(plane.width*ratio),round(plane.height*ratio))
    return plane.resize(size,Image.Resampling.LANCZOS),round(-LEFT_RESERVE*ratio),0


def grid_asset(source,spec,native_size):
    """Explicit source density is independent from the fixed gameplay footprint.

    8x source motifs are retained on disk and downsampled once for this 4x pack.
    A future mixed-density renderer can use the same footprint/anchor metadata.
    """
    density=spec['source_scale']
    if type(density) is not int or density not in (4,8) or spec['native_size']!=list(native_size):
        raise ValueError('Invalid explicit asset density or native footprint')
    relative=Path(spec['image'])
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Grid image must stay inside source folder')
    path=(source/relative).resolve()
    if source not in path.parents:raise ValueError('Grid image escapes source folder')
    image=rgba(path)
    if image.size!=tuple(n*density for n in native_size):
        raise ValueError(f'{path}: expected exact {density}x canvas for {native_size}')
    target=tuple(n*SCALE for n in native_size)
    return path,image if image.size==target else image.resize(target,Image.Resampling.LANCZOS)


def flip(im,flags):
    if flags&0x4000:im=ImageOps.mirror(im)
    if flags&0x8000:im=ImageOps.flip(im)
    return im


def transformed_quad(quad,flags):
    a=np.array(quad,np.uint16).reshape(2,2)
    if flags&0x4000:a=a[:,::-1]
    if flags&0x8000:a=a[::-1]
    return tuple(int(w)^flags for w in a.flat)


def stamp_objects(base,gx,gy,assets,motifs):
    """Whole blocks, individual steps and exact partial block patterns only."""
    room=assets.import_room()
    words=np.array(room['layers']['front'],np.uint16).reshape(32,room['width'])
    covered=np.zeros(words.shape,bool)
    result=base.copy();allowed=np.zeros((base.height,base.width),bool);placements=[]
    block=motifs['block'].resize((64,64),Image.Resampling.LANCZOS)
    right=motifs['junction_right'].resize((64,64),Image.Resampling.LANCZOS)
    left=motifs['junction_left'].resize((64,64),Image.Resampling.LANCZOS)
    step_right=motifs['step_right'].resize((32,32),Image.Resampling.LANCZOS)
    step_left=motifs['step_left'].resize((32,32),Image.Resampling.LANCZOS)

    def put(im,x,y,role,signature):
        px,py=x*4-gx,y*4-gy
        if px<0 or py<0 or px+im.width>base.width or py+im.height>base.height:
            raise ValueError('Motif outside supplied complete plane')
        allowed[py:py+im.height,px:px+im.width]|=np.array(im)[:,:,3]>0
        result.alpha_composite(im,(px,py))
        placements.append(dict(x=x,y=y,role=role,signature=signature,width=im.width,height=im.height))

    # Match an entire original quartet. Similar colours elsewhere confer no match.
    patterns={}
    for flags in (0,0x4000):
        patterns[transformed_quad(BLOCK_QUAD,flags)]=(flip(block,flags),'block')
        patterns[transformed_quad(JUNCTION_QUAD,flags)]=(left if flags else right,'block-stair-junction')
    for y in range(0,28,2):
        for x in range(0,room['width'],2):
            key=tuple(int(w) for w in words[y:y+2,x:x+2].flat)
            if key not in patterns:continue
            art,role=patterns[key];put(art,x*8,y*8,role,list(key));covered[y:y+2,x:x+2]=True

    partial_quadrants={1:(0,0),2:(1,0),3:(0,1),4:(1,1),6:(1,0),8:(1,0),9:(1,1),131:(1,1)}
    for y in range(28):
        for x in range(room['width']):
            if covered[y,x]:continue
            word=int(words[y,x]);ident=word&1023;flags=word&0xc000
            if word>>10&7!=2:continue
            if ident==14:
                im=flip(step_right,flags);role='stair-step-right'
            elif ident==15:
                # Retail left steps use a horizontally flipped tile 15.
                im=flip(ImageOps.mirror(step_left),flags);role='stair-step-left'
            elif ident==5:
                im=flip(right.crop((0,32,32,64)),flags);role='junction-corner'
            elif ident in partial_quadrants:
                qx,qy=partial_quadrants[ident]
                im=flip(block.crop((qx*32,qy*32,qx*32+32,qy*32+32)),flags)
                if ident in (6,8,9,131):
                    # These exact known mixed tiles include original brick
                    # indices 3/4/5. Leave those pixels on the complete wall.
                    mask=~np.isin(tile_indices(assets,word),[0,3,4,5])
                    a=np.array(im);a[:,:,3]*=mask.repeat(4,0).repeat(4,1);im=Image.fromarray(a)
                role='partial-block-face'
            else:continue
            put(im,x*8,y*8,role,[word]);covered[y,x]=True

    old,new=np.array(base),np.array(result)
    assert np.array_equal(old[~allowed],new[~allowed]),'Wall pixels changed outside sprite alpha'
    report=dict(placements=placements,counts=dict(collections.Counter(v['role'] for v in placements)),
                changed_pixels=int(np.count_nonzero(np.any(old!=new,axis=2))),walls_outside_object_alpha_exact=True)
    return result,allowed,report


def build(source,prior,output,audit):
    source,prior,output,audit=[Path(p).resolve() for p in (source,prior,output,audit)]
    if output.exists() or audit.exists():raise FileExistsError('Use new output and audit directories')
    audit.mkdir(parents=True);receipts=[]
    def remember(path):
        path=Path(path)
        receipts.append(dict(source=str(path),sha256=sha(path),backup_relative_path=path.relative_to(source).as_posix()))
        return path
    grid_path=source/'raster.json'
    grid=None
    if grid_path.exists():
        grid=json.loads(remember(grid_path).read_text(encoding='utf-8'))
        if grid.get('version')!=1 or grid.get('kind')!='registered-stage01-grid' or grid.get('export_scale')!=4:
            raise ValueError('Unsupported registered grid manifest')
    shared=source/'HD/Gemeinsame-Teile'
    paths={'block':'Stein-01.png','step_right':'Stufe-Rechts.png','step_left':'Stufe-Links.png',
           'junction_right':'Block-Treppe-Rechts.png','junction_left':'Block-Treppe-Links.png'}
    motifs={}
    for key,name in paths.items():
        if grid:
            spec=grid['motifs'][name]
            if spec.get('anchor_native')!=[0,0]:raise ValueError('Gameplay motifs require top-left anchor')
            size=(16,16) if key.startswith('junction') or key=='block' else (8,8)
            path,motifs[key]=grid_asset(source,spec,size);remember(path)
        else:motifs[key]=rgba(remember(shared/name))
    mirrored=np.array_equal(np.array(motifs['junction_right']),np.array(motifs['junction_left']))
    if mirrored:
        # Human authorization 04.11: mirror one direction of the duplicate pair.
        motifs['junction_left']=ImageOps.mirror(motifs['junction_right'])
    for key,im in motifs.items():
        expected=((64,64) if key.startswith('junction') or key=='block' else (32,32)) if grid else ((65,65) if key.startswith('junction') or key=='block' else (32,33))
        if im.size!=expected:raise ValueError(f'{key}: measured authoring size {expected} required')
    collection=json.loads((prior/'pack.json').read_text())
    if not {'entrance','a02','a03','a04','a05'}<=set(collection['scenes']):
        raise ValueError('Prior collection must contain the verified backgrounds of all five sections')
    before={str(p.relative_to(prior)):sha(p) for p in prior.rglob('*') if p.is_file()}
    shutil.copytree(prior,output)
    report={'junction_left_mirrored_from_right':mirrored,'registered_grid':bool(grid),'stages':{}}
    for stage in ('A03','A04','A05'):
        if grid:
            spec=grid['planes'][stage]
            if spec.get('origin_native')!=[-43,0]:raise ValueError('Unexpected registered plane origin')
            src,base=grid_asset(source,spec,(WIDTHS[stage]+86,224));remember(src)
            plane=rgba(src);gx,gy=-172,0
        else:
            src=remember(source/stage/'HD/Spielebene.png');plane=rgba(src)
            if abs(plane.width-(WIDTHS[stage]*DENSITY+2*LEFT_RESERVE))>2 or plane.height not in (903,904):
                raise ValueError(f'{stage}: unexpected cropped canvas; registration needs review')
            base,gx,gy=normalize(plane)
        a=Assets(ROOT/'artwork-local/level-editor/rooms'/f'{int(stage[1:])-1:02d}')
        # All three artist planes need the explicit gameplay blocks and steps.
        # A complete wall PNG does not imply that these separate motifs are baked in.
        painted,mask,detail=stamp_objects(base,gx,gy,a,motifs)
        base.save(audit/(stage+'-normalized-source.png'));painted.save(audit/(stage+'-complete.png'))
        Image.fromarray(mask.astype(np.uint8)*255).save(audit/(stage+'-object-mask.png'))

        folder=output/stage.lower();meta=json.loads((folder/'pack.json').read_text())
        backgrounds=[r for r in meta['regions'] if r['layer']!=0]
        # Remove ALL inferred foreground tile replacements. Keep only real OBJ art.
        _,_,old_tiles=load_pack(folder);keep=set(meta.get('shared_objects',[]))
        for cy in range(2):
            for cx in range(2):
                px=tile_indices(a,170+cx+cy*16,0x6000).ravel().tolist()
                keep.add(fnv_key(4,px,list(a.colors[240:256])))
        write_pack({k:old_tiles[k] for k in keep},folder,4)
        atlas=json.loads((folder/'pack.json').read_text())
        meta['tiles']=atlas['tiles'];meta['requires']=['scene-regions-v1','shared-objects-v1']
        px,py=gx%4,gy%4
        canvas=Image.new('RGBA',((px+painted.width+3)//4*4,(py+painted.height+3)//4*4))
        canvas.paste(painted,(px,py));regions=[]
        for x in range(0,canvas.width,4096):
            name=f'foreground_{x//4096:02d}.png'
            canvas.crop((x,0,min(canvas.width,x+4096),canvas.height)).save(folder/name)
            regions.append(dict(image=name,layer=0,x=gx//4+x//4,y=gy//4,coordinates='world',wrap_x=0,wrap_y=0,modes=[1]))
        meta['regions']=regions+backgrounds
        (folder/'pack.json').write_text(json.dumps(meta,indent=2))
        assert all(sha(folder/r['image'])==sha(prior/stage.lower()/r['image']) for r in backgrounds)
        report['stages'][stage]=dict(source_size=list(plane.size),registered_origin_hd=[gx,gy],normalized_size=list(base.size),
                                  foreground_chunks=len(regions),background_images_unchanged=True,foreground_tile_replacements=0,**detail)
    assert all(sha(p['source'])==p['sha256'] for p in receipts),'Source changed during import'
    assert before=={str(p.relative_to(prior)):sha(p) for p in prior.rglob('*') if p.is_file()},'Prior pack changed'
    collection['name']='Stage 01 HD: '+('exact 4x grid, ' if grid else '')+'complete artist planes and explicit gameplay motifs'
    (output/'pack.json').write_text(json.dumps(collection,indent=2))
    receipt=dict(art_scale=4,presentation_scale=4,sources=receipts,builder_sha256=sha(__file__),preserved_existing_collection=str(prior),
                 prior_sha256=before,report=report,source_files_unchanged=True)
    (output/'import.json').write_text(json.dumps(receipt,indent=2));(audit/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(output=str(output),mirrored_left=mirrored,stages={s:v['counts'] for s,v in report['stages'].items()})))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','prior','out','audit'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();build(a.source,a.prior,a.out,a.audit)
