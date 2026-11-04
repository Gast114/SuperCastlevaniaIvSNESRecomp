"""Mapped-window UI and genuine Tk mouse-event regressions, without image viewing."""
import copy
import json
from pathlib import Path
import tempfile
import time
import tkinter as tk
from unittest.mock import patch
from types import SimpleNamespace
from enemy_workshop_native import ROOT
from level_editor import Editor
from level_project import Project

def spin(root,predicate):
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        root.update()
        if predicate():return
        time.sleep(.01)
    raise AssertionError('UI background task timed out')

def check():
    parent=ROOT/'artwork-local/level-editor/tests';parent.mkdir(parents=True,exist_ok=True)
    folder=Path(tempfile.mkdtemp(prefix='ui-mouse-',dir=parent));print(folder,flush=True)
    report=dict(passed=False,image_viewer_used=False,checks=[])
    def passed(message):report['checks'].append(message);print('PASS:',message,flush=True)
    try:
        root=tk.Tk()
        with patch.object(root,'winfo_screenwidth',return_value=1920),patch.object(root,'winfo_screenheight',return_value=1080):app=Editor(root,Project())
        try:
            root.geometry('1280x900');spin(root,lambda:0 in app.assets and 2 in app.assets);root.update()
            assert len(app.tabs.tabs())==3 and app.tool.get()=='Auswahl'
            def within(widget,container):
                assert widget.winfo_ismapped(),str(widget)
                assert widget.winfo_rootx()>=container.winfo_rootx()-2,str(widget)
                assert widget.winfo_rooty()>=container.winfo_rooty()-2,str(widget)
                assert widget.winfo_rootx()+widget.winfo_width()<=container.winfo_rootx()+container.winfo_width()+2,str(widget)
                assert widget.winfo_rooty()+widget.winfo_height()<=container.winfo_rooty()+container.winfo_height()+2,str(widget)
            app.monsters.selection_set('M-0011');root.update()
            for button in app.library_actions['Monster']:within(button,app.monster_tab);assert str(button['state'])=='normal'
            before=len(app.current()['actors']);app.library_actions['Monster'][0].invoke();root.update()
            assert len(app.current()['actors'])==before+1 and app.tool.get()=='Auswahl'
            assert app.object()['type']==17 and app.object()['y']<220
            assert not app.prop_rows['target'][0].winfo_ismapped() and app.prop_rows['variant'][0].winfo_ismapped()
            within(app.details_button,app.left)
            passed('1280×900: three clear library tabs, visible add buttons, compact relevant properties and one-click insertion into the visible map')
            r=app.current();bat=dict(id='precise-bat',type=12,variant=0,x=163,y=131,flags=32768);r['actors'].append(bat);app.schedule();root.update()
            def point(actor):
                x1,y1,x2,y2=app.actor_bounds(actor);wx=int(x1);wy=int((y1+y2)/2);z=app.zoom.get()
                return round(wx*z-app.canvas.canvasx(0)),round(wy*z-app.canvas.canvasy(0))
            x,y=point(bat);assert 0<=x<app.canvas.winfo_width() and 0<=y<app.canvas.winfo_height()
            canvas=app.canvas;left=canvas.winfo_rootx();canvas.event_generate('<ButtonPress-1>',x=x,y=y);root.update();assert app.selected_object==('actor',bat['id'])
            canvas.event_generate('<B1-Motion>',x=x+6,y=y+10,state=0x100);root.update();canvas.event_generate('<ButtonRelease-1>',x=x+6,y=y+10);root.update()
            assert (bat['x'],bat['y'])==(166,136),(bat['x'],bat['y']);assert canvas.winfo_rootx()==left,'inspector shifted the canvas while dragging'
            app.undo();root.update();assert next(a for a in app.current()['actors'] if a['id']=='precise-bat')['x']==163
            passed('Actual mouse press/motion/release hits a small off-grid bat, drags by 3×5 pixels, keeps the grab offset and canvas position, and supports undo')
            app.monsters.selection_set('M-0012');root.update();app.library_actions['Monster'][1].invoke();root.update();assert app.tool.get()=='Monster'
            canvas.event_generate('<Motion>',x=300,y=170);root.update();assert app.canvas.find_withtag('brush-cursor')
            count=len(app.current()['actors']);canvas.event_generate('<ButtonPress-1>',x=300,y=170);canvas.event_generate('<ButtonRelease-1>',x=300,y=170);root.update()
            assert len(app.current()['actors'])==count+1 and app.tool.get()=='Auswahl'
            passed('Explicit mouse-placement action shows a sprite preview, inserts once and returns to selection automatically')
            app.monsters.selection_set('M-000C');app.monsters.see('M-000C');root.update();tree=app.monsters;box=tree.bbox('M-000C');assert box
            count=len(app.current()['actors']);tx,ty=box[0]+20,box[1]+box[3]//2
            tree.event_generate('<ButtonPress-1>',x=tx,y=ty);root.update()
            dx=canvas.winfo_rootx()+400-tree.winfo_rootx();dy=canvas.winfo_rooty()+260-tree.winfo_rooty()
            tree.event_generate('<B1-Motion>',x=dx,y=dy,state=0x100);root.update();assert canvas.find_withtag('library-drop')
            tree.event_generate('<ButtonRelease-1>',x=dx,y=dy);root.update();assert len(app.current()['actors'])==count+1 and app.object()['type']==12
            passed('Real Treeview-to-map drag-and-drop adds the chosen monster and selects it for immediate movement')
            app.parts_gallery.selection_set('platform-a03');app.choose_part();app.open_palette('Gegner');root.update()
            own_before=copy.deepcopy(app.project.data);old_id=app.room_id
            app.room_tabs.select(app.original_tab);app.originals.selection_set('1');root.update();app.choose_original();spin(root,lambda:app.original_number==1 and app.original_room is not None and not app.original_loading)
            original=copy.deepcopy(app.original_room);target=next(a for a in app.original_room['actors'] if a['type']==14 and a['x']<220)
            app.tool.set('Auswahl');app.schedule();root.update();x,y=point(target);canvas.event_generate('<ButtonPress-1>',x=x,y=y);root.update()
            canvas.event_generate('<B1-Motion>',x=x+6,y=y+6,state=0x100);root.update()
            canvas.event_generate('<B1-Motion>',x=x+14,y=y+18,state=0x100);root.update();canvas.event_generate('<ButtonRelease-1>',x=x+14,y=y+18);root.update()
            assert not app.original_view and app.selected_object==('actor',target['id'])
            item=app.object();assert (item['x'],item['y'])==(target['x']+7,target['y']+9),(item,target)
            assert app.original_cache[1]==original and app.project.get(old_id)==next(r for r in own_before['rooms'] if r['id']==old_id)
            assert len(app.project.data['rooms'])==len(own_before['rooms'])+1
            app.undo();root.update();assert next(a for a in app.current()['actors'] if a['id']==target['id'])['x']==target['x']
            passed('Dragging an original creates an editable copy automatically, survives queued tab/list events, preserves the existing unsaved project and original, and undoes as one move')
            calls=[]
            class FakePlaytest:
                audio_unavailable=False
                def __init__(self,data,*args,**kw):calls.append(copy.deepcopy(data));self.session=SimpleNamespace(lua=SimpleNamespace(command=lambda *args:None))
                def close(self):self.session=None
            with patch('level_editor.Playtest',FakePlaytest):
                app.test();spin(root,lambda:app.playtest is not None);app.stop_test()
            assert calls[0]['start_room']==app.room_id and app.project.data['start_room']==old_id
            app.filter.set('no-such-monster');root.update();assert all(str(b['state'])=='disabled' for b in app.library_actions['Monster']);app.filter.set('');root.update()
            passed('F5 tests the current room without changing the saved start room; filtering cannot leave stale enabled add actions')
            # A 4K display uses larger controls, while the same logical layout remains within its panels.
            root.geometry('1680x980');root.update();app.open_palette('Objekte');app.object_picker.selection_set('candle');root.update()
            for button in app.library_actions['Objekt']:within(button,app.objects_tab)
            assert app.mode_title.get() and not app.edit_button.winfo_ismapped()
            passed('Larger layout retains object actions and an explicit editable-state banner')
        finally:app.project.dirty=False;app.close();root.update()
        root=tk.Tk()
        with patch.object(root,'winfo_screenwidth',return_value=3840),patch.object(root,'winfo_screenheight',return_value=2160):app=Editor(root,Project())
        try:
            root.maxsize(5000,3200);root.geometry('2856x1700');spin(root,lambda:0 in app.assets);app.monsters.selection_set('M-0080');root.update()
            assert app.ui==1.7 and root.winfo_width()>=2800,(app.ui,root.winfo_width(),root.winfo_height())
            for button in app.library_actions['Monster']:within(button,app.monster_tab)
            app.library_actions['Monster'][0].invoke();root.update();within(app.details_button,app.left)
            assert app.canvas.winfo_width()>1000 and app.canvas.winfo_height()>800
            passed('4K scaling: large readable controls, add/inspector actions fully visible and a spacious map at 1.7× UI density')
        finally:app.project.dirty=False;app.close();root.update()
        report['passed']=True
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:(folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__':check()
