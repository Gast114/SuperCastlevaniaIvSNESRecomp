"""Persistent, non-overwriting artist files shared by workshop and game import."""
import hashlib
import html
import json
import shutil
import time
from pathlib import Path
from PIL import Image
from enemy_hd import pixel_hash,pack

POSE_NAMES={0x8af4:'Gehen_01',0x8b05:'Gehen_02',0x8b1b:'Wurf_01_Ausholen',
            0x8b30:'Wurf_02_Werfen',0x8b4d:'Wurf_03_Ausklang',
            0x900c:'Drehung_01',0x9011:'Drehung_02',0x9016:'Drehung_03'}


class Workspace:
    def __init__(self,folder):
        self.folder=Path(folder).resolve();self.folder.mkdir(parents=True,exist_ok=True)
        for name in ('references','artwork'):(self.folder/name).mkdir(exist_ok=True)
        self.path=self.folder/'project.json'
        self.data=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {
            'version':1,'name':'Gegner-Werkstatt','frames':[],'work_templates':{}}
        self.data.setdefault('work_templates',{})
        for frame in self.data['frames']:
            frame.setdefault('component','__teil-' in frame['id'])
            frame.setdefault('label',Path(frame['image']).stem.replace('_',' '))
        self.frames={f['id']:f for f in self.data['frames']}
        self.identities={}
        for frame in self.data['frames']:
            if frame.get('pixel_identity'):self.identities[frame['pixel_identity']]=frame['image']
        self.cache={};self.last_error=''
        self.invalid=set()

    def ingest(self,source,allowed_ids=None):
        try:manifest=json.loads((Path(source)/'enemies.json').read_text())
        except (ValueError,OSError):return 0
        added=0
        for frame in manifest['frames']:
            if allowed_ids is not None and frame['id'] not in allowed_ids:continue
            if frame['id'] in self.frames:continue
            path=Path(source)/frame['reference']
            try:
                with Image.open(path) as loaded:
                    native=loaded.convert('RGBA');native.load()
            except OSError:continue
            actor=frame['actor_type'];pose=frame['pose']
            family='Skelett' if actor in (17,18) else 'Knochen' if actor==2 else 'Zerfall_Effekt' if actor==45 else f'Figur_{actor:02X}'
            identity=family+':'+pixel_hash(native)
            name=self.identities.get(identity)
            is_part='__teil-' in frame['id']
            label=POSE_NAMES.get(pose,f'Pose_{pose:04X}')
            if name is None:
                suffix='_Teil_'+frame['id'].rsplit('__teil-',1)[1].zfill(2) if is_part else ''
                stem=family+'_'+label+suffix;name=stem+'.png';number=2
                while (self.folder/'artwork'/name).exists() or (self.folder/'references'/name).exists():
                    name=f'{stem}_{number:02d}.png';number+=1
                shutil.copy2(path,self.folder/'references'/name)
                size=tuple(round(n*129/32) for n in native.size)
                working=native.resize(size,Image.Resampling.NEAREST)
                working.save(self.folder/'artwork'/name)
                self.data['work_templates'][name]=pixel_hash(working)
                self.identities[identity]=name
            mapping=dict(frame,image=name,reference=name,pixel_identity=identity,
                         component=is_part,label=family+' '+label.replace('_',' '))
            # Reused identical component images still keep a meaningful label.
            if is_part:mapping['label']=family+' '+label.replace('_',' ')+' · Teil '+frame['id'].rsplit('__teil-',1)[1]
            self.frames[frame['id']]=mapping;self.data['frames'].append(mapping);added+=1
        if added:
            temporary=self.path.with_suffix('.tmp.json')
            temporary.write_text(json.dumps(self.data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            temporary.replace(self.path)
            self.gallery()
        return added

    def coverage(self):
        body={f['pose'] for f in self.frames.values() if f['actor_type'] in (17,18) and not f['component']}
        bone={f['pose'] for f in self.frames.values() if f['actor_type']==2 and not f['component']}
        expected_body={0x8af4,0x8b05,0x8b1b,0x8b30,0x8b4d}
        expected_bone={0x900c,0x9011,0x9016}
        return {'skeleton_body':len(body&expected_body),'skeleton_body_expected':5,
                'bone_images':len(bone&expected_bone),'bone_images_expected':3,
                'skeleton_complete':expected_body<=body and expected_bone<=bone}

    def gallery(self):
        cards={False:[],True:[]}
        for name,frame in {f['image']:f for f in self.frames.values()}.items():
            safe=html.escape(name,quote=True)
            cards[frame['component']].append(f'<article><img src="artwork/{safe}" alt="{safe}"><p>{html.escape(frame["label"])}</p>'
                                             f'<a href="artwork/{safe}">{safe}</a></article>')
        counts=self.coverage()
        (self.folder/'VORLAGEN.html').write_text(
            '<!doctype html><html lang="de"><meta charset="utf-8"><title>Gegner-Werkstatt – PNG-Sammlung</title>'
            '<style>body{font:18px system-ui;background:#151b22;color:#eef1f5;margin:32px auto;max-width:1400px;padding:0 24px}'
            'main{display:flex;flex-wrap:wrap;gap:16px}article{width:260px;padding:18px;background:#242d36;border-radius:12px}'
            'img{width:250px;height:250px;object-fit:contain;image-rendering:pixelated;background:repeating-conic-gradient(#404954 0% 25%,#353f49 0% 50%) 0/18px 18px}'
            'a{color:#9bd2ff;font-size:13px;overflow-wrap:anywhere}summary{cursor:pointer;padding:20px;font-weight:bold}</style>'
            '<h1>Deine aufgenommenen Gegner-PNGs</h1><p>Nur PNGs in <strong>artwork</strong> bearbeiten. Dateinamen, Transparenz und vollständige Bildfläche behalten. '
            'Originale in <strong>references</strong> und <strong>project.json</strong> unverändert aufbewahren.</p>'
            f'<p>Skelett: {counts["skeleton_body"]}/5 Körperposen; Knochen: {counts["bone_images"]}/3 Drehbilder. '
            'Andere Figuren sind nur im bisher tatsächlich aufgenommenen Umfang enthalten.</p>'
            '<h2>Ganze Posen, Geschosse und Effekte</h2><main>'+''.join(cards[False])+ '</main>'
            '<details><summary>Optionale native Einzelteile</summary><p>Eine neue ganze Pose hat Vorrang vor ihren Einzelteilen. '
            'Identische Teilbilder werden gemeinsam verwendet.</p><main>'+''.join(cards[True])+'</main></details></html>',encoding='utf-8')

    def image(self,identifier,custom=False):
        frame=self.frames.get(identifier)
        if not frame:return None
        native=self.folder/'references'/frame['reference']
        path=self.folder/('artwork' if custom else 'references')/frame['image']
        try:
            stamp=(path.stat().st_mtime_ns,path.stat().st_size)
            cached=self.cache.get(path)
            if cached and cached[0]==stamp:return cached[1]
            with Image.open(path) as loaded:
                w,h=loaded.size;dw,dh=frame['display_size']
                if loaded.format!='PNG' or max(w,h)>4096 or abs(w/dw-h/dh)>1/min(dw,dh):
                    raise ValueError('Gültiges proportionales PNG mit vollständiger Bildfläche erforderlich')
                value=loaded.convert('RGBA');value.load()
            # An unedited enlarged template stays native, without pretending to
            # be a new HD drawing. Invalid in-progress saves retain good pixels.
            if custom and pixel_hash(value)==self.data['work_templates'].get(frame['image']):
                value=self.image(identifier,False)
            self.cache[path]=(stamp,value)
            self.invalid.discard(path)
            if not self.invalid:self.last_error=''
            return value
        except (OSError,ValueError) as error:
            self.last_error=f'Letztes gültiges Bild bleibt sichtbar: {path.name}'
            self.invalid.add(path)
            return self.cache.get(path,(None,None))[1] or self.image(identifier,False) if custom else self.cache.get(path,(None,None))[1]

    def edited(self,identifier):
        frame=self.frames.get(identifier)
        if not frame:return False
        image=self.image(identifier,True)
        return image is not None and pixel_hash(image)!=pixel_hash(self.image(identifier,False))

    def replace(self,identifier,source):
        frame=self.frames[identifier];source=Path(source)
        with Image.open(source) as image:
            image.load();w,h=image.size
            if image.format!='PNG' or max(w,h)>4096 or min(w,h)<1:
                raise ValueError('Bitte ein gültiges PNG bis 4096×4096 Pixel auswählen.')
            dw,dh=frame['display_size']
            if abs(w/dw-h/dh)>1/min(dw,dh):
                raise ValueError('Die vollständige Bildfläche proportional beibehalten, nicht beschneiden.')
        target=self.folder/'artwork'/frame['image']
        if source.resolve()==target.resolve():return
        backup=self.folder/'history'/str(time.time_ns());backup.mkdir(parents=True)
        shutil.copy2(target,backup/target.name)
        pending=target.with_suffix('.pending.png');shutil.copy2(source,pending);pending.replace(target)
        self.cache.pop(target,None)

    def build_pack(self,destination):return pack(self.folder,Path(destination))
