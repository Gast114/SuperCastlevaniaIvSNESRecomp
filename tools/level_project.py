"""Editable Castlevania IV projects; originals remain external immutable assets."""
import copy
import json
from pathlib import Path
import uuid
from enemy_resources import ROM_SHA256
from level_tiles import EMPTY,valid

LAYERS=('front','back')
MAX_CELLS=262144


def room(name='Neuer Raum',width=128,height=32,tileset=0):
    identifier='R-'+uuid.uuid4().hex[:8].upper()
    return dict(id=identifier,name=name,width=width,height=height,tileset=tileset,spawn=[64,120],collision_mode=3,
        layers={k:[EMPTY]*(width*height) for k in LAYERS},
        collision={k:[0]*(width*height) for k in LAYERS},actors=[],doors=[])


def validate(data):
    if data.get('version') not in (1,2) or data.get('rom_sha256')!=ROM_SHA256:raise ValueError('Projektversion oder Original-ROM passt nicht.')
    rows=data.get('rooms',[])
    if not 1<=len(rows)<=64:raise ValueError('Ein Projekt benötigt 1 bis 64 Räume.')
    ids={r['id'] for r in rows}
    if len(ids)!=len(rows):raise ValueError('Raum-IDs müssen eindeutig sein.')
    if data.get('start_room') not in ids:raise ValueError('Der Startraum fehlt.')
    for r in rows:
        w,h=r['width'],r['height']
        if type(w) is not int or type(h) is not int or not 32<=w<=1024 or not 28<=h<=512 or w*h>MAX_CELLS:
            raise ValueError('Raumgröße: 32–1024 × 28–512 Kacheln, höchstens 262144 Felder.')
        if type(r['tileset']) is not int or not 0<=r['tileset']<68:raise ValueError('Ungültiger Original-Grafiksatz.')
        if type(r.get('collision_mode',0)) is not int or not 0<=r.get('collision_mode',0)<=3:raise ValueError('Ungültiger Kollisionsmodus.')
        for key in LAYERS:
            for field in ('layers','collision'):
                a=r[field][key]
                check=valid if field=='layers' and data['version']>=2 else lambda v:type(v) is int and 0<=v<=65535
                if len(a)!=w*h or not all(check(v) for v in a):raise ValueError('Ungültige Karten- oder Kollisionsdaten.')
        for xy in [r['spawn']]+[[a['x'],a['y']] for a in r['actors']]:
            if len(xy)!=2 or any(type(v) is not int for v in xy) or not 0<=xy[0]<w*8 or not 0<=xy[1]<h*8:raise ValueError('Startpunkt/Gegner liegt außerhalb des Raums.')
        if len(r['actors'])>128 or len(r['doors'])>64:raise ValueError('Zu viele Gegner oder Ausgänge in einem Raum.')
        for a in r['actors']:
            if type(a['type']) is not int or not 0<a['type']<=0x8d or type(a.get('variant',0)) is not int or not 0<=a.get('variant',0)<=255:
                raise ValueError('Ungültiger Monster-Code oder Variante.')
            if type(a.get('flags',0)) is not int or not 0<=a.get('flags',0)<=65535:raise ValueError('Ungültige Monster-Ebene.')
        objects=r['actors']+r['doors']
        if len({a['id'] for a in objects})!=len(objects):raise ValueError('Objekt-IDs müssen je Raum eindeutig sein.')
        for d in r['doors']:
            if any(type(d[k]) is not int for k in ('x','y','w','h','target_x','target_y')) or d.get('target_plane',0) not in (0,1):raise ValueError('Ungültige Ausgangswerte.')
            if d['target'] not in ids:raise ValueError('Ausgang verweist auf einen fehlenden Raum.')
            target=next(x for x in rows if x['id']==d['target'])
            if d.get('trigger','up') not in ('up','touch'):raise ValueError('Ungültiger Ausgangsauslöser.')
            if not 0<=d['x']<w*8 or not 0<=d['y']<h*8 or not 8<=d['w']<=256 or not 8<=d['h']<=256:
                raise ValueError('Ungültiger Ausgangsbereich.')
            if not 0<=d['target_x']<target['width']*8 or not 0<=d['target_y']<target['height']*8:raise ValueError('Ausgangsziel liegt außerhalb des Zielraums.')
    return data


class Project:
    def __init__(self,data=None):
        r=room();self.data=validate(copy.deepcopy(data) if data else dict(version=2,rom_sha256=ROM_SHA256,name='Mein Castlevania-Level',start_room=r['id'],rooms=[r]))
        self.data['version']=2
        self.path=None;self.undo_stack=[];self.redo_stack=[];self.dirty=False;self.transaction=None

    @classmethod
    def load(cls,path):
        result=cls(json.loads(Path(path).read_text(encoding='utf-8')));result.path=Path(path);return result

    def save(self,path=None):
        path=Path(path or self.path);validate(self.data);path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_name(path.name+'.tmp');temporary.write_text(json.dumps(self.data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8');temporary.replace(path)
        self.path=path;self.dirty=False

    def get(self,identifier):return next(r for r in self.data['rooms'] if r['id']==identifier)

    def begin(self,label):
        if self.transaction is None:self.transaction=(label,copy.deepcopy(self.data))

    def commit(self):
        if self.transaction:
            label,before=self.transaction;self.transaction=None
            if before!=self.data:
                self.undo_stack.append((label,before,copy.deepcopy(self.data)));self.undo_stack=self.undo_stack[-24:]
                self.redo_stack=[];self.dirty=True

    def undo(self):
        self.commit()
        if not self.undo_stack:return
        item=self.undo_stack.pop();self.redo_stack.append(item);self.data=copy.deepcopy(item[1]);self.dirty=True

    def redo(self):
        if not self.redo_stack:return
        item=self.redo_stack.pop();self.undo_stack.append(item);self.data=copy.deepcopy(item[2]);self.dirty=True

    def add_room(self,source=None,tileset=0):
        self.begin('Raum hinzufügen');r=copy.deepcopy(source) if source else room(tileset=tileset)
        r['id']='R-'+uuid.uuid4().hex[:8].upper();r['name']+=' (Kopie)' if source else ''
        if source:r['doors']=[]
        self.data['rooms'].append(r);self.commit();return r

    def resize(self,r,width,height,name=None,collision_mode=None):
        if not 32<=width<=1024 or not 28<=height<=512 or width*height>MAX_CELLS:raise ValueError('Ungültige Raumgröße.')
        if any(a['x']>=width*8 or a['y']>=height*8 for a in r['actors']):raise ValueError('Beim Verkleinern würden Gegner abgeschnitten.')
        if any(d['x']>=width*8 or d['y']>=height*8 for d in r['doors']):raise ValueError('Beim Verkleinern würden Ausgänge abgeschnitten.')
        if any(d['target']==r['id'] and (d['target_x']>=width*8 or d['target_y']>=height*8) for q in self.data['rooms'] for d in q['doors']):raise ValueError('Ein Ausgangsziel würde außerhalb dieses Raums liegen.')
        self.begin('Raumgröße')
        if name is not None:r['name']=name
        if collision_mode is not None:r['collision_mode']=collision_mode
        for kind in ('layers','collision'):
            for key in LAYERS:
                out=[EMPTY if kind=='layers' else 0]*(width*height)
                for y in range(min(height,r['height'])):
                    n=min(width,r['width']);out[y*width:y*width+n]=r[kind][key][y*r['width']:y*r['width']+n]
                r[kind][key]=out
        r['width'],r['height']=width,height;r['spawn']=[min(r['spawn'][0],width*8-1),min(r['spawn'][1],height*8-1)]
        self.commit()


def paint(r,layer,x,y,values,collisions=None,brush_width=1):
    for i,value in enumerate(values):
        xx,yy=x+i%brush_width,y+i//brush_width
        if 0<=xx<r['width'] and 0<=yy<r['height']:
            at=yy*r['width']+xx;r['layers'][layer][at]=value
            if collisions is not None:r['collision'][layer][at]=collisions[i]
