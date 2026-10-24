"""Portable original monster resources, independent of a source-room load.

Graphics come straight from ROM using the retail 02:864A..87C5 codec. Only
palettes reuse prepared original contexts; no level or save state is restored.
The plan explicitly owns native OBJ slots so future placement can check budget.
"""
import json
import struct
from pathlib import Path

ROM_SHA256='0ef6f4cce5a2273fa49fe1ce724e0048a8e39c91da6b00dbb693fe1ba909177d'
RESOURCE_VERSION=1


def offset(address):
    bank=address>>16;word=address&65535
    if word<0x8000 or bank>=0x20:raise ValueError('Resource pointer outside original LoROM')
    return bank*0x8000+(word&0x7fff)


def word(rom,address):return int.from_bytes(rom[offset(address):offset(address)+2],'little')


def decompress(rom,address,limit=0x10000):
    """Bounded native LZ/runs decoder, including its 1024-byte circular history."""
    at=offset(address);end=at+word(rom,address);cursor=at+2
    if not cursor<=end<=len(rom):raise ValueError('Invalid compressed resource extent')
    ring=bytearray(1024);out=bytearray()
    def read():
        nonlocal cursor
        if cursor>=end:raise ValueError('Truncated original resource command')
        value=rom[cursor];cursor+=1;return value
    def emit(value):
        if len(out)>=limit:raise ValueError('Original resource exceeds bounded OBJ budget')
        ring[len(out)&1023]=value;out.append(value)
    while cursor<end:
        command=read()
        if command<0x80:
            source=(((command&3)<<8)|read())-0x3df
            for _ in range((command>>2)+2):emit(ring[source&1023]);source+=1
        elif command<0xa0:
            for _ in range(command&31):emit(read())
        elif command<0xc0:
            for _ in range((command&31)+2):emit(0);emit(read())
        else:
            value=read() if command<0xe0 else 0
            for _ in range((command&31)+2):emit(value)
    return bytes(out)


def resource(rom,actor):
    if type(actor) is not int or not 0<actor<128:raise ValueError('Invalid ordinary monster resource code')
    at=offset(0x01a900+actor*3)
    pointer=int.from_bytes(rom[at:at+3],'little')
    count=rom[offset(0x01aa80+actor)]
    return pointer,count


def ordinary_plan(rom,entry,first_slot=0):
    """Plan the native actor family; fixed global effects keep their base tiles.

    AA80 reserves 1KiB pages. A shared compressed stream can contain more than
    one variant uses, so upload exactly its declared reservation, with zero tail.
    """
    if type(first_slot) is not int or not 0<=first_slot<11:raise ValueError('Invalid first native OBJ slot')
    family={entry['type'],*entry.get('child_types',[])}
    death=rom[offset(0x01ae00+entry['type'])]
    if death:family.add(death)
    groups={}
    for actor in sorted(family,key=lambda t:t!=entry['type']):
        pointer,count=resource(rom,actor)
        if count in (0,255):continue
        if count>11:raise ValueError(f'M-{actor:04X}: no portable ordinary resource declaration')
        row=groups.setdefault(pointer,dict(pointer=pointer,pages=0,types=[]))
        row['pages']=max(row['pages'],count);row['types'].append(actor)
    slots={};blocks=[];slot=first_slot
    for row in groups.values():
        if slot+row['pages']>11:raise ValueError('Monster family exceeds native OBJ resource budget')
        decoded=decompress(rom,row['pointer'])
        size=row['pages']*1024
        blocks.append(dict(row,slot=slot,vram_word=0x6a00+slot*0x200,
                           tile_add=0xa0+slot*0x20,data=decoded[:size].ljust(size,b'\0')))
        for actor in row['types']:slots[actor]=blocks[-1]['tile_add']
        slot+=row['pages']
    return dict(blocks=blocks,tile_add=slots,pages=slot-first_slot,first_slot=first_slot,
                family=sorted(family),remaining_pages=11-slot)


def palette(library,entry):
    key=('boss' if entry.get('boss') else 'actor')+f'-{entry["type"]:02x}-v{entry.get("variant",0):02x}'
    prepared=Path(library)/'resources'/f'{key}-palette.bin'
    if prepared.is_file():
        data=prepared.read_bytes()
    else:
        index=json.loads((Path(library)/'library.json').read_text(encoding='utf-8'))
        profile=next((p for p in index['profiles'] if p['key']==key),{})
        context=profile.get('context')
        if not context:raise ValueError(f'{key}: Farbressource fehlt. Gegner_Werkstatt_starten.cmd bereitet sie einmalig vor.')
        data=Path(context['video']).read_bytes()[0x10000:0x10200]
    if len(data)!=512:raise ValueError('Invalid prepared original palette')
    return data


def write_bundle(path,colors,plan=None,full_palette=False):
    """Small graphics-only host transfer; contains no actors, level or CPU state."""
    if len(colors)!=512:raise ValueError('Expected original 256-color palette')
    blocks=plan['blocks'] if plan else []
    payload=bytearray(b'CV4OBJ1\0')+struct.pack('<HH',int(full_palette),len(blocks))
    for block in blocks:
        payload+=struct.pack('<HH',block['vram_word'],len(block['data']))+block['data']
    payload+=colors if full_palette else colors[256:]
    Path(path).write_bytes(payload)
    return Path(path)
