"""Sprite placement, original catalog startup and real native moving platforms."""
import copy
import argparse
import json
from pathlib import Path
import tempfile
import time
import tkinter as tk
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from PIL import Image
from enemy_workshop_native import ROOT,play
from level_assets import Assets,ensure_source
from level_editor import Editor
from level_objects import SpriteLibrary,validate_platform
from level_parts import builtin_parts,repeat_part
from level_project import Project,paint
from level_playtest import Playtest,OriginalPlaytest


def check(native=True):
    parent=ROOT/'artwork-local/level-editor/tests';parent.mkdir(parents=True,exist_ok=True)
    folder=Path(tempfile.mkdtemp(prefix='objects-catalog-',dir=parent));print(folder,flush=True)
    report=dict(passed=False,image_viewer_used=False,native_checked=native,checks=[])
    def passed(label):report['checks'].append(label);print('PASS:',label,flush=True)
    def spin(root,predicate):
        end=time.monotonic()+35
        while time.monotonic()<end:
            root.update()
            if predicate():return
            time.sleep(.01)
        raise AssertionError('Editor task did not finish')
    try:
        root=tk.Tk();root.withdraw();app=Editor(root,Project())
        try:
            spin(root,lambda:0 in app.assets and 2 in app.assets)
            assert app.monsters.item('M-0011','image') and app.object_picker.item('moving-horizontal','image')
            r=app.current();actor=dict(id='body',type=0x11,variant=0,x=80,y=96,flags=0x8000);r['actors']=[actor]
            image=app.room_image(r,0,0,32,28);sprite,anchor=app.sprites.sprite(actor)
            expected=Image.new('RGBA',(256,224),'#202632');expected.alpha_composite(sprite,(80-anchor[0],96-anchor[1]))
            assert np.array_equal(np.array(image),np.array(expected))
            assert np.count_nonzero(np.any(np.array(image)[:,:,:3]!=[32,38,50],axis=2))>100
            assert app.show_object_names.get()
            passed('Monster/object picker has sprite images; actual map pixels match the native body PNG at its world anchor')
            r['actors']=[]
            app.part_category.set('Bewegliche Plattformen');app.refresh_parts();app.parts_gallery.selection_set('moving-vertical');app.choose_part()
            assert app.tool.get()=='Objekt' and app.object_template['variant']==1
            event=lambda x,y:SimpleNamespace(x=x*8*app.zoom.get()+1,y=y*8*app.zoom.get()+1)
            app.hover_brush(event(25,20));assert len(app.canvas.find_withtag('brush-cursor'))>=2
            app.press(event(25,20));app.release(event(25,20));actor=r['actors'][-1]
            assert (actor['type'],actor['variant'],actor['kind'])==(0x17,1,'platform') and app.props['motion'].get()=='Senkrecht'
            app.props['motion'].set('Waagerecht');app.apply_object();assert r['actors'][-1]['variant']==0
            app.undo();assert app.current()['actors'][-1]['variant']==1;app.redo();assert app.current()['actors'][-1]['variant']==0
            app.project.save(folder/'platform.sc4level.json');assert Project.load(folder/'platform.sc4level.json').data==app.project.data
            try:validate_platform(dict(kind='platform',type=23,variant=0,x=16,y=100),1024,256)
            except ValueError:pass
            else:raise AssertionError('Platform travel outside room accepted')
            passed('Moving-platform gallery, path cursor, motion selector, source-independent project save and undo/redo')
        finally:app.project.dirty=False;app.close()

        root=tk.Tk();root.withdraw();app=Editor(root)
        try:
            assert len(app.originals.get_children())==68
            spin(root,lambda:app.original_view and app.original_room is not None and not app.original_loading)
            assert app.original_number==0
            own=copy.deepcopy(app.project.data);original_snapshot=copy.deepcopy(app.current());app.tool.set('Zeichnen')
            event=lambda x,y:SimpleNamespace(x=x*8*app.zoom.get()+1,y=y*8*app.zoom.get()+1)
            app.press(event(4,4));app.release(event(4,4));assert not app.original_view and app.original_cache[0]==original_snapshot
            app.room_tabs.select(app.original_tab);root.update()
            app.originals.selection_set('1');app.choose_original();spin(root,lambda:app.original_number==1 and app.original_room is not None and not app.original_loading)
            original=copy.deepcopy(app.current());assert any(a['type']==0x11 for a in original['actors'])
            assert app.edit_original();root.update();assert not app.original_view and app.project.dirty
            assert app.current()['id']!=original['id'] and app.original_cache[1]==original
            app.project.dirty=False
            app.room_tabs.select(app.original_tab);app.originals.selection_set('8');root.update();app.choose_original()
            spin(root,lambda:app.original_number==8 and not app.original_loading)
            assert app.original_view and app.original_room is None and app.original_error
            calls=[]
            class Fake:
                audio_unavailable=False
                def __init__(self,n,*args,**kwargs):calls.append(n);self.session=SimpleNamespace(lua=SimpleNamespace(command=lambda *a:None))
                def close(self):self.session=None
            with patch('level_editor.OriginalPlaytest',Fake):
                app.test();spin(root,lambda:app.playtest is not None);app.stop_test()
            assert calls==[8]
            passed('Default startup lists 68 originals; preview is read-only, explicit copy is editable, vertical entries retain native F5 play')
        finally:app.project.dirty=False;app.close()

        assets={2:Assets(ensure_source(2))};floor=repeat_part(next(p for p in builtin_parts(assets) if p['id']=='platform-a03'),16)
        for variant in ((0,1) if native else ()):
            p=Project();r=p.data['rooms'][0];r['spawn']=[200,96]
            paint(r,'front',0,26,floor['tiles'],floor['collision'],floor['width'])
            r['actors']=[dict(id='native-platform',kind='platform',type=0x17,variant=variant,x=200,y=160,flags=0x8000)]
            game=Playtest(p.data,folder/f'axis-{variant}',fast=True)
            try:
                samples=[]
                for frame in range(360):
                    play.advance(game.session.lua,1)
                    values=game.session.lua.eval('return mainmemory.read_u16_le(0x590),mainmemory.read_u16_le(0x58a),mainmemory.read_u16_le(0x58e),mainmemory.read_u16_le(0x54a),mainmemory.read_u16_le(0x54e)')['values']
                    samples.append(list(map(int,values)))
                assert all(v[0]==23 for v in samples)
                moving=[v[1 if variant==0 else 2] for v in samples]
                assert max(moving)-min(moving)>=79,(variant,'did not move/return')
                assert any(b>a for a,b in zip(moving,moving[1:])) and any(b<a for a,b in zip(moving,moving[1:])),variant
                for _,px,py,hx,hy in samples[40:120]:
                    assert abs(hy-(py-35))<=1,(variant,'player fell through',px,py,hx,hy)
                    if variant==0:assert abs(hx-px-8)<=1,(variant,'player not carried horizontally')
                    else:assert hx==200,(variant,'vertical platform moved player sideways')
                play.advance(game.session.lua,2,('B',));play.advance(game.session.lua,10)
                assert game.session.read(0x58e)-game.session.read(0x54e)>40,'cannot jump off platform'
            finally:game.close()
        if native:passed('Both native platform axes move, reverse, support/carry Simon and allow jumping off; no source level loaded for these objects')
        for number in ((1,21) if native else ()):
            game=OriginalPlaytest(number,folder/f'original-{number}',fast=True)
            try:
                assert game.session.read(0x86)==number and game.session.read(0x70)==5
                assert game.session.command('level_room')=='4294967295'
                if number==21:assert json.loads(game.session.command('ppu'))['bgmode']&7==7
            finally:game.close()
        if native:passed('Native original-section play works for A02 and a Mode7 room, without activating custom-level overrides')
        report['passed']=True
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:(folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--no-native',action='store_true');args=parser.parse_args();check(not args.no_native)
