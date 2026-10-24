"""Create the editable introductory world locally from the user's own ROM."""
from enemy_workshop_native import ROOT
from level_assets import Assets,ensure_room
from level_project import Project,room


DEFAULT_PROJECT=ROOT/'artwork-local/level-editor/projects/Erste_Testwelt.sc4level.json'


def make_demo(path=DEFAULT_PROJECT):
    if path.exists():return path
    assets=Assets(ensure_room(0));original=assets.import_room()
    floor=next(w for w,c in zip(original['layers']['front'],original['collision']['front']) if c==1 and assets.tile(w).getbbox())
    p=Project();p.data['name']='Meine erste Testwelt';first=p.data['rooms'][0]
    first['name']='01 · Bauen und ausprobieren';first['width']=128;first['height']=32
    second=room('02 · Zweiter Raum',64,32);p.data['rooms'].append(second)
    for r in (first,second):
        w,h=r['width'],r['height'];r['spawn']=[64,128]
        r['layers']={k:[0x800]*(w*h) for k in ('front','back')};r['collision']={k:[0]*(w*h) for k in ('front','back')}
        for y in range(24,h):
            for x in range(w):r['layers']['front'][y*w+x]=floor;r['collision']['front'][y*w+x]=1
        # A short raised platform gives an immediate example for copy/paste.
        for x in range(28,36):r['layers']['front'][18*w+x]=floor;r['collision']['front'][18*w+x]=1
    first['actors']=[dict(id='E-DEMO',type=0x12,variant=0,x=440,y=152,flags=0x8000)]
    first['doors']=[dict(id='D-HIN',x=936,y=120,w=48,h=64,target=second['id'],target_x=64,target_y=128,trigger='up')]
    second['doors']=[dict(id='D-ZURUECK',x=32,y=120,w=48,h=64,target=first['id'],target_x=880,target_y=128,trigger='up')]
    p.save(path);return path
