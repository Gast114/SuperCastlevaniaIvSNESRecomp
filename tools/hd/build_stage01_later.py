"""Register finished A03/A04/A05 artwork; preserve source files and existing scenes.

PhotoCraft exports private PSD copies. Background pieces follow decoded native
map motifs; palette-driven water uses native tile keys, not a host clock.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from level_assets import Assets
from hd_preview import fnv_key
from hd_tiles import write_pack
from hd_common import load_pack

SCALE = 4
DENSITY = 129 / 32
ORIGINS = {'A03': (346, 346), 'A04': (605, 354), 'A05': (1065, 339)}
WIDTHS = {'A03': 1280, 'A04': 1024, 'A05': 768}
# Palette 2 contains the framed blocks and diagonal steps; palette 4 the grey
# structural trim. Keep partial faces and destructible stone tied to native tiles.
GROUPS = {
    'A03': [(1, 4, 608, 95, 97), (2, 1, 268, 97, 0)],
    'A04': [(1, 2, 417, 63, 161), (2, 3, 508, 33, 128),
            (3, 3, 508, 16, 112), (4, 2, 326, 112, 0)],
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rgba(p):
    with Image.open(p) as im:
        return im.convert('RGBA')


def joined(paths):
    parts = [rgba(p) for p in paths]
    assert len({p.height for p in parts}) == 1
    im = Image.new('RGBA', (sum(p.width for p in parts), parts[0].height))
    x = 0
    for part in parts:
        im.paste(part, (x, 0)); x += part.width
    return im


def leaves(items):
    for layer in items:
        yield layer
        yield from leaves(layer.get('children', []))


def photo_export(source, audit, stage, hidden):
    cli = r'C:\Program Files\PhotoCraft\photocraft-cli.exe'
    info = json.loads(subprocess.check_output([cli, 'info', str(source)]))
    args = [cli, 'run', str(source)]
    for layer in leaves(info['layers']):
        if layer['id'] in hidden and layer['visible']:
            args += ['--cmd', 'layer.hideLayers', '--params', json.dumps({'layer': layer['id']})]
    target = audit / (stage + '-foreground.png')
    log = subprocess.check_output(args + ['--out', str(target)])
    (audit / (stage + '-export.jsonl')).write_bytes(log)
    return rgba(target)


def native_map(assets):
    out = Image.new('RGBA', (512, 256))
    words = np.zeros((32, 64), np.uint16)
    for y in range(32):
        for x in range(64):
            at = assets.meta['ppu']['layers'][1]['map'] + (x // 32) * 1024 + y * 32 + x % 32
            word = assets.vram[at & 32767]
            words[y, x] = word
            out.paste(assets.tile(word, 'back'), (x*8, y*8))
    a = np.array(out)
    a[a[:, :, 3] == 0] = (0, 0, 0, 255)
    return a, words


def strip_to_map(original, painted, native, width, height, y, extra_masks=()):
    """Place native 32px motifs from a source sheet, tolerating its repeat order.

    Larger coherent strips are preferred; only a differing native motif is split.
    The HD pixels come from the corresponding original-source coordinates.
    """
    a = np.array(original.convert('RGB'))
    xx = np.minimum(((np.arange(width)+.5)*a.shape[1]/width).astype(int), a.shape[1]-1)
    yy = np.minimum(((np.arange(height)+.5)*a.shape[0]/height).astype(int), a.shape[0]-1)
    source = (a[yy[:, None], xx[None, :]] >> 3).astype(np.float32)
    target = (native[y:y+height, :, :3] >> 3).astype(np.float32)
    art = np.array(painted.resize((width*SCALE, height*SCALE), Image.Resampling.LANCZOS))
    masks = [np.array(im.resize((width*SCALE, height*SCALE), Image.Resampling.NEAREST)) for im in extra_masks]
    result = np.zeros((height*SCALE, 512*SCALE, 4), np.uint8)
    mask_results = [np.zeros_like(result) for _ in masks]
    placements = []

    def block(x, size):
        chunk = target[:, x:x+size]
        values = cv2.matchTemplate(source, chunk, cv2.TM_SQDIFF)
        _, _, pos, _ = cv2.minMaxLoc(values)
        sx = pos[0]
        error = float(np.mean((source[:, sx:sx+size]-chunk)**2))
        if size > 8 and error > .30:
            block(x, size//2); block(x+size//2, size//2)
            return
        result[:, x*SCALE:(x+size)*SCALE] = art[:, sx*SCALE:(sx+size)*SCALE]
        for out, mask in zip(mask_results, masks):
            out[:, x*SCALE:(x+size)*SCALE] = mask[:, sx*SCALE:(sx+size)*SCALE]
        placements.append(dict(x=x, width=size, source_x=sx, original_colour_mse=error))

    for x in range(0, 512, 32):
        block(x, 32)
    return result, mask_results, placements


def build(source, prior, output, audit):
    source, prior, output, audit = map(lambda p: Path(p).resolve(), (source, prior, output, audit))
    if output.exists() or audit.exists():
        raise FileExistsError('Use new output and audit directories')
    audit.mkdir(parents=True)
    receipts = []

    def remember(p):
        p = Path(p)
        item = dict(source=str(p.resolve()), sha256=sha(p), size=p.stat().st_size,
                    backup_relative_path=p.resolve().relative_to(source).as_posix())
        if item not in receipts: receipts.append(item)
        return p

    background_zip = remember(source / 'Hintergrund-HD-Workflow-2026-11-02/Stage01_A03_A04_HD.zip')
    backgrounds = audit / 'backgrounds'
    with zipfile.ZipFile(background_zip) as z:
        for name in z.namelist():
            p = Path(name)
            if len(p.parts) == 2 and p.parts[0] in ('A03', 'A04') and p.suffix == '.png':
                dst = backgrounds / p
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(z.read(name))
    assets = {}; rooms = {}; composites = {}; fg = {}; report = {}
    for stage in ('A03', 'A04', 'A05'):
        src = remember(source / stage / (stage+'.psd'))
        copy = audit / (stage+'-source.psd'); shutil.copy2(src, copy)
        assets[stage] = Assets(ROOT / 'artwork-local/level-editor/rooms' / f'{int(stage[1:])-1:02d}')
        rooms[stage] = assets[stage].import_room()
        if stage != 'A05':
            composites[stage] = photo_export(copy, audit, stage, {40, 43, 5} if stage == 'A03' else {2, 3})
            x, y = ORIGINS[stage]
            if stage == 'A03':
                core = composites[stage].crop((x, y, x+WIDTHS[stage]*DENSITY, y+903))
            else:
                # Source cut 03 starts 32 native pixels below the other cuts.
                # The PSD's large pixel layer is still SD; preserve only its
                # separately placed HD stones/stairs above the finished HD cuts.
                core = Image.new('RGBA', (4128, 903))
                for n, px, py in [(1,0,0),(2,1032,0),(3,2193,129),(4,3225,0)]:
                    piece = rgba(remember(source/stage/'HD'/f'A04_{n:02d}_HD_background.png'))
                    core.alpha_composite(piece,(px,py))
                core.alpha_composite(composites[stage].crop((x,y,x+4128,y+903)))
            fg[stage] = core.resize((WIDTHS[stage]*4, 896), Image.Resampling.LANCZOS)
        else:
            parts = [remember(source / stage / 'HD' / f'A05_{n:02d}_HD_background.png') for n in range(1, 5)]
            fg[stage] = joined(parts).resize((WIDTHS[stage]*4, 896), Image.Resampling.LANCZOS)

    # Native hashes identify reusable hand-painted gameplay stone/stair tiles.
    pool = {}; pool_scores = {}
    for stage in ('A03', 'A04'):
        room, a = rooms[stage], assets[stage]
        info = json.loads(subprocess.check_output([r'C:\Program Files\PhotoCraft\photocraft-cli.exe', 'info', str(audit/(stage+'-source.psd'))]))
        # Prefer actual hand-placed stone/step layers over generative fill that
        # deliberately removed those motifs. Bounds are in original PSD pixels.
        placed = []
        def manual_bounds(items, inside_steps=False):
            for layer in items:
                steps=inside_steps or layer['name'].startswith('Treppe')
                if layer.get('children'):
                    manual_bounds(layer['children'],steps)
                elif layer.get('visible') and layer.get('bounds') and (steps or layer['name'].startswith(('Stein','Layer ')) and layer['id']!=3):
                    placed.append(layer['bounds'])
        manual_bounds(info['layers'])
        ox,oy=ORIGINS[stage]
        for yy in range(28):
            for xx in range(room['width']):
                word = room['layers']['front'][yy*room['width']+xx]
                if word >> 10 & 7 not in (2,4) or not np.array(a.tile(word))[:,:,3].any(): continue
                canonical = word & 0x3fff
                cx,cy=ox+(xx*8+4)*DENSITY,oy+(yy*8+4)*DENSITY
                score=int(any(x<=cx<x+w and y<=cy<y+h for x,y,w,h in placed))
                if canonical in pool and score<=pool_scores[canonical]: continue
                tile = np.array(fg[stage].crop((xx*32, yy*32, xx*32+32, yy*32+32)))
                if word & 0x4000: tile = tile[:, ::-1]
                if word & 0x8000: tile = tile[::-1]
                # The native silhouette also handles all partial stair faces.
                mask=np.array(a.tile(canonical))[:,:,3].repeat(4,0).repeat(4,1)
                tile[:,:,3]=np.minimum(tile[:,:,3],mask)
                pool[canonical] = tile.copy()
                pool_scores[canonical]=score

    shutil.copytree(prior, output)
    collection = json.loads((output/'pack.json').read_text())
    assert collection['scenes'] == ['entrance', 'a02']
    entrance = json.loads((prior/'entrance/pack.json').read_text())
    _, _, entrance_tiles = load_pack(prior/'entrance')
    shared_keys=entrance.get('shared_objects',[])
    bg_cache = {}
    for stage in ('A03', 'A04', 'A05'):
        folder = output / stage.lower(); folder.mkdir()
        a, room = assets[stage], rooms[stage]
        original_fg = fg[stage].copy()
        core = np.array(original_fg)
        tiles = {}
        # Reuse the already installed crumbling-stone animation rather than
        # losing shared object HD when entering one of the newly authored rooms.
        for key in shared_keys:
            tiles[key]=np.array(Image.fromarray(entrance_tiles[key]).resize((32,32),Image.Resampling.LANCZOS))
        dynamic_cells = []
        for yy in range(28):
            for xx in range(room['width']):
                word = room['layers']['front'][yy*room['width']+xx]
                if word >> 10 & 7 not in (2,4) or not np.array(a.tile(word))[:,:,3].any(): continue
                canonical = word & 0x3fff
                tile = pool[canonical]
                address = (a.meta['ppu']['layers'][0]['tiles']+(word & 1023)*16)&32767
                # Decode canonical unflipped pixels for the native hash.
                pal_base=(word>>10&7)*16
                pal = list(a.colors[pal_base:pal_base+16])
                # Hash raw colour indices rather than reverse-matching colours.
                data = a.vram; px = []
                for row in range(8):
                    p01, p23 = data[(address+row)&32767], data[(address+row+8)&32767]
                    for bit in range(7, -1, -1):
                        px.append((p01>>bit&1)|(p01>>(bit+8)&1)<<1|(p23>>bit&1)<<2|(p23>>(bit+8)&1)<<3)
                key = fnv_key(4, px, pal)
                tiles.setdefault(key, tile)
                core[yy*32:yy*32+32, xx*32:xx*32+32] = 0
                dynamic_cells.append([xx*8, yy*8])

        # Moon: original OBJ remains responsible for position, visibility and priority.
        moon = rgba(backgrounds / ('A03' if stage == 'A05' else stage) / 'Mond_HD.png')
        assert moon.size == (60, 60)
        moon_canvas = Image.new('RGBA', (64, 64)); moon_canvas.paste(moon, (0, 0))
        for cy in range(2):
            for cx in range(2):
                addr = 0x6000+(170+cx+cy*16)*16
                px = []
                for row in range(8):
                    p01, p23 = a.vram[addr+row], a.vram[addr+row+8]
                    for bit in range(7, -1, -1):
                        px.append((p01>>bit&1)|(p01>>(bit+8)&1)<<1|(p23>>bit&1)<<2|(p23>>(bit+8)&1)<<3)
                tiles[fnv_key(4, px, list(a.colors[240:256]))] = np.array(moon_canvas.crop((cx*32, cy*32, cx*32+32, cy*32+32)))
        write_pack(tiles, folder, 4)
        meta = json.loads((folder/'pack.json').read_text())
        meta.update(scene_block=int(stage[1:])-1, native_maps=[0,4096], requires=['scene-regions-v1', 'native-fallback-v1'])
        meta['shared_objects']=shared_keys
        meta['requires'].append('shared-objects-v1')
        regions = []

        def emit(im, x, y, layer, **extra):
            # Work at 4x; pad only right/bottom, preserve exact subpixel placement.
            im = im.convert('RGBA')
            canvas = Image.new('RGBA', ((im.width+3)//4*4, (im.height+3)//4*4)); canvas.paste(im, (0, 0))
            for left in range(0, canvas.width, 4096):
                part = canvas.crop((left, 0, min(canvas.width,left+4096),canvas.height))
                name = f'region_{len(regions):02d}.png'; part.save(folder/name)
                regions.append(dict(image=name, layer=layer, x=x+left//4, y=y,
                                    coordinates='world' if layer==0 else 'map', wrap_x=0 if layer==0 else 512,
                                    wrap_y=0 if layer==0 else 512, modes=[1], **extra))

        # Keep artist-authored 16:9 margins, but never include PSD reference layers.
        lefts = list((source/stage/'HD/16x9').glob('*ERWEITERUNG_LINKS*.png'))
        rights = list((source/stage/'HD/16x9').glob('*ERWEITERUNG_RECHTS*.png'))
        if stage=='A03':
            left=composites[stage].crop((172,346,346,1249)).resize((172,896),Image.Resampling.LANCZOS)
            right=composites[stage].crop((5506,346,5680,1249)).resize((172,896),Image.Resampling.LANCZOS)
        else:
            left = rgba(remember(lefts[0])).resize((172,896),Image.Resampling.LANCZOS)
            right = rgba(remember(rights[0])).resize((172,896),Image.Resampling.LANCZOS)
        full = Image.new('RGBA',(core.shape[1]+344,896)); full.paste(left,(0,0));full.paste(Image.fromarray(core),(172,0));full.paste(right,(172+core.shape[1],0))
        emit(full,-43,0,0,native_fallback=1)

        source_stage = 'A03' if stage == 'A05' else stage
        if source_stage not in bg_cache:
            native, words = native_map(assets[source_stage])
            background = np.repeat(np.repeat(native,4,axis=0),4,axis=1)
            water_mask = np.zeros(background.shape[:2],bool)
            placements = []
            for group, count, nw, nh, y in GROUPS[source_stage]:
                names = [f'Hintergrund-{group:02d} ({n})' for n in range(1,count+1)] if count>1 else [f'Hintergrund-{group:02d}']
                refs = [remember(source/source_stage/'Hintergrund'/(name+'.png')) for name in names]
                hd_paths = [backgrounds/source_stage/(name+'_HD.png') for name in names]
                for ref, hdpath in zip(refs, hd_paths):
                    assert rgba(ref).size == rgba(hdpath).size
                extra = [joined([backgrounds/source_stage/(name+'_Wasser_HD.png') for name in names])] if source_stage=='A04' and group==2 else []
                art, masks, matched = strip_to_map(joined(refs),joined(hd_paths),native,nw,nh,y,extra)
                background[y*4:(y+nh)*4] = art
                if masks: water_mask[y*4:(y+nh)*4] = masks[0][:,:,3]>0
                placements.append(dict(group=group, source_native_size=[nw,nh], y=y, pieces=matched))
            bg_cache[source_stage] = (background,native,words,water_mask,placements)
        background,native,words,water_mask,placements = bg_cache[source_stage]
        if stage == 'A04':
            # Three palette states affect original ripple indices 3/4/5 only.
            indices = np.zeros((256,512),np.uint8)
            for yy in range(32):
                for xx in range(64):
                    word = int(words[yy,xx])
                    if word>>10&7 != 6: continue
                    addr = 8192+(word&1023)*16; raw=[]
                    for row in range(8):
                        p01,p23=a.vram[addr+row],a.vram[addr+row+8]
                        for bit in range(7,-1,-1):raw.append((p01>>bit&1)|(p01>>(bit+8)&1)<<1|(p23>>bit&1)<<2|(p23>>(bit+8)&1)<<3)
                    block = np.array(raw,np.uint8).reshape(8,8)
                    if word&0x4000:block=block[:,::-1]
                    if word&0x8000:block=block[::-1]
                    indices[yy*8:yy*8+8,xx*8:xx*8+8]=block
            probe_word=int(words[18,16]);probe=8192+(probe_word&1023)*16
            probe_px=[]
            for row in range(8):
                p01,p23=a.vram[probe+row],a.vram[probe+row+8]
                for bit in range(7,-1,-1):probe_px.append((p01>>bit&1)|(p01>>(bit+8)&1)<<1|(p23>>bit&1)<<2|(p23>>(bit+8)&1)<<3)
            pal=list(a.colors[96:112]); cycling=np.array(pal[3:6]);index4=indices.repeat(4,0).repeat(4,1)
            expand=lambda c:np.array([(c&31)*255/31,((c>>5)&31)*255/31,((c>>10)&31)*255/31])
            changed=[]
            for phase in range(3):
                rotated=np.roll(cycling,phase);phase_pal=pal.copy();phase_pal[3:6]=[int(v) for v in rotated]
                painted=background.copy()
                for n in range(3):
                    mask=(index4==n+3)&water_mask
                    delta=expand(int(rotated[n]))-expand(int(cycling[n]))
                    painted[:,:,:3][mask]=np.clip(background[:,:,:3][mask].astype(float)+delta*.85,0,255).astype(np.uint8)
                assert np.array_equal(painted[~water_mask],background[~water_mask])
                changed.append(int(np.count_nonzero(np.any(painted!=background,axis=2))))
                emit(Image.fromarray(painted),0,0,1,source_palette=96,select_address=probe,select_keys=[fnv_key(4,probe_px,phase_pal)])
            report['water'] = dict(probe_address=probe, changed_hd_pixels=changed, banks_unchanged=True, clock='native CGRAM key')
        emit(Image.fromarray(background),0,0,1)
        meta['regions']=regions;(folder/'pack.json').write_text(json.dumps(meta,indent=2))
        collection['scenes'].append(stage.lower())
        report[stage]=dict(dynamic_cells=dynamic_cells,tiles=len(tiles),regions=len(regions),background_source=source_stage,background_registration=placements)
    collection['name']='Stage 01 HD entrance + A02 + A03 + A04 + A05'
    (output/'pack.json').write_text(json.dumps(collection,indent=2))
    for item in receipts:
        if sha(item['source'])!=item['sha256']:raise RuntimeError('Source changed during import: '+item['source'])
    receipt=dict(art_scale=4,presentation_scale=4,sources=receipts,builder_sha256=sha(__file__),
                 preserved_existing_collection=str(prior),report=report,source_files_unchanged=True)
    (output/'import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    (audit/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(output=str(output),sources=len(receipts),scenes=collection['scenes'],water=report.get('water'))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','prior','out','audit'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();build(args.source,args.prior,args.out,args.audit)
