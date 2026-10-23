"""Private native-engine session for the separate enemy workshop.

All guest writes, snapshots and captures live in an isolated copy. The artist's
running game, configuration, saves and original ROM are never modified.
"""
import json
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
            if self.entry['type'] in (17,18):family.update((2,45))
            family.update(self.entry.get('child_types',[]))
            result['actors']=[a for a in result['actors'] if a['type'] in family]
            main=next((a for a in result['actors'] if a['type']==self.entry.get('main_type',self.entry['type'])),None)
            if main:self.target=main['slot']
            result['target']=self.target
        return result

    def step(self,frames=1):
        if getattr(self,'entry',{}).get('boss'):hold_boss_stage(self,self.entry)
        play.advance(self.lua,frames);self.elapsed+=frames
        return self.snapshot()

    def camera(self,x,y):
        x=max(0,x);y=max(0,y)
        self.write({0x1c:x,0x1e:y,0x1280:x,0x12c0:x,0x1298:y,0x12d8:y})

    def spawn(self,entry,count=1):
        if entry.get('boss'):return spawn_boss(self,entry)
        self.command('loadfile',self.base)
        self.write({0x86:entry['room'],0x70:3})
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
        # The workshop's neutral stage is centred on the native camera, not on
        # a far-away level-record position which the retail culler would remove.
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
