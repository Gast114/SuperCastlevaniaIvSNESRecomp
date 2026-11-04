"""Single-window workshop integration, shared selection and owned native lifecycle."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import queue
import shutil
import tempfile
import time
import tkinter as tk
from unittest.mock import patch
from enemy_workshop import DEFAULT_WORKSPACE
from enemy_workshop_assets import Workspace
from enemy_workshop_native import ROOT
from level_editor import Editor
from level_project import Project
from monster_model import frame_groups

class FakeWorker:
    def __init__(self,commands,events,*args,initial_entry=None,**kw):self.commands=commands;self.events=events;self.initial_entry=initial_entry;self.stopping=False;self.started=False
    def start(self):self.started=True
    def is_alive(self):return self.started and not self.stopping

def wait(root,predicate,seconds=40):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        root.update()
        if predicate():return
        time.sleep(.01)
    raise AssertionError('Studio operation timed out')

def clone_workspace(destination):
    source=Workspace(DEFAULT_WORKSPACE);data=copy.deepcopy(source.data);data['monster_names']={};data['monster_actions']={}
    data['frames']=[f for f in data['frames'] if f['actor_type'] in (2,17,18,45)]
    destination.mkdir();(destination/'artwork').mkdir();(destination/'references').mkdir()
    for f in {f['image']:f for f in data['frames']}.values():
        shutil.copy2(source.folder/'artwork'/f['image'],destination/'artwork'/f['image']);shutil.copy2(source.folder/'references'/f['reference'],destination/'references'/f['reference'])
    (destination/'project.json').write_text(json.dumps(data),encoding='utf-8');return Workspace(destination)

def check(native=False,ui4k=False):
    folder=Path(tempfile.mkdtemp(prefix='studio-',dir=ROOT/'artwork-local/level-editor/tests'));print(folder,flush=True)
    report=dict(passed=False,native=native,image_viewer_used=False,checks=[])
    def passed(text):report['checks'].append(text);print('PASS:',text,flush=True)
    root=tk.Tk()
    with patch.object(root,'winfo_screenwidth',return_value=3840 if ui4k else 1920),patch.object(root,'winfo_screenheight',return_value=2160 if ui4k else 1080):app=Editor(root,Project())
    root.maxsize(5000,3200);root.geometry('2856x1700' if ui4k else '1280x900')
    artist=ROOT.parent/'Assets (ausgeschnitten)/Gegner/Werkstatt/project.json';before=hashlib.sha256(artist.read_bytes()).hexdigest()
    worker_patch=None
    try:
        wait(root,lambda:0 in app.assets and 2 in app.assets)
        assert app.studio.workshop is None and not app.studio.loading
        workspace=clone_workspace(folder/'workspace');app.studio.workspace_path=workspace.folder;app.studio.library=None
        if not native:worker_patch=patch('monster_workshop.Worker',FakeWorker);worker_patch.start()
        room=app.current();actor=dict(id='linked-skeleton',type=18,variant=0,x=120,y=165,flags=32768,stats={'hp':72});room['actors']=[actor];app.selected_object=('actor',actor['id']);app.object_fields()
        project=app.project;size=root.geometry();app.animation_button.invoke();wait(root,lambda:app.studio.workshop is not None)
        workshop=app.studio.workshop;root.update()
        assert workshop.embedded and workshop.root is app.monster_page and workshop.entry['type']==18
        assert app.studio.visible and len(app.workspaces.tabs())==2 and app.project is project and root.geometry()==size
        assert len([m for m in workshop.monsters if m['boss']])==14 and workshop.picker.item('M-0012','image')
        assert str(workshop.values_button['state'])=='normal' and 'Verknüpft' in workshop.level_context.get()
        passed('One window embeds all workshop features lazily, opens the exact placed actor, keeps the level project and offers 14 boss codes with pictures')
        def within(widget):
            if not widget.winfo_ismapped():return
            parent=widget.master
            assert widget.winfo_rootx()>=parent.winfo_rootx()-2,str(widget)
            assert widget.winfo_rooty()>=parent.winfo_rooty()-2,str(widget)
            assert widget.winfo_rootx()+widget.winfo_width()<=parent.winfo_rootx()+parent.winfo_width()+2,(str(widget),widget.winfo_width(),parent.winfo_width())
            assert widget.winfo_rooty()+widget.winfo_height()<=parent.winfo_rooty()+parent.winfo_height()+2,(str(widget),widget.winfo_height(),parent.winfo_height())
        def walk(widget):
            for child in widget.winfo_children():
                if child.winfo_class() in ('TButton','TCheckbutton','Treeview','TCombobox','Canvas'):within(child)
                walk(child)
        walk(app.monster_page)
        assert min(c.winfo_width() for c in workshop.canvases)>100
        before_undo=copy.deepcopy(app.project.data);app.undo();app.redo();assert app.project.data==before_undo
        passed('Embedded controls fit their panels at '+('4K UI scaling' if ui4k else '1280×900')+'; workshop undo shortcuts cannot change the hidden level')
        workshop.refresh_poses();assert len(workshop.trees['Gehen / Bewegen'].get_children())==2
        workshop.values_button.invoke();root.update();app.stat_fields['hp'].set('101');app.apply_actor_stats(actor['id']);assert actor['stats']['hp']==101;app.stats_window.destroy()
        workshop.name.set('Studio-Skelett');workshop.save_name();root.update()
        assert app.library_names['M-0012']=='Studio-Skelett' and 'Studio-Skelett' in app.actor_label(actor)
        assert Workspace(workspace.folder).data['monster_names']['M-0012']=='Studio-Skelett'
        passed('Level instance values stay editable from the workshop; saved workshop names immediately update the map and library')
        if native:
            wait(root,lambda:bool(workshop.snapshot.get('actors')),60)
            assert workshop.snapshot.get('neutral_scene') and workshop.snapshot['live_stats']['runtime_room']==0
            workshop.run_action('Angriff');wait(root,lambda:any(a['type']==2 for a in workshop.snapshot.get('actors',[])),40)
            workshop.preview_mode.set('New Game+');workshop.change_mode();wait(root,lambda:workshop.snapshot.get('live_stats',{}).get('quest')==1,40)
            passed('Embedded native arena runs the real bone attack and NG+ preview in a neutral room')
            for boss in (0x82,0x8d):
                workshop.select_entry({'type':boss,'variant':0})
                wait(root,lambda:workshop.snapshot.get('actors') and workshop.snapshot.get('live_stats',{}).get('quest')==1,70)
                assert workshop.snapshot['neutral_scene'] and workshop.snapshot['live_stats']['runtime_room']==0
                assert not workshop.snapshot.get('context_error'),workshop.snapshot.get('context_error')
            passed('Both additional scene-controlled bosses start in the embedded neutral arena and retain the NG+ selection')
        workshop.select_entry({'type':17,'variant':34});root.update()
        assert app.library_entry('Monster')['variant']==34 and str(workshop.values_button['state'])=='disabled'
        with patch('level_editor.filedialog.asksaveasfilename') as dialog:app.save();dialog.assert_not_called()
        count=len(app.current()['actors']);workshop.place_button.invoke();root.update()
        assert not app.studio.visible and not workshop.active and app.object()['type']==17 and app.object()['variant']==34 and len(app.current()['actors'])==count+1
        assert app.project is project and actor['stats']['hp']==101
        passed('Shared variant selection inserts the chosen monster into the same level; context Save does not open a level-file dialog; returning pauses the arena')
        if native:
            deadline=time.monotonic()+.7
            while time.monotonic()<deadline:root.update();time.sleep(.01)
            field=workshop.snapshot.get('tick');deadline=time.monotonic()+.3
            while time.monotonic()<deadline:root.update();time.sleep(.01)
            assert workshop.snapshot.get('tick')==field,'hidden native arena is still running'
            passed('Hidden native arena actually stops advancing while the level workspace is active')
        # No unrelated projectiles may be borrowed for a boss without its own library profile.
        groups=frame_groups(dict(type=0x8d,boss=True,main_type=0x8d,child_types=list(range(1,14))),workspace)
        assert not any(groups.values())
        passed('An unprepared extra boss does not collect unrelated sprites from other monsters')
        assert hashlib.sha256(artist.read_bytes()).hexdigest()==before
        report['passed']=True
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:
        app.project.dirty=False;app.close();deadline=time.monotonic()+35
        while not app.studio.stopped() and time.monotonic()<deadline:root.update();time.sleep(.02)
        assert app.studio.stopped(),'embedded worker was orphaned';root.update()
        if worker_patch:worker_patch.stop()
        report['checks'].append('Main-window close saves and stops the owned workshop; artist source workspace unchanged')
        (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--native',action='store_true');parser.add_argument('--ui4k',action='store_true');args=parser.parse_args();check(args.native,args.ui4k)
