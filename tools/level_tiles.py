"""Stable per-cell graphics provenance, independent of the destination room.

Legacy low words still refer to the room's original tileset/layer. Explicit
references keep the source ID plus one (bits16..22) and layer (bit23).
They survive copying between rooms; flips/priority remain native word bits.
"""
EMPTY=0x1000000
SOURCE_COUNT=69


def source_name(number):return f'R-{number:02d}' if number<68 else 'R-23 / Mode7'


def bind(value,source,layer):
    if value==EMPTY or value>>16:return value
    return value|((source+1)<<16)|(0x800000 if layer=='back' else 0)


def resolve(value,default_source,default_layer):
    if value==EMPTY:return None
    source=(value>>16)&127
    return (source-1,'back' if value&0x800000 else 'front',value&65535) if source else (default_source,default_layer,value)


def valid(value):
    if type(value) is not int or value<0:return False
    if value==EMPTY:return True
    if value<=65535:return True
    return value<0x1000000 and 1<=((value>>16)&127)<=SOURCE_COUNT


def sources(r):
    result={r['tileset']}
    for layer in ('front','back'):
        for value in set(r['layers'][layer]):
            ref=resolve(value,r['tileset'],layer)
            if ref:result.add(ref[0])
    return result
