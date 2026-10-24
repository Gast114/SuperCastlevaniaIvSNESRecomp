"""Native room assets and exact 32px blocks for the visual level editor."""
import json
from pathlib import Path
import struct
import threading
from PIL import Image,ImageOps
from enemy_workshop_native import NativeSession,ROOT,play
from enemy_resources import ROM_SHA256
from level_project import room

CACHE=ROOT/'artwork-local/level-editor/rooms'
_locks={}


def collision_value(tile,limits):
    value=tile&1023
    if not limits[0]<=value<limits[14]:return 0
    values=(1,2,3,4,5,65535,7,8,9,10,11,0x8000,6)
    for n,end in enumerate(limits[1:14]):
        if value<end:
            result=values[n]
            return result^((tile>>14)&1) if n in (1,2,5,11) else result
    return 0


def ensure_room(number,rom=None,build=None):
    if type(number) is not int or not 0<=number<68:raise ValueError('Originalraum muss zwischen 0 und 67 liegen.')
    with _locks.setdefault(number,threading.Lock()):return _ensure_room(number,rom,build)


def _ensure_room(number,rom=None,build=None):
    folder=CACHE/f'{number:02d}';manifest=folder/'room.json'
    if manifest.is_file():
        data=json.loads(manifest.read_text())
        if data.get('version')==1 and data.get('rom_sha256')==ROM_SHA256 and all((folder/n).is_file() for n in ('ram.bin','video.bin')):return folder
    folder.mkdir(parents=True,exist_ok=True);s=NativeSession(rom,build,folder=folder/'capture')
    try:
        s.start();s.command('enemy','capture off')
        if number:
            s.command('loadfile',s.base);s.write({0x86:number,0x70:3})
            for _ in range(900):
                play.advance(s.lua,1)
                if s.read(0x70)==5 and s.read(0x3c)==0:break
            else:raise ValueError('Dieser Originalraum konnte nicht vollständig geladen werden.')
        s.command('wram',folder/'ram.bin');s.command('dump',folder/'video.bin')
        ppu=json.loads(s.command('ppu'));ram=(folder/'ram.bin').read_bytes()
        w=lambda a:struct.unpack_from('<H',ram,a)[0]
        data=dict(version=1,rom_sha256=ROM_SHA256,room=number,ppu=ppu,
                  width=max(256,w(0xa2)+256),height=max(256,w(0xa6)+224),
                  spawn=[w(0x54a),w(0x54e)],limits=[w(a) for a in range(0xc8,0xe6,2)],
                  camera=[w(0x1c),w(0x1e)],supported=(ppu['bgmode']&7)==1)
        manifest.write_text(json.dumps(data,indent=2));return folder
    finally:s.close()


class Assets:
    def __init__(self,folder):
        self.folder=Path(folder);self.meta=json.loads((self.folder/'room.json').read_text())
        self.ram=(self.folder/'ram.bin').read_bytes();self.video=(self.folder/'video.bin').read_bytes()
        self.vram=struct.unpack_from('<32768H',self.video);self.colors=struct.unpack_from('<256H',self.video,0x10000)
        self.cache={}

    def tile(self,word,layer='front'):
        key=(word,layer)
        if key in self.cache:return self.cache[key]
        spec=self.meta['ppu']['layers'][0 if layer=='front' else 1];base=(spec['tiles']+(word&1023)*16)&32767
        palette=(word>>10&7)*16;pixels=[]
        for y in range(8):
            a=self.vram[(base+y)&32767];b=self.vram[(base+y+8)&32767]
            for x in range(8):
                bit=7-x;v=((a>>bit)&1)|(((a>>(bit+8))&1)<<1)|(((b>>bit)&1)<<2)|(((b>>(bit+8))&1)<<3)
                c=self.colors[palette+v];expand=lambda n:(n<<3)|(n>>2)
                pixels.append((expand(c&31),expand(c>>5&31),expand(c>>10&31),255 if v else 0))
        image=Image.new('RGBA',(8,8));image.putdata(pixels)
        if word&0x4000:image=ImageOps.mirror(image)
        if word&0x8000:image=ImageOps.flip(image)
        self.cache[key]=image;return image

    def block(self,index,layer='front'):
        address=0x6000 if layer=='front' else 0xc000
        return list(struct.unpack_from('<16H',self.ram,address+(index&255)*32))

    def import_room(self):
        if not self.meta['supported']:raise ValueError('Mode7-Räume benötigen einen eigenen Kartenmodus und sind noch nicht importierbar.')
        if self.meta['height']>256:raise ValueError('Vertikale Originalkarten folgen separat. Eigene hohe Räume sind schon möglich.')
        width=min(8192,self.meta['width'])//8;r=room(f'Original R-{self.meta["room"]:02d}',width,32,self.meta['room'])
        for layer,base in (('front',0x8000),('back',0xe000)):
            for y in range(32):
                for x in range(width):
                    at=base+(x//32)*128+(y//4)*16+(x//4%8)*2
                    if at+2>len(self.ram):continue
                    m=struct.unpack_from('<H',self.ram,at)[0];xx=3-x%4 if m&0x8000 else x%4;yy=3-y%4 if m&0x4000 else y%4
                    flip=(0x4000 if m&0x8000 else 0)|(0x8000 if m&0x4000 else 0)
                    word=self.block(m&255,layer)[yy*4+xx]^flip
                    r['layers'][layer][y*width+x]=word;r['collision'][layer][y*width+x]=collision_value(word,self.meta['limits'])
        r['spawn']=[min(self.meta['spawn'][0],width*8-1),min(self.meta['spawn'][1],255)]
        r['collision_mode']=struct.unpack_from('<H',self.ram,0xae)[0]
        raw=NativeSession.__new__(NativeSession);raw.bytes=(ROOT/'Super Castlevania IV (USA).sfc').read_bytes()
        from monster_model import definitions
        allowed={m['type'] for m in definitions(raw.read_catalog(),raw.bytes)}
        pointer=raw.word(0,0xd81b+self.meta['room']*2);special=0
        for n in range(1024):
            at=5*0x8000+((pointer+n*6)&0x7fff);flags,yy,t,var=struct.unpack_from('<HHBB',raw.bytes,at)
            if flags==65535:break
            xx=flags&0xffc;yy&=0xffc
            if flags&3 or t not in allowed:special+=1;continue
            if xx<width*8 and yy<256:r['actors'].append(dict(id=f'E-{len(r["actors"]):03d}',type=t,variant=var,x=xx,y=yy,flags=flags))
        r['source_note']=f'{special} native Spezial-/Dekorobjekte benötigen noch eigene Editorwerkzeuge.' if special else ''
        return r
