"""Reusable terrain stamps with explicit graphics provenance and collision."""
import copy
import uuid
from level_tiles import EMPTY, bind, valid

CATEGORIES=('Alle','Steine','Plattformen','Bewegliche Plattformen','Treppen','Eigene')


def validate_part(part):
    if not isinstance(part,dict):raise ValueError('Ungültiges Bauteil.')
    width=part.get('width');tiles=part.get('tiles',[]);collision=part.get('collision',[]);mask=part.get('mask',[])
    if not isinstance(part.get('id'),str) or not part['id'] or not isinstance(part.get('name'),str) or not 1<=len(part['name'])<=80:
        raise ValueError('Bauteil benötigt eine ID und einen Namen mit höchstens 80 Zeichen.')
    if type(width) is not int or not 1<=width<=128 or not tiles or len(tiles)%width or len(tiles)>4096 or len(tiles)//width>64:
        raise ValueError('Bauteilgröße: höchstens 128 × 64 Kacheln und 4096 Felder.')
    if not all(valid(v) and (v==EMPTY or v>>16) for v in tiles):
        raise ValueError('Bauteile benötigen eindeutige Grafikquellen.')
    if len(collision)!=len(tiles) or not all(type(v) is int and 0<=v<=65535 for v in collision):
        raise ValueError('Ungültige Bauteilkollision.')
    if len(mask)!=len(tiles) or not all(type(v) is bool for v in mask) or not any(mask):
        raise ValueError('Ungültige oder leere Bauteilmaske.')
    return part


def builtin_parts(assets):
    from level_assets import collision_value
    result=[]
    def add(identifier,name,category,source,width,words,repeat=False,collisions=None):
        asset=assets.get(source)
        if asset is None:return
        part=dict(id=identifier,name=name,category=category,width=width,
            tiles=[bind(v,source,'front') if v!=EMPTY else EMPTY for v in words],
            collision=collisions if collisions is not None else [collision_value(v,asset.meta['limits']) if v!=EMPTY else 0 for v in words],
            mask=[v!=EMPTY for v in words],repeatable=repeat)
        result.append(validate_part(part))
    block=[0x2801,0x2802,0x2803,0x2804]
    add('block-a03','Stein · A03','Steine',2,2,block)
    add('platform-a03','Steinplattform · A03','Plattformen',2,2,block,True)
    # These graphics belong to A02's second gameplay plane. The live ring at
    # F10 has solid class 1; tile-class 3 is not a flat raw collision value.
    add('platform-a02','Plattform · A02 / F10','Plattformen',1,2,[0x2c19,0x2c1a,0x2c1b,0x2c1c],True,collisions=[1]*4)
    add('junction-a03','Stein mit Treppenanschluss','Steine',2,2,[0x2801,0x2802,0x2805,0x2804])
    for direction in ('right','left'):
        words=[EMPTY]*16
        for x in range(4):words[(3-x if direction=='right' else x)*4+x]=0x280e if direction=='right' else 0x680f
        add('stairs-'+direction,'Treppe · '+('rechts hoch' if direction=='right' else 'links hoch'),'Treppen',2,4,words)
    return result


def repeat_part(part,count):
    if type(count) is not int or not 1<=count<=32:raise ValueError('Plattformlänge: 1 bis 32 Steine.')
    result=copy.deepcopy(part)
    if not part.get('repeatable'):return result
    width=part['width'];height=len(part['tiles'])//width
    for field in ('tiles','collision','mask'):
        result[field]=[v for y in range(height) for v in part[field][y*width:(y+1)*width]*count]
    result['width']=width*count
    return validate_part(result)


def capture_part(r,layer,rect,name):
    x1,y1,x2,y2=rect
    if not (0<=x1<=x2<r['width'] and 0<=y1<=y2<r['height']):raise ValueError('Die Auswahl liegt außerhalb des Raums.')
    cells=[y*r['width']+x for y in range(y1,y2+1) for x in range(x1,x2+1)]
    tiles=[bind(r['layers'][layer][i],r['tileset'],layer) for i in cells]
    return validate_part(dict(id='P-'+uuid.uuid4().hex[:12],name=name.strip(),category='Eigene',width=x2-x1+1,
        tiles=tiles,collision=[r['collision'][layer][i] for i in cells],mask=[v!=EMPTY for v in tiles]))


def pick_connected_part(r,layer,x,y):
    """Pick one connected collision surface; preserve holes and the other plane."""
    width,height=r['width'],r['height']
    if not 0<=x<width or not 0<=y<height:return None
    value=r['collision'][layer][y*width+x]
    if not value:return None
    pending=[(x,y)];cells=set();left=right=x;top=bottom=y
    while pending:
        xx,yy=pending.pop()
        if (xx,yy) in cells or not 0<=xx<width or not 0<=yy<height or r['collision'][layer][yy*width+xx]!=value:continue
        cells.add((xx,yy));left=min(left,xx);right=max(right,xx);top=min(top,yy);bottom=max(bottom,yy)
        if len(cells)>4096 or right-left>=128 or bottom-top>=64:
            raise ValueError('Die verbundene Fläche ist zu groß. Bitte mit „Auswahl“ einen kleineren Ausschnitt wählen.')
        pending.extend(((xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)))
    rect=(left,top,right,bottom);part=capture_part(r,layer,rect,'Aufgenommenes Bauteil')
    part['mask']=[(xx,yy) in cells for yy in range(top,bottom+1) for xx in range(left,right+1)]
    return part,rect
