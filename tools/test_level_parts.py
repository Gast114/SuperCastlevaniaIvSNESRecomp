"""Terrain picker workflows, retained source/collision, and native platform support.

Uses actual Tk callbacks and native physics; does not open an image viewer.
"""
import copy
import argparse
import json
from pathlib import Path
import tempfile
import time
import tkinter as tk
from types import SimpleNamespace

from enemy_workshop_native import ROOT,play
from level_assets import Assets,ensure_source
from level_editor import Editor
from level_parts import builtin_parts,repeat_part,validate_part,pick_connected_part
from level_project import Project,paint
from level_playtest import Playtest
from level_tiles import EMPTY,resolve,SOURCE_COUNT


def check(native=True):
    parent=ROOT/'artwork-local/level-editor/tests';parent.mkdir(parents=True,exist_ok=True)
    folder=Path(tempfile.mkdtemp(prefix='parts-',dir=parent));print(folder,flush=True)
    report=dict(passed=False,image_viewer_used=False,native_physics_checked=native,checks=[])
    def passed(label):report['checks'].append(label);print('PASS:',label,flush=True)
    def spin(root,predicate):
        end=time.monotonic()+30
        while time.monotonic()<end:
            root.update()
            if predicate():return
            time.sleep(.01)
        raise AssertionError('Terrain picker did not load')
    try:
        assets={n:Assets(ensure_source(n)) for n in (1,2)}
        parts={p['id']:p for p in builtin_parts(assets)}
        repeated=repeat_part(parts['platform-a03'],3)
        assert repeated['width']==6
        assert [resolve(v,0,'back')[2] for v in repeated['tiles']]==[0x2801,0x2802]*3+[0x2803,0x2804]*3
        assert all(v==1 for v in repeated['collision'])
        bad=copy.deepcopy(repeated);bad['mask'][0]=1
        try:validate_part(bad)
        except ValueError:pass
        else:raise AssertionError('Nonboolean terrain mask accepted')
        passed('Repeatable platforms preserve whole rows, explicit source and native collision; invalid masks rejected')
        r=Project().data['rooms'][0]
        for x,y in [(1,1),(3,1),(1,2),(2,2),(3,2)]:paint(r,'front',x,y,[0x2801],[1])
        paint(r,'front',2,1,[0x1234],[7]);part,rect=pick_connected_part(r,'front',1,1)
        assert rect==(1,1,3,2) and part['mask']==[True,False,True,True,True,True]
        paint(r,'front',11,10,[0x3456],[9]);paint(r,'front',10,10,part['tiles'],part['collision'],part['width'],mask=part['mask'])
        assert r['layers']['front'][10*r['width']+11]==0x3456 and r['collision']['front'][10*r['width']+11]==9
        passed('Connected platform picking skips holes and other collision classes without erasing destination terrain')

        root=tk.Tk();root.withdraw();app=Editor(root,Project())
        try:
            spin(root,lambda:1 in app.assets and 2 in app.assets)
            assert len(app.source_picker['values'])==SOURCE_COUNT
            assert not app.object_props.winfo_manager()
            app.part_category.set('Plattformen');app.refresh_parts()
            assert app.parts_gallery.exists('platform-a02') and not app.parts_gallery.exists('stairs-right')
            app.parts_gallery.selection_set('platform-a02');app.part_length.set(3);app.choose_part()
            assert app.tool.get()=='Bauteil' and app.brush_width==6 and '48 × 16' in app.brush_label.get()
            event=lambda x,y:SimpleNamespace(x=x*8*app.zoom.get()+1,y=y*8*app.zoom.get()+1)
            app.hover_brush(event(5,10));assert len(app.canvas.find_withtag('brush-cursor'))==1
            before=copy.deepcopy(app.project.data);app.press(event(5,10));app.release(event(5,10))
            first=app.room_id;r=app.current();width=r['width']
            assert r['layers']['front'][10*width+4]==EMPTY
            for y in range(2):
                for x in range(6):
                    at=(10+y)*width+5+x
                    assert r['layers']['front'][at]==app.brush[y*6+x]
                    assert r['collision']['front'][at]==app.brush_collision[y*6+x]
            after=copy.deepcopy(app.project.data);app.undo();assert app.project.data==before;app.redo();assert app.project.data==after
            passed('Visual category picker, adjustable length, footprint cursor, exact 8px placement, collision and undo/redo')

            app.part_category.set('Treppen');app.refresh_parts();app.parts_gallery.selection_set('stairs-right');app.choose_part()
            r=app.current()
            for y in range(8,12):
                for x in range(13,17):paint(r,'front',x,y,[0x1234],[7])
            old=copy.deepcopy(r);mask=app.brush_mask[:]
            app.press(event(13,8));app.release(event(13,8))
            for i,on in enumerate(mask):
                at=(8+i//4)*width+13+i%4
                if not on:assert r['layers']['front'][at]==old['layers']['front'][at] and r['collision']['front'][at]==7
            original=(app.brush[:],app.brush_collision[:],app.brush_mask[:]);app.flip(True);app.flip(True)
            assert (app.brush,app.brush_collision,app.brush_mask)==original
            passed('Stair stamps and mirrored masks preserve wall graphics/collision outside the actual steps')

            app.pick_part(event(6,10));assert app.selection==(5,10,10,11) and app.brush_width==6
            app.part_name.set('Meine Plattform');app.remember_brush();identifier=app.project.data['parts'][0]['id']
            assert all(resolve(v,0,'back')[:2]==(1,'front') for v in app.brush)
            app.add_room();app.layer.set('back');app.part_category.set('Eigene');app.refresh_parts();app.parts_gallery.selection_set(identifier);app.choose_part()
            app.press(event(3,7));app.release(event(3,7));r=app.current()
            assert all(v==EMPTY for v in r['layers']['front'])
            assert resolve(r['layers']['back'][7*r['width']+3],0,'back')[:2]==(1,'front')
            app.project.save(folder/'parts.sc4level.json');loaded=Project.load(folder/'parts.sc4level.json')
            assert loaded.data==app.project.data
            app.remove_part();assert not app.project.data['parts'];app.undo();assert app.project.data['parts'][0]['id']==identifier
            passed('Shift-right-click picks a whole platform; custom parts persist with the project and work across rooms/planes without changing their source')
        finally:app.project.dirty=False;app.close()

        for key,standing_y in ([('platform-a03',69),('platform-a02',69)] if native else []):
            p=Project();r=p.data['rooms'][0];r['spawn']=[80,40]
            part=repeat_part(parts[key],4)
            paint(r,'front',8,12,part['tiles'],part['collision'],part['width'],mask=part['mask'])
            game=Playtest(p.data,folder/key,fast=True)
            try:
                play.advance(game.session.lua,80);assert game.session.read(0x54e)==standing_y
                start=game.session.read(0x54a);play.advance(game.session.lua,20,('Right',))
                assert game.session.read(0x54a)>start and game.session.read(0x54e)==standing_y,(key,'platform walk height changed')
            finally:game.close()
        if native:passed('Native playtests: A03 stone platform and A02/F10 platform both support Simon and walking on a flat surface')
        report['passed']=True
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:(folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--no-native',action='store_true');args=parser.parse_args();check(not args.no_native)
