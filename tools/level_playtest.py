"""Compile editor projects and run them in a private native game instance."""
import configparser
import hashlib
import json
from pathlib import Path
import struct
from enemy_workshop_native import NativeSession,ROOT
from enemy_resources import ordinary_plan,palette,write_bundle,ROM_SHA256
from enemy_sprite_export import descriptor
from level_assets import Assets,ensure_room
from level_project import validate


def monster_plan(raw,placements,index):
    family=set()
    for a in placements:
        t=a['type'];family.add(t)
        profile=next((p for p in index['profiles'] if p['type']==t and p.get('variant',0)==a.get('variant',0)),{})
        family.update(profile.get('child_types',[]))
        death=raw[0x8000+((0xae00+t)&0x7fff)]
        if death:family.add(death)
    return ordinary_plan(raw,dict(type=min(family),child_types=sorted(family))) if family else None


def compile_project(data,destination,rom=None,build=None,quest=0):
    validate(data);destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    raw=Path(rom or ROOT/'Super Castlevania IV (USA).sfc').read_bytes()
    if len(raw)!=0x100000 or hashlib.sha256(raw).hexdigest()!=ROM_SHA256:raise ValueError('Der Editor benötigt die ungeheaderte USA-ROM des Projekts.')
    library=ROOT/'artwork-local/enemy-library';index=json.loads((library/'library.json').read_text())
    inventory=json.loads((ROOT/'assets/enemy_sprite_inventory.json').read_text())
    poses={a['type']:a.get('poses',[]) for a in inventory['actors']}
    actors={};templates={}
    for r in data['rooms']:
        templates[r['tileset']]=Assets(ensure_room(r['tileset'],rom,build))
        for a in r['actors']:
            if a['type']>=128:raise ValueError('Bossmarker sind speicherbar. Der Level-Spieltest braucht dafür noch den jeweils passenden Boss-/Levelabschlussadapter.')
            actors.setdefault((a['type'],a.get('variant',0),bool(a.get('flags',0)&0x8000)),a)
    plan=monster_plan(raw,actors.values(),index)
    owners={};bank_data={}
    for a in actors.values():
        t=a['type']
        entry=dict(type=t,variant=a.get('variant',0));colors=palette(library,entry)
        profile=next((p for p in index['profiles'] if p['type']==t and p.get('variant',0)==a.get('variant',0)),{})
        banks={}
        for pose in set(poses.get(t,[]))|set(profile.get('poses',[])):
            for _,_,attr in descriptor(raw,pose):
                bank=attr>>9&7
                banks[bank]=colors[256+bank*32:256+(bank+1)*32]
        for bank,value in banks.items():
            if bank in bank_data and bank_data[bank]!=value:
                raise ValueError(f'M-{t:04X} und M-{owners[bank]:04X} benötigen verschiedene Farben in Palette {bank}. Diese Kombination braucht noch eine Palettenumlegung.')
            bank_data[bank]=value;owners[bank]=t
    word=lambda address:int.from_bytes(raw[(address>>16)*0x8000+(address&0x7fff):(address>>16)*0x8000+(address&0x7fff)+2],'little')
    stop=word(0x00d81b)
    while word(0x050000|stop)!=65535:stop+=6
    out=bytearray(b'CV4LVL1\0')+struct.pack('<HHH',len(data['rooms']),next(i for i,r in enumerate(data['rooms']) if r['id']==data['start_room']),stop)
    for r in data['rooms']:
        asset=templates[r['tileset']]
        if not asset.meta['supported'] or any(x.get('big') for x in asset.meta['ppu']['layers'][:2]):raise ValueError('Dieser Grafiksatz braucht noch einen eigenen Kartenmodus.')
        bases=[x['tiles'] for x in asset.meta['ppu']['layers'][:2]];colors=bytearray(asset.video[0x10000:0x10200])
        for bank,value in bank_data.items():colors[256+bank*32:256+(bank+1)*32]=value
        out+=struct.pack('<11H',r['width'],r['height'],r['tileset'],*r['spawn'],*bases,asset.meta['ppu']['bgmode'],r.get('collision_mode',0),len(r['actors']),len(r['doors']))
        out+=asset.video[:0xd400]+colors
        for kind in ('layers','collision'):
            for layer in ('front','back'):out+=struct.pack(f'<{r["width"]*r["height"]}H',*r[kind][layer])
        for a in r['actors']:
            t=a['type'];word=lambda addr:int.from_bytes(raw[0x8000+(addr&0x7fff):0x8000+(addr&0x7fff)+2],'little')
            hit=word(0xab00+t*2);bonus=raw[0x8000+((0xa88f+r['tileset'])&0x7fff)]+16*quest
            out+=struct.pack('<10H',t,a.get('variant',0),a['x'],a['y'],a.get('flags',0),hit&255,hit>>8,min(32767,word(0xac00+t*2)+bonus),word(0xad00+t*2),plan['tile_add'].get(t,0))
        for d in r['doors']:
            target=next(i for i,row in enumerate(data['rooms']) if row['id']==d['target'])
            out+=struct.pack('<9H',d['x'],d['y'],d['w'],d['h'],target,d['target_x'],d['target_y'],int(d.get('trigger','up')=='touch'),d.get('target_plane',0))
    file=destination/'level.bin';file.write_bytes(out)
    colors=bytearray(templates[data['rooms'][0]['tileset']].video[0x10000:0x10200])
    for bank,value in bank_data.items():colors[256+bank*32:256+(bank+1)*32]=value
    bundle=write_bundle(destination/'monsters.bin',colors,plan)
    return file,bundle


class Playtest:
    def __init__(self,data,folder,rom=None,build=None,fast=False,window_scale=3):
        self.folder=Path(folder);self.session=None;self.audio_unavailable=False
        level,monsters=compile_project(data,self.folder,rom,build)
        s=NativeSession(rom,build,folder=self.folder/'game');self.session=s
        config=configparser.ConfigParser();config.read(s.folder/'config.ini')
        config['General']['RunAhead']='0';config['Rewind']={'Enabled':'0'}
        if not fast:
            config['General']['DisableFrameDelay']='0';config['Graphics']['WindowScale']=str(max(2,min(8,window_scale)));config['Sound']['EnableAudio']='1'
        with (s.folder/'config.ini').open('w') as f:config.write(f)
        try:
            try:s.start()
            except (OSError,RuntimeError):
                log=(s.folder/'game.log').read_text(encoding='utf-8',errors='replace')
                if fast or 'audio device open FAILED' not in log:raise
                config['Sound']['EnableAudio']='0';self.audio_unavailable=True
                with (s.folder/'config.ini').open('w') as f:config.write(f)
                s.start()
            s.command('enemy','workshop off');s.command('enemy','capture off')
            s.command('enemy_resources',monsters)
            # Keep the declared slot list for native projectile/child lookups.
            raw=s.bytes;placements=[a for r in data['rooms'] for a in r['actors']]
            s.lua.eval('for a=0x13a0,0x13b5 do mainmemory.write_u8(a,255) end')
            if placements:
                index=json.loads((ROOT/'artwork-local/enemy-library/library.json').read_text(encoding='utf-8'))
                plan=monster_plan(raw,placements,index)
                # Compiler and runtime must use the same deterministic order.
                for b in plan['blocks']:s.write({0x13a0+b['slot']*2:b['pointer']&65535})
            s.command('level_project',level)
        except BaseException:self.close();raise

    def close(self):
        if self.session:self.session.close();self.session=None
