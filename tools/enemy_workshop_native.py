"""Private native-engine session for the separate enemy workshop.

All guest writes, snapshots and captures live in an isolated copy. The artist's
running game, configuration, saves and original ROM are never modified.
"""
import json
import base64
import hashlib
import socket
import subprocess
import tempfile
import time
from pathlib import Path
import sciv_play as play
import sciv_test_support as sciv
from enemy_catalog_profiles import boss_profiles,spawn_boss,hold_boss_stage
from enemy_catalog_data import catalog_metadata

ROOT=Path(__file__).resolve().parents[1]
NAMES={0x11:'Skelett – Gehen',0x12:'Skelett – Knochenwerfer',2:'Knochen und Bruchstücke'}


class NativeSession:
    def __init__(self,rom=None,build=None,folder=None):
        self.rom=Path(rom or ROOT/'Super Castlevania IV (USA).sfc').resolve()
        self.bytes=self.rom.read_bytes()
        if len(self.bytes)!=0x100000 or hashlib.sha256(self.bytes).hexdigest()!='0ef6f4cce5a2273fa49fe1ce724e0048a8e39c91da6b00dbb693fe1ba909177d':
            raise ValueError('Die Werkstatt benötigt die ungeheaderte USA-ROM des Projekts.')
        self.build=Path(build or ROOT/'build-lua').resolve()
        if not (self.build/sciv.EXE_NAME).is_file():
            raise FileNotFoundError('Werkstatt-Laufzeit fehlt. Bitte Gegner_Werkstatt_starten.cmd verwenden.')
        parent=ROOT/'artwork-local/enemy-workshop';parent.mkdir(parents=True,exist_ok=True)
        self.folder=Path(folder or tempfile.mkdtemp(prefix='session-',dir=parent)).resolve()
        self.exe=sciv.prepare(self.folder,self.build,{'General':{'DisableFrameDelay':1},
                    'Graphics':{'WindowScale':1,'Widescreen':0},'Sound':{'EnableAudio':0}})
        self.proc=None;self.lua=None;self.log=None;self.target=0x580
        self.catalog=self.read_catalog()+boss_profiles(self)
        self.direction=-1
        self.elapsed=0
        self.arena_enabled=False;self.arena_target=96;self.quest=0
        self.neutral_scene=False;self.resource_library=ROOT/'artwork-local/enemy-library';self.resource_plan=None

    def word(self,bank,address):
        offset=bank*0x8000+(address&0x7fff)
        return int.from_bytes(self.bytes[offset:offset+2],'little')

    def read_catalog(self):
        """Retail ordinary-actor records, not a guessed list of tile images.

        $00:D3EC selects $00:D81B, bank05 records are six bytes; low x bits
        select other record families and must not be interpreted as actor IDs.
        """
        entries={}
        for room in range(68):
            address=self.word(0,0xd81b+room*2)
            for index in range(1024):
                offset=5*0x8000+(address&0x7fff)+index*6
                raw=self.bytes[offset:offset+6]
                if len(raw)!=6:raise ValueError('Ungültige native Spawn-Tabelle')
                flags=int.from_bytes(raw[:2],'little')
                if flags==0xffff:break
                if flags&3 or not raw[4] or raw[4] in (0x0e,0x2a,0x2e,0x48):continue
                actor=raw[4]
                entry={'type':actor,'variant':raw[5],'room':room,'x':flags&0xffc,
                       'y':int.from_bytes(raw[2:4],'little')&0xffc,'flags':flags,'record':address+index*6}
                entries.setdefault((actor,raw[5]),entry)
            else:raise ValueError('Spawn-Tabelle ohne Abschluss')
        # Script-created enemies/bosses need not occur in the ordinary placement
        # records. Offer their native graphics contexts as provisional entries.
        contexts={}
        for room in range(68):
            pointer=self.word(6,0x8bcd+room*2)
            offset=6*0x8000+(pointer&0x7fff)
            count=self.bytes[offset]
            if count>32:continue
            for actor in self.bytes[offset+1:offset+1+count]:
                if actor<128:contexts.setdefault(self.word(1,0xa900+actor*3),room)
        present={key[0] for key in entries}
        for actor in range(1,128):
            if actor in present or actor in (0x0e,0x2a,0x2e,0x48):continue
            group=self.word(1,0xa900+actor*3)
            count=self.bytes[0x8000+(0xaa80&0x7fff)+actor]
            if group in contexts and 0<count<32:
                entries[(actor,0)]={'type':actor,'variant':0,'room':contexts[group],
                    'x':160,'y':176,'flags':0x8000,'record':None,'provisional':True}
        return [dict(v,**catalog_metadata(v)) for _,v in sorted(entries.items())]

    def start(self,fixture=None):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        self.log=(self.folder/'game.log').open('w')
        self.proc=subprocess.Popen([str(self.exe),str(self.rom)],cwd=self.folder,
            env=sciv.clean_env(SNESRECOMP_LUA_PORT=port,SNESRECOMP_LUA_PAUSED=1),
            stdout=self.log,stderr=self.log,startupinfo=sciv.hidden_window())
        try:
            for _ in range(200):
                try:self.lua=play.LuaClient(port=port);self.lua.command('ping');break
                except OSError:
                    if self.proc.poll() is not None:raise RuntimeError('Native Laufzeit beendet; siehe game.log')
                    time.sleep(.05)
            if self.lua is None:raise TimeoutError('Native Werkstatt-Laufzeit antwortet nicht')
            self.command('enemy','workshop on')
            self.command('hd','off')
            if fixture:self.command('loadfile',Path(fixture).resolve())
            else:
                self.command('reset')
                play.advance(self.lua,240);play.advance(self.lua,2,('Start',));play.advance(self.lua,50)
                play.advance(self.lua,2,('Start',));play.advance(self.lua,330)
                for _ in range(4):
                    if self.read(0x32)==4 and self.read(0x70)==5:break
                    play.advance(self.lua,2,('Start',))
                    play.advance(self.lua,180)
                if self.read(0x32)!=4 or self.read(0x70)!=5:
                    self.command('screenshot',self.folder/'boot-error.png')
                    raise RuntimeError('Native Ausgangsszene wurde nicht vollständig geladen.')
            self.command('save',0)
            self.base=self.folder/'saves/save0.sav'
            self.step(1)
            return self
        except BaseException:
            self.close();raise

    def command(self,name,arg=''):
        return self.lua.eval(f'return game.command({json.dumps(name)},{json.dumps(str(arg))})')['values'][0]

    def read(self,address):
        return int(self.lua.eval(f'return mainmemory.read_u16_le({address})')['values'][0])

    def write(self,values):
        self.lua.eval(';'.join(f'mainmemory.write_u16_le({a},{v&65535})' for a,v in values.items()))

    def snapshot(self):
        path=self.folder/'observation.json';self.command('enemy_snapshot',path)
        result=json.loads(path.read_text())
        if hasattr(self,'entry'):
            # Scripted gates/props may be created by the room after streaming
            # stops. They are not descendants of the selected skeleton.
            family={self.entry['type'],self.entry.get('main_type',self.entry['type'])}
            if self.entry['type'] in (0x11,0x12,0x31,0x56):family.update((2,45,0x3d))
            family.update(self.entry.get('child_types',[]))
            if self.entry['type']<128:family.add(self.bytes[0x8000+((0xae00+self.entry['type'])&0x7fff)])
            result['actors']=[a for a in result['actors'] if a['type'] in family]
            main=next((a for a in result['actors'] if a['type']==self.entry.get('main_type',self.entry['type']) and
                       (not self.entry.get('boss') or a['slot']==self.entry.get('main_slot',a['slot']))),None)
            if main:self.target=main['slot']
            result['target']=self.target
            if getattr(self,'arena_enabled',False) and not self.entry.get('boss'):
                result['arena']={'floor':192,'target_x':self.arena_target,'target_y':168}
            values=self.lua.eval(f'return mainmemory.read_u16_le({self.target}+6),mainmemory.read_u16_le({self.target}+0x12),'
                f'mainmemory.read_u16_le({self.target}+0xa),mainmemory.read_u16_le({self.target}+0xe),'
                f'mainmemory.read_u16_le({self.target}+0x28),mainmemory.read_u16_le({self.target}+0x2a),'
                f'mainmemory.read_u16_le({self.target}+0x18),mainmemory.read_u16_le({self.target}+0x1a),'
                f'mainmemory.read_u16_le({self.target}+0x1c),mainmemory.read_u16_le({self.target}+0x1e),'
                f'mainmemory.read_u16_le({self.target}+0x10),mainmemory.read_u16_le(0x84),'
                f'mainmemory.read_u16_le(0x88),mainmemory.read_u16_le(0x1c),'
                f'mainmemory.read_u16_le(0x1e),mainmemory.read_u16_le(0x86)')['values']
            values=list(map(int,values))
            signed=lambda v:v-65536 if v>=32768 else v
            result['live_stats']=dict(hp=values[0],state=values[1],x=values[2],y=values[3],half_width=values[4],half_height=values[5],
                                      speed_x=signed(values[7])+values[6]/65536,speed_y=signed(values[9])+values[8]/65536,
                                      actor_type=values[10],present=values[10]==self.entry.get('main_type',self.entry['type']),
                                      difficulty=values[11],quest=values[12],source_room=self.entry['room'],
                                      runtime_room=values[15],neutral=self.neutral_scene)
            if self.entry.get('boss'):
                origin=max(0,self.entry['x']-128)
                result['arena']={'floor':(192 if self.neutral_scene else 200)-values[14],
                                 'target_x':origin+(64 if self.direction<0 else 192)-values[13],
                                 'target_y':(168 if self.neutral_scene else 176)-values[14],'boss':True}
                if self.arena_enabled and self.entry['type']==0x81:
                    surface=self.folder/'boss-surface.png'
                    self.command('enemy_surface',surface)
                    # The exact field travels with its OBJ snapshot; reusing a
                    # mutable file path would mix two animation times in the UI.
                    result['boss_surface']=base64.b64encode(surface.read_bytes()).decode('ascii')
            if self.neutral_scene:
                result['neutral_scene']=True
                result['resources']={'source':'original ROM + prepared palette','source_level_loaded':False,
                    'obj_pages':self.resource_plan['pages'] if self.resource_plan else None}
            if self.arena_enabled and not self.entry.get('boss') and values[10]>0x8d:
                result['context_error']=f'M-{self.entry["type"]:04X}: Grafik-/Szenenkontext noch nicht stabil. Bitte ein anderes Monster wählen.'
                result['live_stats']={'present':False}
                result['actors']=[]
        return result

    def prepare_arena(self):
        # The original collision lookup 00:CF86 reads 64x64 8px cells
        # from 7E:4000 / 7E:A000. Tile 0=air, 1=solid. Both planes agree.
        # Bound each RPC below the Lua runtime's instruction limit.
        if not getattr(self,'arena_collision_ready',False):
            for page in range(4):
                self.lua.eval(f'for i={page*1024},{page*1024+1023} do '
                    'local solid=(i>=1024 or i%1024>=768 or i%32==0 or i%32==31) and 1 or 0 '
                    'mainmemory.write_u16_le(0x4000+i*2,solid) mainmemory.write_u16_le(0xa000+i*2,solid) end')
            self.arena_collision_ready=True
        boss=getattr(self,'entry',{}).get('boss',False)
        origin=max(0,self.entry['x']-128) if boss else 0
        self.camera(origin,0)
        target=origin+(64 if self.direction<0 else 192) if boss else self.arena_target
        values={0x54a:target,0x54e:168,0xbc:0x7fff,
                0x70:5,0x86:self.arena_room,0x552:0,0x558:0,0x55a:0,0x55c:0,0x55e:0,0x13f4:16}
        if not boss:values[0xb8]=0
        self.write(values)

    def step(self,frames=1):
        if getattr(self,'entry',{}).get('boss'):
            for _ in range(frames):
                # Leave suspended native room/graphics initialization alone.
                # Its DP blocks are distinct from the normal scene context.
                if self.read(0x3c)==0:hold_boss_stage(self,self.entry)
                play.advance(self.lua,1)
            self.elapsed+=frames
            return self.snapshot()
        elif getattr(self,'entry',None) and self.arena_enabled:
            for _ in range(frames):
                if self.read(0x3c)==0:self.prepare_arena()
                play.advance(self.lua,1)
            self.elapsed+=frames
            return self.snapshot()
        play.advance(self.lua,frames);self.elapsed+=frames
        return self.snapshot()

    def camera(self,x,y):
        x=max(0,x);y=max(0,y)
        self.write({0x1c:x,0x1e:y,0x1280:x,0x12c0:x,0x1298:y,0x12d8:y})

    def enter_neutral(self,entry):
        """Reset only the common stage, then install graphics without a room load."""
        from enemy_resources import ordinary_plan,palette,write_bundle
        plan=None if entry.get('boss') else ordinary_plan(self.bytes,entry)
        bundle=write_bundle(self.folder/'monster-resources.bin',palette(self.resource_library,entry),
                            plan,full_palette=bool(entry.get('boss')))
        self.command('loadfile',self.base)
        self.entry=entry;self.target=entry.get('main_slot',0x580) if entry.get('boss') else 0x580
        self.neutral_scene=True;self.arena_room=0;self.elapsed=0
        self.arena_collision_ready=False
        self.lua.eval('for a=0x580,0xebf do mainmemory.write_u8(a,0) end '
                      'for a=0x1200,0x127f do mainmemory.write_u8(a,0) end '
                      'for a=0x13a0,0x13b5 do mainmemory.write_u8(a,255) end')
        pointer=self.word(0,0xd81b)
        for _ in range(1024):
            if self.word(5,pointer)==0xffff:break
            pointer+=6
        else:raise RuntimeError('Neutrale Spawnliste hat keinen Abschluss.')
        self.write({0x94:pointer,0x96:pointer,0x88:self.quest,0xb8:0,
                    0x84:self.bytes[0x8000+((0xa88f+entry['room'])&0x7fff)]+16*self.quest})
        self.resource_plan=plan
        self.command('enemy_resources',bundle)
        if self.resource_plan:
            for block in self.resource_plan['blocks']:
                self.write({0x13a0+block['slot']*2:block['pointer']&65535})
        self.prepare_arena()

    def spawn_neutral(self,entry,count=1):
        if entry.get('boss'):
            arena=self.arena_enabled;self.arena_enabled=False
            try:spawn_boss(self,entry,neutral=True)
            finally:self.arena_enabled=arena
            return self.snapshot()
        self.enter_neutral(entry)
        t=entry['type'];hit=self.word(1,0xab00+t*2);difficulty=self.read(0x84)
        for n in range(max(1,min(8,count))):
            base=0x580+n*0x40
            self.write({base+0x10:t,base+0x14:entry['variant'],base+0xa:160+n*30,base+0xe:128,
                        base+2:0x8018 if entry['flags']&0x8000 else 0,
                        base+0x28:hit&255,base+0x2a:hit>>8,
                        base+0x26:self.resource_plan['tile_add'].get(t,0),
                        base+6:min(0x7fff,self.word(1,0xac00+t*2)+difficulty),
                        base+0x2e:self.word(1,0xad00+t*2)})
        snapshot=self.step(4)
        for _ in range(48):
            if any(a['type']==t for a in snapshot['actors']):break
            snapshot=self.step(1)
        return snapshot

    def spawn(self,entry,count=1):
        if self.arena_enabled:return self.spawn_neutral(entry,count)
        self.neutral_scene=False
        return self._spawn_original(entry,count)

    def _spawn_original(self,entry,count=1):
        if entry.get('boss'):
            arena=self.arena_enabled;self.arena_enabled=False
            try:return spawn_boss(self,entry)
            finally:self.arena_enabled=arena
        self.command('loadfile',self.base)
        self.write({0x86:entry['room'],0x70:3,0x88:self.quest})
        play.advance(self.lua,100)
        x,y=entry['x'],entry['y']
        self.camera(x-160,y-176)
        self.write({0x54a:max(32,x-72),0x54e:y})
        play.advance(self.lua,32)
        # The retail loader has supplied the room's actual graphics, palette,
        # collision data and $13A0 resource list. Initialize like $00:D6F0.
        group=self.word(1,0xa900+entry['type']*3)
        add=0
        for i in range(11):
            if self.read(0x13a0+i*2)==group:
                add=self.word(1,0x9534+0x13a0+i*2);break
        self.lua.eval('for a=0x580,0xEBF do mainmemory.write_u8(a,0) end')
        # Stop room streaming at its own terminator, preserving native actor AI.
        pointer=self.word(0,0xd81b+entry['room']*2)
        while self.word(5,pointer)!=0xffff:pointer+=6
        self.write({0x94:pointer,0x96:pointer})
        # Offline original-context extraction retains native world positions.
        self.camera(x-160,y-176)
        self.write({0x54a:x-64,0x54e:y})
        t=entry['type'];hit=self.word(1,0xab00+t*2)
        difficulty=self.read(0x84)
        for n in range(max(1,min(8,count))):
            base=0x580+n*0x40
            self.write({base+0x10:t,base+0x14:entry['variant'],base+0xa:x+n*30,
                        base+0xe:y,base+2:0x8018 if entry['flags']&0x8000 else 0,
                        base+0x28:hit&255,base+0x2a:hit>>8,base+0x26:add,
                        base+6:min(0x7fff,self.word(1,0xac00+t*2)+difficulty),
                        base+0x2e:self.word(1,0xad00+t*2)})
        self.entry=entry;self.target=0x580;self.elapsed=0
        snapshot=self.step(4)
        # Some original initializers need several fields before the first
        # complete OAM image exists. Finish that bounded setup even when the
        # workshop was paused before the user pressed Spawn.
        if t!=0x2a:
            for _ in range(12):
                if any(a['type']==t for a in snapshot['actors']):break
                snapshot=self.step(1)
        return snapshot

    def action(self,action):
        if action=='Gehen' and self.entry['type'] in (0x11,0x12,0x31,0x56,0x69):
            self.write({self.target+0x12:2,self.target+0x22:0})
            return
        if action=='Sterben' and self.entry['type']<128:
            t=self.entry['type'];base=self.target
            self.write({base+6:0,base+0x16:0,base+0x2e:0,
                base+0x10:self.bytes[0x8000+((0xae00+t)&0x7fff)],
                base+0x12:self.bytes[0x8000+((0xae80+t)&0x7fff)]})
            return
        if action=='Angriff' and self.entry['type'] in (18,49,86):
            state={18:7,49:9,86:8}[self.entry['type']]
            self.write({self.target+0x12:state,self.target+0x22:0,self.target+0x24:0,self.target+0x2c:0})
            return
        if action=='Springen' and self.entry['type'] in (18,49,86):
            right=self.arena_target>=self.read(self.target+0xa)
            self.write({self.target+0x1e:0xfffa,self.target+0x1c:0,self.target+0x18:0,
                        self.target+0x1a:1 if right else 0xffff,self.target+0x12:5 if right else 3})
            return
        if self.entry['type'] not in (0x11,0x12):
            if action!='Natürlich':raise ValueError('Für diese Figur ist nur der native Ablauf zugeordnet.')
            return
        if action=='Werfen':self.write({self.target+0x12:7,self.target+0x22:0})
        elif action=='Zerfallen':self.write({self.target+0x12:6,self.target+0x3c:0})
        elif action=='Gehen':self.write({self.target+0x12:2,self.target+0x22:0})

    @property
    def references(self):return self.folder/'enemy_packs/native-template'

    def close(self):
        if self.lua:
            try:self.command("enemy","flush")
            except (OSError,RuntimeError):pass
            try:self.lua.close()
            except OSError:pass
            self.lua=None
        if self.proc:
            if self.proc.poll() is None:self.proc.terminate()
            self.proc.wait(timeout=10);self.proc=None
        if self.log:self.log.close();self.log=None

    def __enter__(self):return self.start()
    def __exit__(self,*_):self.close()
