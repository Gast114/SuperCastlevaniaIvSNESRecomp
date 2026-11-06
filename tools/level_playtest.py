"""Compile editor projects and run them in a private native game instance."""
import configparser
import hashlib
from pathlib import Path
import struct
from enemy_workshop_native import NativeSession,ROOT
from enemy_resources import ordinary_plan,write_bundle,ROM_SHA256
from level_assets import Assets,ensure_room
from level_project import validate
from level_graphics import compile_graphics
from level_objects import resource_entry
from level_actor_values import values_for


def monster_plan(raw,placements,index):
    family=set()
    for a in placements:
        t=a['type']
        if t>=128:continue
        family.add(t)
        profile=next((p for p in index['profiles'] if p['type']==t and p.get('variant',0)==a.get('variant',0)),{})
        family.update(profile.get('child_types',[]))
        death=raw[0x8000+((0xae00+t)&0x7fff)]
        if death:family.add(death)
    return ordinary_plan(raw,dict(type=min(family),child_types=sorted(family))) if family else None


def compile_project(data,destination,rom=None,build=None,quest=0):
    validate(data);destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    raw=Path(rom or ROOT/'Super Castlevania IV (USA).sfc').read_bytes()
    if len(raw)!=0x100000 or hashlib.sha256(raw).hexdigest()!=ROM_SHA256:raise ValueError('Der Editor benötigt die ungeheaderte USA-ROM des Projekts.')
    library=ROOT/'artwork-local/enemy-library'
    actors={};templates={}
    for r in data['rooms']:
        templates[r['tileset']]=Assets(ensure_room(r['tileset'],rom,build))
        for a in r['actors']:
            actors.setdefault((a['type'],a.get('variant',0),bool(a.get('flags',0)&0x8000)),a)
    from level_bosses import prepare_bosses
    bosses=prepare_bosses({a['type'] for a in actors.values() if a['type']>=128},rom,build)
    boss_indices={t:i for i,t in enumerate(bosses)}
    from level_sprite_resources import compile_resources
    virtual,adds=compile_resources(raw,actors.values(),library,templates[data['rooms'][0]['tileset']].video)
    word=lambda address:int.from_bytes(raw[(address>>16)*0x8000+(address&0x7fff):(address>>16)*0x8000+(address&0x7fff)+2],'little')
    stop=word(0x00d81b)
    while word(0x050000|stop)!=65535:stop+=6
    # Immutable host background texels cannot be overwritten by OBJ uploads or boss DMA.
    mixed=True
    out=bytearray(b'CV4LVL4\0' if mixed else b'CV4LVL3\0')+struct.pack('<HHH',len(data['rooms']),next(i for i,r in enumerate(data['rooms']) if r['id']==data['start_room']),stop)
    if mixed:
        atlas,maps=compile_graphics(data,rom,build);out+=struct.pack('<I',len(atlas))+b''.join(atlas)
    out+=struct.pack('<H',len(bosses))+b''.join(bosses.values())
    for room_index,r in enumerate(data['rooms']):
        asset=templates[r['tileset']]
        if not asset.meta['supported'] or any(x.get('big') for x in asset.meta['ppu']['layers'][:2]):
            if not mixed:raise ValueError('Dieser Grafiksatz braucht noch einen eigenen Kartenmodus.')
            asset=Assets(ensure_room(0,rom,build))
        bases=[x['tiles'] for x in asset.meta['ppu']['layers'][:2]];colors=bytearray(asset.video[0x10000:0x10200])
        out+=struct.pack('<11H',r['width'],r['height'],r['tileset'],*r['spawn'],*bases,asset.meta['ppu']['bgmode'],r.get('collision_mode',0),len(r['actors']),len(r['doors']))
        video=bytearray(asset.video[:0x10000])
        out+=video+colors
        for kind in ('layers','collision'):
            for layer_index,layer in enumerate(('front','back')):
                values=maps[room_index][layer_index] if kind=='layers' and mixed else r[kind][layer]
                out+=struct.pack(f'<{len(values)}'+('I' if kind=='layers' and mixed else 'H'),*values)
        for a in r['actors']:
            t=a['type'];word=lambda addr:int.from_bytes(raw[0x8000+(addr&0x7fff):0x8000+(addr&0x7fff)+2],'little')
            value=values_for(raw,a,r['tileset'],quest)
            options=int(a.get('boss_start','direct')=='sequence')|2*int(a.get('boss_end','continue')=='exit')|4*int('hp' in a.get('stats',{}))|8*int('half_width' in a.get('stats',{}))|16*int('half_height' in a.get('stats',{}))
            out+=struct.pack('<14H',t,a.get('variant',0),a['x'],a['y'],a.get('flags',0),value['half_width'],value['half_height'],value['hp'] or 0,0x26 if t==14 else word(0xad00+t*2),adds.get((t,resource_entry(a)['variant']),0),a.get('stats',{}).get('contact_damage',65535),2 if t>=128 else 1 if t==14 else 3 if a.get('kind')=='event' else 0,boss_indices.get(t,0),options)
        for d in r['doors']:
            target=next(i for i,row in enumerate(data['rooms']) if row['id']==d['target'])
            out+=struct.pack('<9H',d['x'],d['y'],d['w'],d['h'],target,d['target_x'],d['target_y'],int(d.get('trigger','up')=='touch'),d.get('target_plane',0))
    out+=virtual
    file=destination/'level.bin';file.write_bytes(out)
    colors=templates[data['rooms'][0]['tileset']].video[0x10000:0x10200]
    bundle=write_bundle(destination/'monsters.bin',colors)
    return file,bundle


class Playtest:
    def __init__(self,data,folder,rom=None,build=None,fast=False,window_scale=3):
        self.folder=Path(folder);self.session=None;self.audio_unavailable=False
        self.notes='Szenenobjekte werden als Kulisse dargestellt; ihre Original-Levelskripte sind deaktiviert.' if any(a.get('kind')=='event' for r in data['rooms'] for a in r['actors']) else ''
        level,monsters=compile_project(data,self.folder,rom,build)
        s=NativeSession(rom,build,folder=self.folder/'game');self.session=s
        config=configparser.ConfigParser();config.read(s.folder/'config.ini')
        config['General']['RunAhead']='0';config['Rewind']={'Enabled':'0'}
        if not fast:
            config['General']['DisableFrameDelay']='0';config['Graphics']['WindowScale']=str(max(2,min(8,window_scale)));config['Sound']['EnableAudio']='1'
        with (s.folder/'config.ini').open('w') as f:config.write(f)
        try:
            try:s.start(defer_show=True)
            except (OSError,RuntimeError):
                log=(s.folder/'game.log').read_text(encoding='utf-8',errors='replace')
                if fast or 'audio device open FAILED' not in log:raise
                config['Sound']['EnableAudio']='0';self.audio_unavailable=True
                with (s.folder/'config.ini').open('w') as f:config.write(f)
                s.start(defer_show=True)
            s.command('enemy','workshop off');s.command('enemy','capture off')
            s.command('enemy_resources',monsters)
            # Virtual families own their own textures/palettes; guest child lookups
            # may keep the original fixed effect offset without allocating OBJ VRAM.
            s.lua.eval('for a=0x13a0,0x13b5 do mainmemory.write_u8(a,255) end')
            s.command('level_project',level)
            # Finish actor initialization and draw the project while hidden.
            # Otherwise the user can play the bootstrap level before F5 is ready.
            from enemy_workshop_native import play
            play.advance(s.lua,2)
        except BaseException:self.close();raise

    def show(self):
        if self.session:self.session.command('window','show')

    def close(self):
        if self.session:self.session.close();self.session=None


class OriginalPlaytest:
    """Play an original section natively, including its scripts and Mode7 scenes."""
    def __init__(self,number,folder,rom=None,build=None,fast=False,window_scale=3):
        if type(number) is not int or not 0<=number<68:raise ValueError('Ungültiger Originalabschnitt.')
        self.folder=Path(folder);self.session=None;self.audio_unavailable=False
        session=NativeSession(rom,build,folder=self.folder/'game');self.session=session
        config=configparser.ConfigParser();config.read(session.folder/'config.ini')
        config['General']['RunAhead']='0';config['Rewind']={'Enabled':'0'}
        if not fast:
            config['General']['DisableFrameDelay']='0';config['Graphics']['WindowScale']=str(max(2,min(8,window_scale)));config['Sound']['EnableAudio']='1'
        with (session.folder/'config.ini').open('w') as f:config.write(f)
        try:
            try:session.start(defer_show=True)
            except (OSError,RuntimeError):
                log=(session.folder/'game.log').read_text(encoding='utf-8',errors='replace')
                if fast or 'audio device open FAILED' not in log:raise
                config['Sound']['EnableAudio']='0';self.audio_unavailable=True
                with (session.folder/'config.ini').open('w') as f:config.write(f)
                session.start(defer_show=True)
            session.command('enemy','workshop off');session.command('enemy','capture off')
            if number:
                session.write({0x86:number,0x70:3})
                from enemy_workshop_native import play
                for _ in range(900):
                    play.advance(session.lua,1)
                    if session.read(0x70)==5 and session.read(0x3c)==0:break
                else:raise ValueError('Originalabschnitt konnte nicht vollständig geladen werden.')
        except BaseException:self.close();raise
    def close(self):
        if self.session:self.session.close();self.session=None

    def show(self):
        if self.session:self.session.command('window','show')
