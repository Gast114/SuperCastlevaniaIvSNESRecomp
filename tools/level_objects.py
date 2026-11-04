"""Readonly sprite previews and verified portable native platform presets."""
import json
from pathlib import Path
from PIL import Image

PLATFORM_TYPE=0x17
PLATFORM_TRAVEL=80
MOVING_PLATFORMS=(
    dict(id='moving-horizontal',name='O-0017 · Waagerecht',kind='platform',type=PLATFORM_TYPE,variant=0,category='Bewegliche Plattformen'),
    dict(id='moving-vertical',name='O-0017 · Senkrecht',kind='platform',type=PLATFORM_TYPE,variant=1,category='Bewegliche Plattformen'),
)

def scene_objects(session,known):
    """Expose actual scene records as objects, retaining their native variant."""
    found=set((e['type'],e.get('variant',0)) for e in known);rows=[]
    for room in range(68):
        pointer=session.word(0,0xd81b+room*2)
        for n in range(1024):
            at=5*0x8000+((pointer+n*6)&32767);data=session.bytes[at:at+6];flags=int.from_bytes(data[:2],'little')
            if flags==65535:break
            t,var=data[4],data[5]
            if flags&3!=2 or not 0<t<128 or t==42 or (t,var) in found:continue
            found.add((t,var));rows.append(dict(type=t,variant=var,room=room,flags=flags,category='object',kind='event',native_family=2))
    return rows


def is_platform(actor):return actor.get('type')==PLATFORM_TYPE and actor.get('variant',0) in (0,1)


def resource_entry(actor):
    # Variants 0/1 change only the native motion axis. OBJ resource and pose
    # table are shared; both use the verified variant-0 palette context.
    return dict(type=actor['type'],variant=0 if is_platform(actor) else actor.get('variant',0))


def platform_bounds(actor):
    x,y=actor['x'],actor['y']
    return (x-16,y-8,x+16,y+8)


def platform_path(actor):
    x,y=actor['x'],actor['y']
    return (x,y,x-PLATFORM_TRAVEL,y) if actor.get('variant',0)==0 else (x,y,x,y-PLATFORM_TRAVEL)


def validate_platform(actor,width,height):
    if actor.get('kind')!='platform':return
    if not is_platform(actor):raise ValueError('Bewegliche Plattform: nur geprüfte waagerechte/senkrechte Varianten 0/1.')
    x,y,tx,ty=platform_path(actor)
    if min(x,tx)<16 or max(x,tx)>width-16 or min(y,ty)<8 or max(y,ty)>height-8:
        raise ValueError('Der 80-Pixel-Bewegungsweg der Plattform reicht über den Raumrand.')


class SpriteLibrary:
    """Use existing native PNGs without importing/writing an artist workspace."""
    def __init__(self,folder):
        self.folder=Path(folder);self.cache={};self.frames={};self.profiles={};self.by_type={}
        path=self.folder/'native-template/enemies.json'
        if path.is_file():
            for row in json.loads(path.read_text(encoding='utf-8'))['frames']:
                if '__teil-' in row['id']:continue
                self.frames[row['id']]=row;self.by_type.setdefault(row['actor_type'],[]).append(row)
        path=self.folder/'library.json'
        if path.is_file():
            self.profiles={(p['type'],p.get('variant',0)):p for p in json.loads(path.read_text(encoding='utf-8')).get('profiles',[]) if not p.get('preview_only')}
    def sprite(self,actor):
        entry=resource_entry(actor);key=(entry['type'],entry['variant'])
        if key in self.cache:return self.cache[key]
        profile=self.profiles.get(key,{})
        if actor['type']==14:return self.candle(actor)
        if actor['type']==0x81:
            path=self.folder.parent/'level-editor/bosses/mode7-body.png'
            if path.is_file():
                with Image.open(path) as source:picture=source.convert('RGBA')
                anchor=json.loads(path.with_suffix('.json').read_text())['anchor']
                if picture.getbbox():return (picture,tuple(anchor))
        if actor['type']>=128:
            path=self.folder.parent/f'level-editor/bosses/{actor["type"]:02x}-group.png'
            if path.is_file():
                with Image.open(path) as source:picture=source.convert('RGBA')
                anchor=json.loads(path.with_suffix('.json').read_text())['anchor']
                if picture.getbbox():return (picture,tuple(anchor))
        body=profile.get('main_type',actor['type'])
        preferred=[profile.get('context',{}).get('current_id'),*profile.get('main_frame_ids',[]),*profile.get('frame_ids',[])]
        candidates=[self.frames[i] for i in preferred if i in self.frames]
        candidates+=self.by_type.get(body,[]) if not candidates else []
        for frame in candidates:
            if frame['actor_type']!=body:continue
            reference=frame['reference']
            if Path(reference).name!=reference:continue
            try:
                with Image.open(self.folder/'native-template'/reference) as loaded:
                    image=loaded.convert('RGBA');image.load()
                size=tuple(frame['display_size'])
                if image.size!=size:image=image.resize(size,Image.Resampling.NEAREST)
                if image.getbbox():
                    result=(image,tuple(frame['anchor']));self.cache[key]=result;return result
            except OSError:continue
        self.cache[key]=None;return None
    def candle(self,actor):
        # $00:D771 creates actor $0E; $00:D233 selects the two fixed poses.
        # These global OBJ tiles already exist in every ordinary room.
        from enemy_sprite_export import render_pose
        from enemy_workshop_native import ROOT
        from level_assets import ensure_room,Assets
        key=('candle',0)
        if key not in self.cache:
            asset=Assets(ensure_room(0));rom=(ROOT/'Super Castlevania IV (USA).sfc').read_bytes()
            rows=render_pose(rom,14,0x80d2,asset.video,3,0,0x8018)
            meta,image=rows[0];self.cache[key]=(image,tuple(meta['anchor']))
        return self.cache[key]
    def thumbnail(self,actor,size):
        result=Image.new('RGBA',size,'#252c38');sprite=self.sprite(actor)
        if sprite:
            image=sprite[0];image=image.crop(image.getbbox());ratio=min((size[0]-6)/image.width,(size[1]-6)/image.height,3)
            image=image.resize((max(1,round(image.width*ratio)),max(1,round(image.height*ratio))),Image.Resampling.NEAREST)
            result.alpha_composite(image,((size[0]-image.width)//2,(size[1]-image.height)//2))
        return result
