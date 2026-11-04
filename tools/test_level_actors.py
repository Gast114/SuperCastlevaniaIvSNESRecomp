"""Real editor callbacks, instance balance, candle import and native boss rendering."""
import argparse
import copy
import json
from pathlib import Path
import struct
import tempfile
import time
import tkinter as tk
from types import SimpleNamespace
import numpy as np
from PIL import Image
from enemy_workshop_native import ROOT,play
from enemy_sprite_export import Graphics,descriptor
from level_assets import Assets,ensure_room
from level_editor import Editor
from level_project import Project,paint
from level_parts import builtin_parts,repeat_part
from level_playtest import Playtest,compile_project
from level_bosses import profiles,STATE_BYTES,prepare_bosses

def visible_pixels(s,folder,kind):
    s.command('wram',folder/'ram.bin');s.command('dump',folder/'video.bin');s.command('screenshot',folder/'picture.png')
    ram=(folder/'ram.bin').read_bytes();video=(folder/'video.bin').read_bytes();image=Image.open(folder/'picture.png').convert('RGB');graphics=Graphics(video,3)
    matches=0
    # Bosses may emit independent limb tiles, palette changes and flipped
    # components rather than the root actor's current descriptor. Inspect
    # actual emitted OAM, excluding Simon's first eight slots and the HUD.
    for oam in range(8,128):
        x,y,attr=struct.unpack_from('<BBH',video,0x10200+oam*4);hi=video[0x10400+oam//4]>>(oam%4*2)&3;x=x+256*(hi&1);x=x-512 if x>=256 else x
        if not 0<=x<240 or not 32<=y<208:continue
        size=16 if hi&2 else 8
        for py in range(size):
            for px in range(size):
                value,color=graphics.pixel(attr,size,px,py)
                if value and len(set(color[:3]))>1 and image.getpixel((x+px,y+py))==color[:3]:matches+=1
    if kind==129:
        s.command('enemy_surface',folder/'mode7.png');surface=Image.open(folder/'mode7.png').convert('RGBA');matches=int(np.count_nonzero(np.array(surface)[:,:,3]))
    return matches

def check(native=True):
    parent=ROOT/'artwork-local/level-editor/tests';parent.mkdir(parents=True,exist_ok=True)
    folder=Path(tempfile.mkdtemp(prefix='actor-edit-',dir=parent));print(folder,flush=True)
    report=dict(passed=False,image_viewer_used=False,native=native,checks=[],bosses=[])
    def passed(text):report['checks'].append(text);print('PASS:',text,flush=True)
    def spin(root,predicate):
        end=time.monotonic()+40
        while time.monotonic()<end:
            root.update()
            if predicate():return
            time.sleep(.01)
        raise AssertionError('Editor background operation timed out')
    try:
        root=tk.Tk();root.withdraw();app=Editor(root,Project())
        try:
            spin(root,lambda:0 in app.assets and 2 in app.assets)
            assert app.show_object_names.get()
            assert not app.sprites.profiles[(12,0)].get('preview_only')
            profile=app.sprites.profiles[(12,0)];picture,_=app.sprites.sprite(dict(type=12,variant=0))
            frame=app.sprites.frames[profile['context']['current_id']]
            with Image.open(app.sprites.folder/'native-template'/frame['reference']) as ref:assert np.array_equal(np.array(picture),np.array(ref.convert('RGBA')))
            assert len([m for m in app.definitions if m['boss']])==14
            assert app.object_picker.exists('candle') and app.sprites.sprite(dict(type=14,variant=24))
            r=app.current();event=lambda x,y:SimpleNamespace(x=x*8*app.zoom.get()+1,y=y*8*app.zoom.get()+1)
            app.monsters.selection_set('M-000C');app.tool.set('Monster');app.press(event(20,16));app.release(event(20,16))
            actor=r['actors'][-1];identifier=actor['id'];app.props['name'].set('Mein Monster');app.apply_object()
            app.actor_details();root.update();app.stat_fields['hp'].set('123');app.stat_fields['contact_damage'].set('7');app.stat_fields['half_width'].set('10');app.apply_actor_stats(identifier)
            assert actor['stats']==dict(hp=123,contact_damage=7,half_width=10)
            assert 'Mein Monster' in app.actor_label(actor) and app.stats_table.item('hp','values')[-1]=='123'
            app.nudge_actor(1,-1);assert (actor['x'],actor['y'])==(161,127)
            app.tool.set('Auswahl');app.press(event(20,15));app.motion(event(22,16));app.release(event(22,16));assert (actor['x'],actor['y'])==(177,135)
            app.copy();app.paste();app.press(event(30,16));app.release(event(30,16));clone=r['actors'][-1]
            assert clone['id']!=identifier and clone['stats']==actor['stats'] and clone['name']==actor['name']
            app.project.save(folder/'actors.sc4level.json');assert Project.load(folder/'actors.sc4level.json').data==app.project.data
            app.delete();assert len(app.current()['actors'])==1;app.undo();assert len(app.current()['actors'])==2
            passed('Bat uses its measured body context; labels default on; 14 bosses and candles selectable; real stats/name/edit/drag/nudge/duplicate/save/undo callbacks')
        finally:app.project.dirty=False;app.close();root.update()
        assets={2:Assets(ensure_room(2))};floor=repeat_part(next(p for p in builtin_parts(assets) if p['id']=='platform-a03'),16)
        for n in range(5):
            r=Assets(ensure_room(n)).import_room(True);assert any(a['kind']=='candle' for a in r['actors'] if 'kind' in a)
            p=Project();p.data['rooms']=[r];p.data['start_room']=r['id'];compile_project(p.data,folder/f'original-{n}')
        passed('A01–A05 copies include real candle records and scene objects, and compile with the new actor format')
        if native:
            p=Project();r=p.data['rooms'][0];r['spawn']=[100,165];paint(r,'front',0,24,floor['tiles'],floor['collision'],floor['width'])
            r['actors']=[dict(id='skeleton',type=17,variant=0,x=120,y=165,flags=32768,stats=dict(hp=123,contact_damage=7)),dict(id='candle',type=14,kind='candle',variant=24,x=176,y=128,flags=32768)]
            g=Playtest(p.data,folder/'balance',fast=True)
            try:
                s=g.session;play.advance(s.lua,2);assert s.read(0x586)==123 and s.read(0x5d0)==14
                poses=set()
                s.write({0xbc:0,0x13f4:16,0x54a:s.read(0x58a),0x54e:s.read(0x58e)});play.advance(s.lua,1);assert s.read(0x13f4)==9
                for _ in range(16):play.advance(s.lua,1);poses.add(s.read(0x5c0))
                assert poses=={0x80d2,0x80d7}
            finally:g.close()
            passed('Native HP override persists; contact damage 7 removes exactly 7 HP; imported candle uses both original flame poses')
            for t in range(128,142):
                p=Project();r=p.data['rooms'][0];r['spawn']=[100,165];paint(r,'front',0,24,floor['tiles'],floor['collision'],floor['width'])
                r['actors']=[dict(id='boss',type=t,variant=0,x=200,y=96,flags=32768,boss_start='direct',boss_end='continue')]
                payload=prepare_bosses({t})[t];_,bx,by,slot,body=struct.unpack_from('<5H',payload)
                g=Playtest(p.data,folder/f'boss-{t:02x}',fast=True)
                try:
                    s=g.session;s.command('enemy','workshop on');s.command('enemy','capture off');motions=set();matches=0
                    for frame in range(90):
                        s.write({0xbc:32767,0x13f4:16});play.advance(s.lua,1)
                        motions.add(tuple(map(int,s.lua.eval(f'return mainmemory.read_u16_le({slot}),mainmemory.read_u16_le({slot}+10),mainmemory.read_u16_le({slot}+14),mainmemory.read_u16_le({slot}+18),mainmemory.read_u16_le({slot}+0x24),mainmemory.read_u16_le({slot}+0x32)')['values'])))
                        if frame in (14,44,89):matches=max(matches,visible_pixels(s,g.folder,t))
                    assert s.read(0xb8)>0 and s.read(slot+16)==body,(hex(t),'encounter ended unexpectedly')
                    assert matches>8,(hex(t),'no actual boss sprite pixels on screen',matches)
                    assert len(motions)>1,(hex(t),'boss state frozen')
                    row=dict(type=t,visible_pixels=matches,distinct_native_states=len(motions));report['bosses'].append(row);print('BOSS',row,flush=True)
                    if t==128:
                        # End-policy must return to this project rather than load the source stage.
                        s.write({0x70:7});play.advance(s.lua,2);assert s.read(0xb8)==0 and s.command('level_room')=='0'
                finally:g.close()
            passed('All 14 native boss groups move and draw actual pixels, including the Mode7 body; encounter completion returns to the custom map')
        report['passed']=True
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:(folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--no-native',action='store_true');args=parser.parse_args();check(not args.no_native)
