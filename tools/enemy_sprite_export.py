"""Render original metasprite poses against a measured native graphics context.

This is a static art export, never an animation simulation. Pose ownership must
come from a proved ROM animation/handler reference. IDs and anchors match the
game's enemy renderer; a later different VRAM pattern safely gets another ID.
"""
import struct
from PIL import Image


def descriptor(rom,pose):
    if not 0x8000<=pose<=0xffff:raise ValueError('Invalid original pose address')
    offset=0x20000+(pose&0x7fff)
    count=rom[offset]
    if not 1<=count<=32 or offset+1+count*4>len(rom):
        raise ValueError('Invalid original metasprite descriptor')
    return [struct.unpack_from('<bbH',rom,offset+1+i*4) for i in range(count)]


class Graphics:
    def __init__(self,video,obsel):
        if len(video)!=0x10420:raise ValueError('Invalid native video context')
        self.vram=struct.unpack_from('<32768H',video)
        self.palette=struct.unpack_from('<256H',video,0x10000)
        self.base1=(obsel&7)<<13
        self.base2=self.base1+(((obsel&0x18)+8)<<9)
        def expand(value):return (value<<3)|(value>>2)
        self.rgba=[(expand(c&31),expand((c>>5)&31),expand((c>>10)&31),255) for c in self.palette]

    def pixel(self,attr,size,x,y):
        if attr&0x4000:x=size-1-x
        if attr&0x8000:y=size-1-y
        tile=((((attr&255)>>4)+(y>>3))<<4)|(((attr&15)+(x>>3))&15)
        base=self.base2 if attr&256 else self.base1
        addr=(base+tile*16+(y&7))&0x7fff;bit=7-(x&7)
        value=self.vram[addr]|self.vram[(addr+8)&0x7fff]<<16
        index=(value>>bit&1)|(value>>(bit+7)&2)|(value>>(bit+14)&4)|(value>>(bit+21)&8)
        return index,self.rgba[128+((attr>>9)&7)*16+index]


def render_pose(rom,actor_type,pose,video,obsel,tile_add=0,priority=0):
    """Return (frame metadata, RGBA) pairs for a whole pose and all its parts.

    The caller supplies a live measured tile offset/priority from this actor's
    own graphics context. No ROM, PPU or guest state is modified.
    """
    parts=descriptor(rom,pose)
    size=96;anchor=48
    for x,y,attr in parts:
        extent=16 if attr&0x2000 else 8
        if min(x,y)<-48 or x+extent>48 or y+extent>48:size=256;anchor=128
    graphics=Graphics(video,obsel)
    indices=bytearray(size*size)
    whole=Image.new('RGBA',(size,size));whole_pixels=whole.load();pieces=[]
    for index in reversed(range(len(parts))):
        x,y,raw=parts[index];extent=16 if raw&0x2000 else 8
        attr=raw|0x2000
        if priority&0x8000:attr=(attr&0xcfff)|((priority*2&255)<<8)
        attr=(attr+tile_add)&0xffff
        if min(x+anchor,y+anchor)<0 or x+anchor+extent>size or y+anchor+extent>size:
            raise ValueError('Original pose exceeds supported 256px canvas')
        piece=Image.new('RGBA',(size,size));pixels=piece.load()
        for py in range(extent):
            for px in range(extent):
                value,color=graphics.pixel(attr,extent,px,py)
                if value:
                    dx,dy=x+anchor+px,y+anchor+py
                    indices[dy*size+dx]=value
                    whole_pixels[dx,dy]=color;pixels[dx,dy]=color
        pieces.append((index,piece))
    if not any(indices):raise ValueError('Pose is empty in this native graphics context')
    digest=14695981039346656037
    for value in indices:digest=((digest^value)*1099511628211)&0xffffffffffffffff
    family='skelett' if actor_type in (17,18) else 'gegner'
    identifier=f'{family}-{actor_type:04x}_pose-{pose:04x}_{digest:016x}'
    metadata=dict(id=identifier,actor_type=actor_type,pose=pose,
                  reference=identifier+'.png',display_size=[size,size],anchor=[anchor,anchor])
    result=[(metadata,whole)]
    for index,piece in sorted(pieces):
        part_id=identifier+f'__teil-{index}'
        result.append((dict(metadata,id=part_id,reference=part_id+'.png'),piece))
    return result
