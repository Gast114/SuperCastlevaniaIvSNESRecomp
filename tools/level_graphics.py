"""Compile mixed source artwork without SNES tile or BG-palette allocation."""
import struct
from level_tiles import EMPTY,resolve,sources
from level_assets import Assets,ensure_source


def compile_graphics(data,rom=None,build=None):
    """RGBA-equivalent RGB555+A atlas and per-room pixel/priority references.

    The native engine still handles collision, actors and objects. Background
    texels are host artwork so a foreign palette never changes existing tiles.
    Transparent texels stay zero; bit31 in a map cell is native BG priority.
    """
    assets={n:Assets(ensure_source(n,rom,build)) for n in sorted({n for r in data['rooms'] for n in sources(r)})}
    atlas=[b'\0'*128];indices={atlas[0]:0};cache={};maps=[]
    for r in data['rooms']:
        layers=[]
        for layer in ('front','back'):
            out=[]
            for value in r['layers'][layer]:
                ref=resolve(value,r['tileset'],layer)
                if ref is None:out.append(0);continue
                if ref not in cache:
                    n,source_layer,word=ref;image=assets[n].tile(word,source_layer)
                    colors=[(red>>3)|((green>>3)<<5)|((blue>>3)<<10)|0x8000 if alpha else 0 for red,green,blue,alpha in image.getdata()]
                    pixels=struct.pack('<64H',*colors)
                    if pixels not in indices:indices[pixels]=len(atlas);atlas.append(pixels)
                    cache[ref]=indices[pixels]|(0x80000000 if word&0x2000 else 0)
                out.append(cache[ref])
            layers.append(out)
        maps.append(layers)
    return atlas,maps
