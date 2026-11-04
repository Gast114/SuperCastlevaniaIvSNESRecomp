"""Prepared native boss encounters, including their real auxiliary actors.

Only an isolated boot scene is used; no player saves or source levels load.
These are bounded encounter templates, not invented boss AI or art.
"""
import json
import hashlib
from pathlib import Path
import struct
from enemy_workshop_native import NativeSession,ROOT
from enemy_catalog_profiles import spawn_boss
from enemy_catalog_profiles import boss_profiles

REVISION=5
RANGES=((0x580,0x940),(0x1200,0x80),(0x13c0,0x30),(0x1e00,0x200))
STATE_BYTES=sum(size for _,size in RANGES)

def preview_from_template(payload,cache):
    t,bx,by,slot,body=struct.unpack_from('<5H',payload)
    path=cache/f'{t:02x}-group.png'
    digest=hashlib.sha256(payload).hexdigest()
    if t==0x81:return
    if path.is_file() and path.with_suffix('.json').is_file() and json.loads(path.with_suffix('.json').read_text()).get('template_sha256')==digest:return
    from enemy_sprite_export import render_pose
    state=payload[10+STATE_BYTES+2:];at=2+slot-0x580
    w=lambda off:struct.unpack_from('<H',state,at+off)[0]
    rom=(ROOT/'Super Castlevania IV (USA).sfc').read_bytes();start=10+(STATE_BYTES+2)*2;video=payload[start:start+0x10200]+bytes(0x220)
    from PIL import Image
    picture=Image.new('RGBA',(512,512));anchor=[256,256];center=(bx,by)
    for pos in reversed(range(0,0x940,64)):
        field=lambda off:struct.unpack_from('<H',state,2+pos+off)[0]
        if not field(16) or field(0)<0x8000:continue
        try:meta,part=render_pose(rom,field(16),field(0),video,3,field(0x26),field(2))[0]
        except ValueError:continue
        ax,ay=meta['anchor'];flip=field(4)
        if flip&0x4000:part=part.transpose(Image.Transpose.FLIP_LEFT_RIGHT);ax=part.width-ax
        if flip&0x8000:part=part.transpose(Image.Transpose.FLIP_TOP_BOTTOM);ay=part.height-ay
        signed=lambda v:(v+32768)%65536-32768
        picture.alpha_composite(part,(256+signed(field(10)-center[0])-ax,256+signed(field(14)-center[1])-ay))
    if not picture.getbbox():raise ValueError('Bossvorlage enthält keinen sichtbaren Körper oder Hilfsteil.')
    picture.save(path);path.with_suffix('.json').write_text(json.dumps(dict(anchor=anchor,template_sha256=digest)))

def profiles(session):
    rows=boss_profiles(session)
    for t,room,controller,variant,slot in ((0x82,17,0x48,0,0x680),(0x8d,67,0x2a,12,0x580)):
        p=session.word(0,0xd81b+room*2);record=None
        for n in range(1024):
            at=5*0x8000+((p+n*6)&32767);data=session.bytes[at:at+6]
            if data[:2]==b'\xff\xff':break
            if data[4:]==bytes((controller,variant)):record=p+n*6;break
        if record is None:raise ValueError('Der native Boss-Szenencontroller fehlt.')
        rows.append(dict(type=t,variant=0,boss=True,room=room,x=128,y=160,flags=0x8000,main_type=t,main_slot=slot,
            controller=controller,controller_variant=variant,scene_record=record,name=f'M-{t:04X}',child_types=list(range(1,14))))
    return rows

def spawn_scene(session,entry):
    from level_assets import Assets,ensure_room
    from enemy_resources import write_bundle
    video=Assets(ensure_room(entry['room'])).video;colors=video[0x10000:0x10200]
    session.command('loadfile',session.base);session.entry=entry;session.target=entry['main_slot'];session.neutral_scene=True;session.arena_room=0;session.elapsed=0;session.arena_collision_ready=False
    session.lua.eval('for a=0x580,0xebf do mainmemory.write_u8(a,0) end')
    session.command('enemy_resources',write_bundle(session.folder/'scene-colors.bin',colors,dict(blocks=[dict(vram_word=0x6a00,data=video[0xd400:0x10000])]),full_palette=True))
    pointer=session.word(0,0xd81b)
    while session.word(5,pointer)!=65535:pointer+=6
    session.write({0xb8:0,0x88:session.quest,0x94:pointer,0x96:pointer,0x590:entry['controller'],0x594:entry['controller_variant'],0x58a:128,0x58e:128,0x592:0})
    for _ in range(1200):
        snapshot=session.step(1)
        main=next((a for a in snapshot['actors'] if a['type']==entry['type']),None)
        if main:entry['main_slot']=main['slot'];session.target=main['slot'];return snapshot
        if entry['type']==0x8d and session.read(0x590)==0x8d and session.read(0x586)>0 and snapshot['actors']:return snapshot
    session.command('wram',session.folder/'scene-failure-ram.bin');session.command('dump',session.folder/'scene-failure-video.bin')
    raise ValueError(f'M-{entry["type"]:04X}: der native Szenencontroller hat keinen sichtbaren Körper gestartet. Diagnose: {session.folder}')

def prepare_bosses(types,rom=None,build=None):
    result={};session=None
    cache=ROOT/'artwork-local/level-editor/bosses';cache.mkdir(parents=True,exist_ok=True)
    try:
        for t in sorted(types):
            path=cache/f'{t:02x}-r{REVISION}.bin'
            if path.is_file():
                cached=path.read_bytes();slot=struct.unpack_from('<5H',cached)[3]
                state=struct.unpack_from('<H',cached,10+STATE_BYTES+4+slot-0x580+18)[0]
                if t!=0x8d or state>=3:result[t]=cached;preview_from_template(cached,cache);continue
            if session is None:session=NativeSession(rom,build);session.start();session.command('enemy','capture off')
            entry=next((e for e in profiles(session) if e['type']==t and e.get('boss')),None)
            if not entry:raise ValueError(f'M-{t:04X}: kein geprüfter Bosscontroller vorhanden.')
            states=[];video=None
            for intro in (True,False):
                if 'controller' in entry:spawn_scene(session,entry)
                else:spawn_boss(session,entry,neutral=True,introduction=intro)
                if not intro:session.step(240)
                if not intro and t==0x8d:
                    for _ in range(1200):
                        if session.read(entry['main_slot']+18)>=3:break
                        session.step(1)
                    else:raise ValueError('Der Finalboss hat seine native Einleitung noch nicht beendet.')
                ram=session.folder/'boss-ram.bin';session.command('wram',ram);data=ram.read_bytes()
                states.append(struct.pack('<H',int.from_bytes(data[0xb8:0xba],'little'))+b''.join(data[a:a+n] for a,n in RANGES))
                if not intro:
                    video=session.folder/'boss-video.bin';session.command('dump',video);video=video.read_bytes()
                    # The native raster IRQ reads these shadow registers each
                    # field. OBJ bytes alone lose boss palettes/mode switches.
                    video=video[:0x10200]+data[0x100:0x200]
                    if t==0x81:
                        image=cache/'mode7-body.png'
                        session.command('enemy_surface',image)
                        (cache/'mode7-body.json').write_text(json.dumps(dict(anchor=[entry['x']-session.read(0x1c),entry['y']-session.read(0x1e)])))
            ppu=json.loads(session.command('ppu'));matrix=struct.pack('<9H',*(v&65535 for v in ppu['m7']),ppu['m7sel'])
            payload=struct.pack('<5H',t,entry['x'],entry['y'],entry['main_slot'],entry.get('main_type',t))+b''.join(states)+video+matrix
            preview_from_template(payload,cache);path.write_bytes(payload);result[t]=payload
    finally:
        if session:session.close()
    return result
