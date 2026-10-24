"""Native arena/UI checks without screenshots or opening an image viewer."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
import tkinter as tk
import zipfile

from PIL import Image
from enemy_workshop import DEFAULT_WORKSPACE, preview
from enemy_workshop_assets import Workspace
from enemy_workshop_native import ROOT
from monster_model import actions, combat_stats, frame_groups, visible_frames
from monster_workshop import MonsterWorkshop, export_monster


def main():
    parent=ROOT/'artwork-local/enemy-workshop';parent.mkdir(parents=True,exist_ok=True)
    folder=Path(tempfile.mkdtemp(prefix='monster-check-',dir=parent))
    source=Workspace(DEFAULT_WORKSPACE);target=folder/'workspace'
    (target/'artwork').mkdir(parents=True);(target/'references').mkdir()
    data=copy.deepcopy(source.data);data['monster_names']={};data['monster_actions']={}
    data['frames']=[f for f in data['frames'] if f['actor_type'] in (2,7,17,18,45,49,61,86,105)]
    for frame in {f['image']:f for f in data['frames']}.values():
        shutil.copy2(source.folder/'artwork'/frame['image'],target/'artwork'/frame['image'])
        shutil.copy2(source.folder/'references'/frame['reference'],target/'references'/frame['reference'])
    (target/'project.json').write_text(json.dumps(data),encoding='utf-8')
    root=tk.Tk();root.withdraw();app=MonsterWorkshop(root,workspace=target,library=None)
    report={'passed':False,'image_viewer_used':False,'checks':[]}
    def wait(predicate,timeout=35):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            root.update()
            if predicate():return
            if not app.worker.is_alive():raise AssertionError(app.status.get())
            time.sleep(.01)
        raise AssertionError('Timeout: '+app.status.get())
    def spin(seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:root.update();time.sleep(.01)
    def passed(text):report['checks'].append(text);print('PASS:',text,flush=True)
    try:
        wait(lambda:bool(app.catalog) and bool(app.snapshot.get('actors')))
        assert app.picker.exists('M-0012') and not app.picker.exists('M-0002')
        assert len([m for m in app.monsters if m['type']==18])==1
        assert not any('Skelett' in app.picker.item(i,'text') for i in app.picker.get_children())
        passed('Monster codes group native variants; projectiles have no separate monster entry')
        app.name.set('Mein Testname');app.save_name()
        assert Workspace(target).data['monster_names']['M-0012']=='Mein Testname'
        passed('Artist name persists without changing the stable code')
        wait(lambda:len(app.trees['Gehen / Bewegen'].get_children())==2)
        attack=[app.workspace.frames[i] for i in app.trees['Angriff'].get_children()]
        assert {f['pose'] for f in attack if f['actor_type']==18}=={0x8b1b,0x8b30,0x8b4d}
        assert {f['pose'] for f in attack if f['actor_type']==2}=={0x900c,0x9011,0x9016}
        assert len(attack)==6
        assert not frame_groups({'type':17,'variant':0},app.workspace)['Angriff']
        assert not actions({'type':17})['Springen']
        passed('Walk/jump share two body PNGs; attack includes three body poses and three bone rotations')
        wait(lambda:app.snapshot['live_stats']['y']==168)
        stats=combat_stats(app.rom,app.entry,app.snapshot['live_stats'])
        assert (stats['current_hp'],stats['base_hp'],stats['contact_damage'])==(48,48,3)
        assert (stats['hitbox_width'],stats['hitbox_height'])==(24,46)
        assert app.snapshot['arena']['floor']==192
        passed('Flat arena settles at y168; original HP48, contact damage3, live hitbox24x46')
        assert tuple(map(str,app.comparison.item('hp','values')))==('Gesundheit','48','64 (+16)')
        assert tuple(map(str,app.comparison.item('contact','values')))==('Kontaktschaden','3','3')
        app.preview_mode.set('New Game+');app.change_mode()
        wait(lambda:app.snapshot.get('live_stats',{}).get('quest')==1 and app.snapshot['live_stats']['hp']==64)
        assert 'Live-Szene: New Game+' in app.stats.get()
        app.preview_mode.set('Normal');app.change_mode()
        wait(lambda:app.snapshot.get('live_stats',{}).get('quest')==0 and app.snapshot['live_stats']['hp']==48)
        passed('Separate Normal/NG+ values and native preview switch show HP48/64 and unchanged contact3')
        app.run_action('Springen');wait(lambda:app.active_action=='Springen' and app.snapshot['live_stats']['y']<140)
        wait(lambda:app.snapshot['live_stats']['y']==168)
        passed('Original jump rises and lands on the neutral floor')
        app.run_action('Angriff');wait(lambda:app.active_action=='Angriff' and any(a['type']==2 for a in app.snapshot['actors']))
        passed('Native attack emits an actual bone in the same monster group')
        app.single_step();spin(.5);tick=app.snapshot['tick'];spin(.4);assert app.snapshot['tick']==tick
        app.single_step();wait(lambda:app.snapshot['tick']>tick)
        passed('Pause and single field stepping hold and advance the native engine')
        spin(.3);snapshot=copy.deepcopy(app.snapshot)
        actor=next(a for a in snapshot['actors'] if a['type']==18);identifier=actor['id']
        wait(lambda:identifier in app.workspace.frames)
        frame=app.workspace.frames[identifier];path=target/'artwork'/frame['image']
        original=path.read_bytes();left=preview(snapshot,app.workspace,False,(512,448)).tobytes()
        before=preview(snapshot,app.workspace,True,(512,448)).tobytes()
        with Image.open(path) as loaded:
            changed=loaded.convert('RGBA');changed.paste((255,0,255,255),(175,160,215,205));changed.save(path)
        after=preview(snapshot,app.workspace,True,(512,448)).tobytes()
        assert before!=after and preview(snapshot,app.workspace,False,(512,448)).tobytes()==left
        path.write_bytes(original)
        passed('Saving a PNG changes only the HD view; native motion and original pixels remain identical')
        destination=folder/'M-0012.zip';count=export_monster(app.workspace,app.entry,destination)
        with zipfile.ZipFile(destination) as archive:
            project=json.loads(archive.read('project.json'));members=json.loads(archive.read('AKTIONEN.json'))
            assert all(f['image'].startswith('M-0012_') for f in project['frames'])
            assert any(f['actor_type']==2 and f['id'] in members['Angriff'] for f in project['frames'])
            assert count==len([n for n in archive.namelist() if n.startswith('artwork/')])
        passed('Code-named PNG collection exports exact native mappings, originals and action ownership')
        app.run_action('Sterben');wait(lambda:app.active_action=='Sterben' and app.snapshot['live_stats']['hp']==0)
        wait(lambda:bool(app.workspace.data.get('monster_actions',{}).get('actor-12-v00',{}).get('Sterben')))
        groups=visible_frames(frame_groups(app.entry,app.workspace,app.live_ids.get('actor-12-v00',())))
        assert {f['pose'] for f in groups['Angriff'] if f['actor_type']==2}=={0x900c,0x9011,0x9016}
        passed('Native death is captured under the monster without removing shared bone PNGs from attack')
        app.picker.selection_set('M-0007');app.choose()
        wait(lambda:app.entry['type']==7 and any(a['type']==7 for a in app.snapshot['actors']))
        assert str(app.buttons['Angriff'].cget('state'))=='disabled'
        assert len(app.trees['Noch zuordnen'].get_children())>0
        assert 'noch nicht geprüft' in app.notes.get()
        passed('Other monsters spawn with their stats; unverified action mappings stay explicitly disabled')
        app.show_bosses.set(True);app.refresh_monsters()
        app.picker.selection_set('M-0081');app.choose()
        wait(lambda:bool(app.snapshot.get('boss_surface')),timeout=70)
        app.single_step();spin(.5)
        snapshot=copy.deepcopy(app.snapshot)
        without=dict(snapshot);without.pop('boss_surface')
        native=preview(snapshot,app.workspace,False,(512,448)).tobytes()
        assert native!=preview(without,app.workspace,False,(512,448)).tobytes()
        assert native==preview(snapshot,app.workspace,True,(512,448)).tobytes()
        assert snapshot['arena']['boss'] and 'HD-Textur' in app.notes.get()
        assert app.trees['Noch zuordnen'].get_children()
        tick=snapshot['tick'];spin(.3);assert app.snapshot['tick']==tick
        passed('Mode7 boss body and OBJ parts render together in both views; pause holds the same native field')
        app.picker.selection_set('M-008B');app.choose()
        wait(lambda:app.snapshot.get('live_stats',{}).get('actor_type')==9 and app.snapshot.get('target')==0xd80,timeout=70)
        assert app.snapshot['live_stats']['present']
        app.preview_mode.set('New Game+');app.change_mode()
        wait(lambda:app.snapshot.get('live_stats',{}).get('quest')==1 and app.snapshot.get('target')==0xd80,timeout=70)
        app.preview_mode.set('Normal');app.change_mode()
        wait(lambda:app.snapshot.get('live_stats',{}).get('quest')==0 and app.snapshot.get('target')==0xd80,timeout=70)
        passed('Boss alias uses its real main slot; Normal/NG+ switches restart the original boss scene')
        report['passed']=True
    finally:
        app.close();deadline=time.monotonic()+20
        while app.worker.is_alive() and time.monotonic()<deadline:root.update();time.sleep(.02)
        assert not app.worker.is_alive(),'Owned native worker did not stop'
        report['checks'].append('Owned native session closes cleanly')
        (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(folder,flush=True)
    return report


if __name__=='__main__':main()
