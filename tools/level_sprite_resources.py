"""Per-family original OBJ contexts. Editor levels do not share SNES VRAM slots."""
import json
from pathlib import Path
import struct
from enemy_resources import ordinary_plan,palette
from level_objects import resource_entry,SpriteLibrary


def compile_resources(raw,placements,library,base_video):
    library=Path(library);index=json.loads((library/'library.json').read_text(encoding='utf-8'))
    profiles={(p['type'],p.get('variant',0)):p for p in index['profiles'] if not p.get('preview_only')}
    requested={};static=set()
    for actor in placements:
        if actor['type']>=128:continue
        entry=resource_entry(actor);key=(entry['type'],entry['variant']);requested[key]=key
        if actor.get('kind')=='event':static.add(key);continue
        profile=profiles.get(key,{})
        children=set(profile.get('child_types',()))
        if entry['type'] in (0x11,0x12,0x31,0x56):children.update((2,45,0x3d))
        death=raw[0x8000+((0xae00+entry['type'])&0x7fff)]
        if death:children.add(death)
        for t in children:
            if 0<t<128:requested.setdefault((t,0),key)
    out=bytearray(b'CV4VOBJ1')+struct.pack('<H',len(requested))+raw[0x20000:0x28000];adds={};sprites=SpriteLibrary(library)
    for key,parent in sorted(requested.items()):
        t,var=key;profile=profiles.get(key,{}) or next((p for (ty,_),p in profiles.items() if ty==t),{})
        context=profile.get('context',{});video_path=Path(context.get('video','_missing_'))
        if video_path.is_file():video=video_path.read_bytes()[:0x10200];add=context.get('tile_add',0)
        else:
            video=bytearray(base_video[:0x10200]);add=0
            if key not in static:
                plan=ordinary_plan(raw,dict(type=t))
                add=plan['tile_add'].get(t,0)
                for block in plan['blocks']:video[block['vram_word']*2:block['vram_word']*2+len(block['data'])]=block['data']
                try:colors=palette(library,dict(type=t,variant=var))
                except ValueError:
                    try:colors=palette(library,dict(type=parent[0],variant=parent[1]))
                    except ValueError:colors=base_video[0x10000:0x10200]
                video[0x10000:0x10200]=colors
        if len(video)!=0x10200:raise ValueError(f'M-{t:04X}: unvollständiger eigener Grafikkontext.')
        width=height=ax=ay=0;pixels=b''
        if key in static:
            sprite=sprites.sprite(dict(type=t,variant=var))
            if sprite:
                image,(ax,ay)=sprite;width,height=image.size;pixels=image.tobytes()
        out+=struct.pack('<8H',t,var,add,context.get('current_pose',0),width,height,ax,ay)+video+pixels
        adds[key]=add
    return bytes(out),adds
