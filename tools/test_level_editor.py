"""Editor transactions, original-map fidelity and real native custom rooms.

No image is displayed. Raster comparisons read pixels programmatically.
"""
import argparse
import copy
import json
from pathlib import Path
import struct
import tempfile
import time
import tkinter as tk
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
from enemy_workshop_native import ROOT,play
from level_assets import Assets,ensure_room
from level_demo import make_demo
from level_project import Project,paint,room,validate
from level_playtest import Playtest,compile_project
from level_tiles import EMPTY


def check(native=True):
    parent=ROOT/'artwork-local/level-editor/tests';parent.mkdir(parents=True,exist_ok=True)
    folder=Path(tempfile.mkdtemp(prefix='check-',dir=parent))
    report=dict(passed=False,image_viewer_used=False,checks=[])
    def passed(text):report['checks'].append(text);print('PASS:',text,flush=True)
    def spin(root,predicate,seconds=30):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            root.update()
            if predicate():return
            time.sleep(.01)
        raise AssertionError('UI task timed out')
    try:
        p=Project();r=p.data['rooms'][0];identifier=r['id']
        p.begin('paint');paint(r,'front',5,7,[0x123,0x456],[1,0],2);p.commit()
        p.undo();assert p.get(identifier)['layers']['front'][7*r['width']+5]==EMPTY
        p.redo();assert p.get(identifier)['collision']['front'][7*r['width']+5]==1
        p.resize(p.get(identifier),160,40,name='Changed');p.undo();assert p.get(identifier)['name']!='Changed'
        p.redo();assert p.get(identifier)['width']==160 and p.get(identifier)['name']=='Changed'
        q=p.add_room(tileset=1);qid=q['id'];p.undo();p.redo();assert p.get(qid)['tileset']==1
        p.save(folder/'saved.sc4level.json');assert Project.load(p.path).data==p.data
        bad=copy.deepcopy(p.data);bad['rooms'][0]['doors']=[dict(id='broken',x=0,y=0,w=32,h=48,target='missing',target_x=0,target_y=0)]
        try:validate(bad)
        except ValueError:pass
        else:raise AssertionError('Dangling exit accepted')
        passed('Painting, collision, resize/name and room transactions undo/redo; JSON round-trip and invalid exit rejection')

        assets=Assets(ensure_room(0));original=assets.import_room()
        for n,layer in enumerate(('front','back')):
            spec=assets.meta['ppu']['layers'][n]
            for y in range(28):
                for x in range(32):assert original['layers'][layer][y*original['width']+x]==assets.vram[spec['map']+y*32+x]
        passed('Imported room 0 matches 1792 independently captured BG1/BG2 tile words, including metatile flips')

        from level_editor import Editor
        demo=Project.load(make_demo(folder/'demo.sc4level.json'));saved=copy.deepcopy(demo.data)
        root=tk.Tk();root.withdraw();app=Editor(root,demo)
        try:
            spin(root,lambda:0 in app.assets)
            # Exercise actual Tk callbacks for painting, rectangle selection,
            # copy/paste and coded monster placement without a screenshot.
            def event(x,y):return SimpleNamespace(x=x*8*app.zoom.get()+1,y=y*8*app.zoom.get()+1)
            block=next(n for n in range(256) if any(w!=0x800 for w in assets.block(n)))
            app.choose_block(SimpleNamespace(x=(block%8*32+1)*app.ui,y=(block//8*32+1)*app.ui));app.press(event(4,4));app.release(event(4,4));assert app.project.dirty
            app.undo();assert app.project.data==saved
            app.tool.set('Auswahl');app.press(event(4,4));app.motion(event(7,7));app.release(event(7,7));app.copy();app.paste()
            assert app.brush_width==4 and len(app.brush)==16
            app.monsters.selection_set('M-0012');app.tool.set('Monster');app.press(event(14,16));app.release(event(14,16))
            assert app.current()['actors'][-1]['type']==18
            assert not app.monsters.exists('M-0002')
            app.props['variant'].set('0');app.props['x'].set('120');app.props['plane'].set('back');app.apply_object()
            assert app.current()['actors'][-1]['x']==120 and not app.current()['actors'][-1]['flags']&0x8000
            app.name.set('GUI renamed');app.width.set(1152);app.apply_room();app.undo();assert app.current()['name']!='GUI renamed'
            app.project.save(folder/'gui.sc4level.json');assert Project.load(folder/'gui.sc4level.json').data==app.project.data
            passed('Real Tk callbacks: block paint, selection/copy/paste, coded enemy placement, plane editing, room rename undo and save')
        finally:app.project.dirty=False;app.close()

        if native:
            p=Project.load(make_demo(folder/'native.sc4level.json'));r,q=p.data['rooms'];r['actors'][0].update(x=200,flags=0)
            # The second room is deliberately tall and wide enough to test
            # both ring boundaries and a camera away from the origin.
            p.resize(q,96,64);w=q['width'];q['layers']={k:[0x800]*(w*64) for k in ('front','back')};q['collision']={k:[0]*(w*64) for k in ('front','back')}
            tile=r['layers']['front'][24*r['width']]
            for y in range(50,64):
                for x in range(w):q['layers']['front'][y*w+x]=tile;q['collision']['front'][y*w+x]=1
            r['doors']=[dict(id='TOUCH',x=360,y=120,w=48,h=64,target=q['id'],target_x=620,target_y=336,trigger='touch')]
            q['doors']=[dict(id='UP',x=600,y=330,w=48,h=64,target=r['id'],target_x=80,target_y=128,trigger='up',target_plane=1)]
            # Two genuinely separate gameplay planes, with different floors.
            r['collision_mode']=3
            for y in range(20,32):
                for x in range(r['width']):r['collision']['back'][y*r['width']+x]=1
            g=Playtest(p.data,folder/'native',fast=True)
            try:
                s=g.session;play.advance(s.lua,60);assert s.read(0x54e)==165
                start=s.read(0x54a);play.advance(s.lua,45,('Right',));assert s.read(0x54a)>start+30
                assert any(s.read(slot+0x10)==18 for slot in range(0x580,0xec0,0x40))
                passed('Native engine: hand-painted floor supports Simon, walking works, foreign-room M-0012 runs')
                # The rendered opaque floor agrees with the editor tile pixels.
                s.command('screenshot',folder/'raster.png');s.command('dump',folder/'video.bin')
                raster=Image.open(folder/'raster.png').convert('RGB');pixels=Assets(ensure_room(0))
                pixels.colors=struct.unpack_from('<256H',(folder/'video.bin').read_bytes(),0x10000)
                cam=s.read(0x1c);matches=0
                for yy in range(200,216):
                    for xx in range(16,160):
                        world=xx+cam;word=r['layers']['front'][(yy//8)*r['width']+world//8];c=pixels.tile(word).getpixel((world%8,yy%8))
                        if c[3]:assert raster.getpixel((xx,yy))==c[:3];matches+=1
                assert matches>1000
                passed(f'Native raster matches {matches} opaque floor pixels; image was not displayed')
                s.write({0x54a:370,0x54e:160});play.advance(s.lua,2)
                assert s.command('level_room')=='1' and s.read(0x54a)==620
                play.advance(s.lua,60);assert s.read(0x54e)==373 and s.read(0x1c)==492 and s.read(0x1e)==261
                s.command('dump',folder/'tall-video.bin');video=struct.unpack_from('<32768H',(folder/'tall-video.bin').read_bytes())
                xx,yy=75,50;assert video[0x4000+(xx%64//32)*1024+(yy%32)*32+xx%32]==tile
                passed('Touch exit enters tall room; floor y400, horizontal/vertical camera and wrapped native tile ring agree')
                malformed=folder/'truncated.bin';malformed.write_bytes((g.folder/'level.bin').read_bytes()[:-5]);s.command('dump',folder/'before.bin')
                try:s.command('level_project',malformed)
                except RuntimeError:pass
                else:raise AssertionError('Truncated native project accepted')
                s.command('dump',folder/'after.bin');assert (folder/'before.bin').read_bytes()==(folder/'after.bin').read_bytes() and s.command('level_room')=='1'
                passed('Invalid native project is rejected atomically without changing the active room or PPU')
                play.advance(s.lua,2,('Up',));assert s.command('level_room')=='0' and s.read(0x542)&0x8000==0
                play.advance(s.lua,40);assert s.read(0x54e)==133
                passed('Up exit returns on the second gameplay plane, with its own higher floor y160')
                s.command('level_project','off');assert s.command('level_room')=='4294967295'
            finally:g.close()
            # Closing while the asynchronous real game is starting must not
            # leak the new private process after the editor disappears.
            created=[]
            def create(*args,**kwargs):
                result=Playtest(*args,**kwargs,fast=True);created.append(result);return result
            root=tk.Tk();root.withdraw();app=Editor(root,Project.load(make_demo()))
            with patch('level_editor.Playtest',create):
                app.test();app.close()
                end=time.monotonic()+30
                while time.monotonic()<end:
                    try:root.update()
                    except tk.TclError:break
                    if created and created[0].session is None and not any(t.is_alive() for t in app.workers):break
                    time.sleep(.01)
                assert created and created[0].session is None
            passed('Closing during asynchronous playtest startup closes its private game process')
        report['passed']=True
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:
        (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(folder,flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--no-native',action='store_true');args=parser.parse_args();check(not args.no_native)
