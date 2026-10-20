"""Register complete user-painted scene planes and original animated tile sheets.

Source files are preserved. Runtime planes are cropped/split, and a shared
sprite material may be normalized downward to native bounds. Native references
identify frames and flips. No image generation or upscaling occurs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct

import numpy as np
from PIL import Image

import hd_common as hd
from hd_tiles import write_pack
from hd_preview import fnv_key


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def native_rgba(path):
    a = hd.load_rgba(path).copy()
    matte = np.all(a[..., :3] == (128, 0, 0), axis=2)
    # Web rips use both truncated and expanded 5-bit colours. Canonicalize the
    # SD reference only; the user's HD files are never colour-converted.
    a[..., :3] = (a[..., :3] >> 3) * 8 + (a[..., :3] >> 3) // 4
    a[matte] = 0
    return a


def video_tiles(path):
    """Include tiles hidden from clean captures by per-line scroll animation."""
    data = Path(path).read_bytes()
    if len(data) != 0x10420: raise ValueError('Invalid video dump')
    vram = struct.unpack('<32768H', data[:0x10000])
    palette = struct.unpack('<256H', data[0x10000:0x10200])
    meta = json.loads(Path(path).with_suffix('.json').read_text())
    addresses = set()
    for layer in meta['layers']:
        for row in range(32):
            for col in range(64 if layer['wide'] else 32):
                entry = vram[(layer['map']+(col>>5)*0x400+row*32+(col&31))&0x7fff]
                addresses.add(((layer['tiles']+(entry&1023)*16)&0x7fff,(entry>>10&7)*16))
    for base in meta.get('obj_bases',[]):
        for tile in range(256):
            for pal in range(128,256,16): addresses.add(((base+tile*16)&0x7fff,pal))
    result = {}
    for address,pal in addresses:
        pixels=[]
        for y in range(8):
            a,b=vram[(address+y)&0x7fff],vram[(address+y+8)&0x7fff]
            for bit in range(7,-1,-1):pixels.append((a>>bit&1)|(a>>(bit+8)&1)<<1|(b>>bit&1)<<2|(b>>(bit+8)&1)<<3)
        if not any(pixels):continue
        colours=list(palette[pal:pal+16]);key=fnv_key(4,pixels,colours)
        result[key]=hd.TileInfo(4,colours,pixels).rgba()
    return result


def object_frames(spec, source, video, scale):
    """Bind one reusable material to native OBJ poses, including break masks.

    Guest frames own the silhouette and damage changes. This is a technical
    material transfer, not newly painted damage artwork. An explicit HD frame
    sheet can replace this temporary native_delta source later.
    """
    raw = Path(video).read_bytes()
    if len(raw) != 0x10420: raise ValueError('Invalid object video dump')
    vram = struct.unpack('<32768H', raw[:0x10000])
    palette = struct.unpack('<256H', raw[0x10000:0x10200])
    width, height = spec['size']
    if width % 8 or height % 8 or not 8 <= width <= 64 or not 8 <= height <= 64:
        raise ValueError('Object size must use native 8-pixel cells, up to 64x64')
    decoded = []
    for frame in spec['frames']:
        cells = []
        native = np.zeros((height, width, 4), np.uint8)
        for y in range(height // 8):
            for x in range(width // 8):
                addr = (spec['base'] + ((frame+x+y*16)&255)*16) & 0x7fff
                pixels = []
                for row in range(8):
                    a,b = vram[(addr+row)&0x7fff],vram[(addr+row+8)&0x7fff]
                    for bit in range(7,-1,-1):
                        pixels.append((a>>bit&1)|(a>>(bit+8)&1)<<1|(b>>bit&1)<<2|(b>>(bit+8)&1)<<3)
                colours = list(palette[spec['palette']:spec['palette']+16])
                key = fnv_key(4,pixels,colours)
                native[y*8:y*8+8,x*8:x*8+8] = hd.TileInfo(4,colours,pixels).rgba()
                cells.append((key,x,y))
        decoded.append((native,cells))
    if 'frame_images' not in spec:
        with Image.open(source/spec['image']) as im:
            art = im.convert('RGBA').crop(tuple(spec['art_crop_px']))
            if art.width < width*scale or art.height < height*scale:
                raise ValueError('Object material is below the requested HD resolution')
            art = np.array(art.resize((width*scale,height*scale),Image.Resampling.LANCZOS))
    elif len(spec['frame_images']) != len(spec['frames']):
        raise ValueError('Each object phase needs one HD frame image')
    base = decoded[0][0]
    result, receipts = {}, []
    for n,(native,cells) in enumerate(decoded):
        if 'frame_images' in spec:
            with Image.open(source/spec['frame_images'][n]) as im:
                im=im.convert('RGBA')
                factor=min(width*scale/im.width,height*scale/im.height)
                if factor>1:raise ValueError('Object frame would require upscaling')
                fitted=im.resize((round(im.width*factor),round(im.height*factor)),Image.Resampling.LANCZOS)
                canvas=Image.new('RGBA',(width*scale,height*scale))
                canvas.paste(fitted,((canvas.width-fitted.width)//2,0))
                painted=np.array(canvas)
        else:
            painted = art.copy()
        # Preserve HD material, applying only the original per-pixel colour
        # delta and holes at each damage phase. No runtime positional overlay.
        ratio = native[...,:3].astype(np.float32) / np.maximum(base[...,:3],8)
        ratio = np.clip(ratio,0,2).repeat(scale,0).repeat(scale,1)
        if n and 'frame_images' not in spec:
            painted[...,:3] = np.clip(np.rint(painted[...,:3]*ratio),0,255).astype(np.uint8)
        if 'frame_images' not in spec:
            alpha = native[...,3].repeat(scale,0).repeat(scale,1).astype(np.uint16)
            painted[...,3] = (painted[...,3].astype(np.uint16)*alpha//255).astype(np.uint8)
        for key,x,y in cells:
            tile = painted[y*8*scale:(y+1)*8*scale,x*8*scale:(x+1)*8*scale]
            if key in result and not np.array_equal(result[key],tile):
                raise ValueError('Conflicting object tile artwork')
            result[key] = tile.copy()
        receipts.append({'frame':spec['frames'][n],'keys':[key for key,_,_ in cells]})
    return result, receipts


def build(recipe_path, source, dumps, output, videos=()):
    output, source = Path(output), Path(source)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a new empty output directory')
    recipe = json.loads(Path(recipe_path).read_text(encoding='utf-8'))
    scale = recipe['scale']
    if recipe['version'] != 1 or type(scale) is not int or not 1 <= scale <= 10:
        raise ValueError('Expected version 1 and scale 1..10')
    originals = {}
    for dump in dumps:
        for key, tile in hd.load_tiles(dump).items():
            rgba = tile.rgba()
            if key in originals and not np.array_equal(originals[key], rgba):
                raise ValueError('Original key collision')
            originals[key] = rgba
    for video in videos:
        for key,rgba in video_tiles(video).items():
            if key in originals and not np.array_equal(originals[key],rgba):raise ValueError('Video key collision')
            originals[key]=rgba
    patterns = {}
    for key, a in originals.items():
        for flip in range(4):
            b = a[:, ::-1] if flip & 1 else a
            if flip & 2:
                b = b[::-1]
            patterns.setdefault(b.tobytes(), []).append((key, flip))
    tiles, registrations, conflicts = {}, [], []
    for motif in recipe.get('tilesheets', []):
        ref, art = source / motif['reference'], source / motif['image']
        native, painted = native_rgba(ref), hd.load_rgba(art)
        if painted.shape[:2] != (native.shape[0] * scale, native.shape[1] * scale):
            raise ValueError(f'{art}: expected exact {scale}x dimensions')
        matched = set()
        frame_counts=[]
        frame_key_lists=[]
        frames=motif.get('frames',[motif.get('crop',[0,0,native.shape[1],native.shape[0]])])
        for frame,(x0,y0,x1,y1) in enumerate(frames):
            cells=np.pad(native[y0:y1,x0:x1],((7,7),(7,7),(0,0)))
            art_cells=np.pad(painted[y0*scale:y1*scale,x0*scale:x1*scale],((7*scale,7*scale),(7*scale,7*scale),(0,0)))
            frame_keys=set()
            for y in range(cells.shape[0]-7):
                for x in range(cells.shape[1]-7):
                    cell=cells[y:y+8,x:x+8]
                    if not cell[...,3].any():continue
                    for key,flip in patterns.get(cell.tobytes(),[]):
                        tile=art_cells[y*scale:(y+8)*scale,x*scale:(x+8)*scale]
                        if flip&1:tile=tile[:,::-1]
                        if flip&2:tile=tile[::-1]
                        if key in tiles and not np.array_equal(tiles[key],tile):
                            conflicts.append({'key':key,'motif':motif['name'],'frame':frame,'xy':[x+x0-7,y+y0-7]})
                        else:tiles[key]=tile.copy()
                        matched.add(key);frame_keys.add(key)
            frame_counts.append(len(frame_keys))
            frame_key_lists.append(sorted(frame_keys))
        registrations.append({'name': motif['name'], 'keys': sorted(matched),
                              'frame_key_counts':frame_counts,
                              'frame_keys':frame_key_lists,
                              'reference_sha256': sha(ref), 'image_sha256': sha(art)})
    objects = []
    for spec in recipe.get('objects',[]):
        mapped, frames = object_frames(spec,source,videos[spec.get('video_index',0)],scale)
        for key,tile in mapped.items():
            if key in tiles and not np.array_equal(tiles[key],tile):
                raise ValueError('Object conflicts with a decorative tile')
            tiles[key] = tile
        objects.append({'name':spec['name'],'frames':frames,
                        'image_sha256':[sha(source/f) for f in spec['frame_images']] if 'frame_images' in spec else sha(source/spec['image']),
                        'damage_source':'authored HD frames, aspect fit, top aligned' if 'frame_images' in spec else 'native colour delta and silhouette'})
    # Validate all region dimensions before producing files.
    regions = []
    for region in recipe['regions']:
        region = dict(region)
        mask_sheet=region.pop('mask_tilesheet',None)
        if mask_sheet:region['mask_keys']=next(r['keys'] for r in registrations if r['name']==mask_sheet)
        path = source / region['image']
        crop = region.pop('crop', None)
        clear = region.pop('clear', [])
        preserve = region.pop('preserve', [])
        remove_top=region.pop('remove_top_components',False)
        from PIL import Image
        with Image.open(path) as im:
            if crop:
                im = im.crop(tuple(n*scale for n in crop))
                region['x'] += crop[0]; region['y'] += crop[1]
            if im.width % scale or im.height % scale:
                raise ValueError(f'{path}: region dimensions are not multiples of scale')
            if im.height > 4096:
                raise ValueError('Scene image is too tall')
            # The shared PNG decoder is limited to 4096 pixels. Split exactly
            # on native texel boundaries; no painting, resizing or overlap.
            chunk = 4096 // scale * scale
            for left in range(0, im.width, chunk):
                part = dict(region)
                part['x'] += left // scale
                part['image'] = f'region_{len(regions):02d}.png'
                regions.append((part, path, [left, 0, min(left+chunk, im.width), im.height], crop, clear, preserve,remove_top))
    if tiles:
        write_pack(tiles, output, scale)
        meta = json.loads((output / 'pack.json').read_text())
    else:
        output.mkdir(parents=True, exist_ok=True)
        meta = {'version': 1, 'scale': scale, 'tile_size': 8*scale, 'atlas_size': 2048, 'tiles': {}}
    for region, path, rect, crop, clear, preserve,remove_top in regions:
        with Image.open(path) as im:
            if crop: im=im.crop(tuple(n*scale for n in crop))
            if remove_top:
                from PIL import ImageDraw
                mask=im.getchannel('A').point(lambda a:255 if a else 0)
                for x in range(mask.width):
                    if mask.getpixel((x,0))==255:ImageDraw.floodfill(mask,(x,0),128)
                rgba=np.array(im);rgba[np.array(mask)==128]=0;im=Image.fromarray(rgba)
            if clear:
                original=im.copy()
                im=im.copy()
                for rectangle in clear: im.paste((0,0,0,0),tuple(n*scale for n in rectangle))
                for rectangle in preserve:
                    bounds=tuple(n*scale for n in rectangle);im.paste(original.crop(bounds),bounds[:2])
            if not crop and not clear and not remove_top and rect == [0,0,im.width,im.height]: shutil.copy2(path, output / region['image'])
            else: im.crop(rect).save(output / region['image'])
    meta.update(requires=['scene-regions-v1'], scene_block=recipe['scene_block'], regions=[r for r, *_ in regions])
    if 'native_maps' in recipe:meta['native_maps']=recipe['native_maps']
    if objects:
        meta['requires'].append('shared-objects-v1')
        meta['shared_objects'] = sorted({key for obj in objects for frame in obj['frames'] for key in frame['keys']})
    for animation in recipe.get('animations',[]):
        registration=next(r for r in registrations if r['name']==animation['tilesheet'])
        sheet=next(r for r in recipe['tilesheets'] if r['name']==animation['tilesheet'])
        with Image.open(source/sheet['image']) as im:
            # The runtime game-clock selector is deterministic across pause
            # and savestate restore. Native VRAM keys are retained as phase
            # evidence, not claimed to synchronize this cosmetic HD loop.
            for frame in list(range(1,len(sheet['frames'])))+[0]:
                x0,y0,x1,y1=sheet['frames'][frame]
                x0=animation['content_x'][0];x1=animation['content_x'][1]
                art=im.crop((x0*scale,y0*scale,x1*scale,y1*scale))
                canvas=Image.new('RGBA',((x1-x0)*scale,animation['height']*scale))
                canvas.paste(art,(0,canvas.height-art.height))
                name=f"animation_{animation['tilesheet']}_{frame}.png";canvas.save(output/name)
                meta['regions'].append({'layer':animation['layer'],'image':name,'coordinates':'map',
                    'x':animation['x'],'y':animation['y'],'wrap_x':x1-x0,'wrap_y':256,
                    'source_palette':animation['palette'],'select_address':animation['select_address'],
                    **({'priority':animation['priority']} if 'priority' in animation else {}),
                    'select_keys':registration['frame_keys'][frame] if frame else [],
                    'frame_period':animation.get('period',16),'frame_count':len(sheet['frames']),'frame_phase':frame})
    if 'object_mask_palette' in recipe: meta['object_mask_palette'] = recipe['object_mask_palette']
    (output / 'pack.json').write_text(json.dumps(meta, indent=2))
    receipt = {'recipe_sha256': sha(recipe_path), 'builder_sha256':sha(__file__),'recipe':recipe,'regions': [
        {'source': str(p.resolve()), 'sha256': sha(p), 'source_rect': rect, 'crop':crop, 'clear':clear, 'preserve':preserve,'remove_top_components':bool(remove_top), **r} for r, p, rect, crop, clear, preserve,remove_top in regions],
        'tilesheets': registrations, 'objects':objects, 'ambiguous_tile_variants': conflicts,
        'dump_sha256': [sha(Path(d)/'tiles.tsv') for d in dumps],
        'video_sha256': [sha(v) for v in videos]}
    (output / 'scene-receipt.json').write_text(json.dumps(receipt, indent=2))
    print(f'{len(meta["regions"])} scene image blocks, {len(tiles)} animated/decorative tiles: {output}')
    print('Sheet matches:', {r['name']: len(r['keys']) for r in registrations})
    return meta, receipt


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--recipe', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--dump', type=Path, action='append', required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--video', type=Path, action='append', default=[])
    a = p.parse_args()
    build(a.recipe, a.source, a.dump, a.out, a.video)
