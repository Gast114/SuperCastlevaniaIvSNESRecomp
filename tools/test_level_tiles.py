"""Cross-section graphics, independent palettes and native host composition.

Uses original assets and pixel comparisons; no image viewer is opened.
"""
import copy
import json
from pathlib import Path
import struct
import tempfile
import time
import tkinter as tk
from types import SimpleNamespace
from PIL import Image
from enemy_workshop_native import ROOT,play
from level_assets import Assets,ensure_source
from level_editor import Editor
from level_graphics import compile_graphics
from level_playtest import Playtest,compile_project
from level_project import Project,room,paint,validate
from level_tiles import EMPTY,SOURCE_COUNT,bind,resolve,sources,valid


def check():
    folder=Path(tempfile.mkdtemp(prefix='mixed-check-',dir=ROOT/'artwork-local/level-editor/tests'))
    report=dict(passed=False,image_viewer_used=False,checks=[])
    def passed(text):report['checks'].append(text);print('PASS:',text,flush=True)
    def spin(root,predicate):
        end=time.monotonic()+35
        while time.monotonic()<end:
            root.update()
            if predicate():return
            time.sleep(.01)
        raise AssertionError('UI source load timed out')
    try:
        assets={n:Assets(ensure_source(n)) for n in (0,1,68)}
        values=[bind(0x8401,n,layer) for n in range(SOURCE_COUNT) for layer in ('front','back')]
        assert all(valid(v) for v in values) and valid(EMPTY)
        assert all(resolve(bind(7,n,'back'),0,'front')==(n,'back',7) for n in range(SOURCE_COUNT))
        assert not valid(0x7f0000) and not valid(0x800001) and not valid(0x2000000)
        p=Project();r=p.data['rooms'][0];paint(r,'front',3,4,values,[0]*len(values),16);p.save(folder/'mixed.sc4level.json')
        assert Project.load(p.path).data==p.data
        legacy=copy.deepcopy(p.data);legacy['version']=1;legacy['rooms'][0]['layers']={k:[0x800]*(r['width']*r['height']) for k in ('front','back')}
        assert Project(legacy).data['version']==2
        passed('All 69 source IDs and both source layers survive JSON; invalid references rejected; version1 projects remain readable')

        # Compare Mode7 decoding against independent byte addressing of the
        # prepared native picture, not against another use of Assets.tile.
        mode7=assets[68];assert mode7.meta['ppu']['bgmode']&7==7 and mode7.block_count==1024
        for t in (0,1,33,127,255):
            image=mode7.tile(t)
            for y in range(8):
                for x in range(8):
                    index=mode7.video[(t*64+y*8+x)*2+1];color=mode7.colors[index]
                    expand=lambda c:(c<<3)|(c>>2)
                    assert image.getpixel((x,y))==(expand(color&31),expand(color>>5&31),expand(color>>10&31),255 if index else 0)
        assert mode7.block(1023)==[mode7.vram[(124+y)*128+124+x]&255 for y in range(4) for x in range(4)]
        passed('Mode7 source exposes all 256 texture tiles and all 1024 map blocks; raw native byte/palette decoding agrees')

        p=Project();root=tk.Tk();root.withdraw();app=Editor(root,p)
        try:
            spin(root,lambda:0 in app.assets)
            assert len(app.source_picker['values'])==SOURCE_COUNT
            app.load_assets(range(SOURCE_COUNT));spin(root,lambda:len(app.assets)==SOURCE_COUNT and not app.loading_assets)
            assert 'bereit' in app.status.get()
            app.source_picker.set('68 · R-23 / Mode7');app.source_changed(SimpleNamespace(widget=app.source_picker))
            assert str(app.palette_box['state'])=='disabled'
            app.choose_block(SimpleNamespace(x=(1023%8*32+1)*app.ui,y=(1023//8*32+1)*app.ui));assert all(resolve(v,0,'front')[0]==68 for v in app.brush)
            app.source_picker.set('1 · R-01');app.source_layer.set('back');app.source_changed(SimpleNamespace(widget=app.source_picker));spin(root,lambda:1 in app.assets)
            block=next(n for n in range(256) if any(assets[1].tile(w,'back').getbbox() for w in assets[1].block(n,'back')))
            app.choose_block(SimpleNamespace(x=(block%8*32+1)*app.ui,y=(block//8*32+1)*app.ui))
            assert all(resolve(v,0,'front')[:2]==(1,'back') for v in app.brush)
            r=app.current();p.begin('foreign block');paint(r,'front',4,4,app.brush,app.brush_collision,4);p.commit()
            expected=assets[1].tile(assets[1].block(block,'back')[0],'back').tobytes()
            assert app.tile_image(r['layers']['front'][4*r['width']+4],r['tileset'],'front').tobytes()==expected
            app.selection=(4,4,7,7);app.copy();app.add_room();app.layer.set('back');app.paste()
            paint(app.current(),'back',8,8,app.brush,app.brush_collision,4)
            assert resolve(app.current()['layers']['back'][8*app.current()['width']+8],app.current()['tileset'],'back')[:2]==(1,'back')
            before=app.brush[:];collisions=app.brush_collision[:];app.flip(True);app.flip(True);assert app.brush==before and app.brush_collision==collisions
            # Legacy area copy also binds its original room/layer before moving.
            app.current()['layers']['front'][0]=0x1234;app.current()['tileset']=1;app.layer.set('front');app.selection=(0,0,0,0);app.copy();assert resolve(app.clipboard[0][0],0,'back')==(1,'front',0x1234)
            app.project.save(folder/'gui.sc4level.json');assert Project.load(folder/'gui.sc4level.json').data==app.project.data
            passed('Tk source picker, BG2-to-BG1 placement, cross-room/layer copy, reversible flips and save preserve source colors and collision')
        finally:app.project.dirty=False;app.close()

        p=Project();r=p.data['rooms'][0];r.update(width=64,height=32,spawn=[64,128])
        r['layers']={k:[EMPTY]*2048 for k in ('front','back')};r['collision']={k:[0]*2048 for k in ('front','back')}
        # More palette combinations than a native BG's eight palette banks.
        swatches=[]
        for n in (0,1):
            for bank in range(8):
                word=next(w|(bank<<10) for w in range(1024) if assets[n].tile(w|(bank<<10)).getbbox())
                swatches.append(bind(word,n,'front'))
        m7word=next(w for w in range(256) if assets[68].tile(w).getbbox());swatches.append(bind(m7word,68,'front'))
        for y in range(24,32):
            for x in range(64):r['layers']['front'][y*64+x]=swatches[x%len(swatches)];r['collision']['front'][y*64+x]=1
        # An opaque source layer behind front-layer holes checks transparency.
        back_word=next(w for w in range(1024) if assets[1].tile(w,'back').getbbox())
        for y in range(24,32):
            for x in range(64):r['layers']['back'][y*64+x]=bind(back_word,1,'back')
        # A native actor remains in front of low-priority artwork. A duplicate
        # frame with raised front priority must cover it on the back plane.
        r['actors']=[dict(id='foreign',type=18,variant=0,x=208,y=144,flags=0)]
        for y in range(12,24):
            for x in range(20,32):r['layers']['front'][y*64+x]=bind(back_word&~0x2000,1,'back')
        r['collision']['back']=r['collision']['front'][:]
        q=room('Other graphics');p.data['rooms'].append(q)
        r['doors']=[dict(id='next',x=420,y=120,w=32,h=64,target=q['id'],target_x=64,target_y=128,trigger='touch')]
        # q uses a palette-heavy floor of different provenance.
        for y in range(24,32):
            for x in range(q['width']):q['layers']['front'][y*q['width']+x]=bind(m7word,68,'front');q['collision']['front'][y*q['width']+x]=1
        p.save(folder/'native.sc4level.json');atlas,maps=compile_graphics(p.data)
        assert len(atlas)>8
        g=Playtest(p.data,folder/'native',fast=True)
        try:
            s=g.session;play.advance(s.lua,60);assert s.read(0x54e)==165
            assert s.read(0x590)==18
            cx,cy=s.read(0x1c),s.read(0x1e)
            s.command('screenshot',folder/'mixed.png');image=Image.open(folder/'mixed.png').convert('RGB')
            matches=0
            for y in range(200,216):
                for x in range(16,240):
                    wx,wy=x+cx,y+cy
                    n,layer,w=resolve(r['layers']['front'][wy//8*64+wx//8],0,'front');pixel=assets[n].tile(w,layer).getpixel((wx%8,wy%8))
                    if pixel[3]:expected=pixel[:3]
                    else:
                        behind=assets[1].tile(back_word,'back').getpixel((wx%8,wy%8))
                        if not behind[3]:continue
                        expected=behind[:3]
                    assert image.getpixel((x,y))==expected,(x,y,image.getpixel((x,y)),expected)
                    matches+=1
            assert matches>1000
            passed(f'Native playtest renders {matches} exact pixels from 17 source/palette combinations including Mode7; transparent front texels reveal foreign BG2')
            # Corrupt an atlas cell index in an otherwise well-formed packet.
            packet=bytearray((g.folder/'level.bin').read_bytes());assert packet[:8]==b'CV4LVL2\0'
            count=struct.unpack_from('<I',packet,14)[0];at=18+count*128+22+0xd600;struct.pack_into('<I',packet,at,0x7fffffff)
            bad=folder/'bad-atlas.bin';bad.write_bytes(packet);s.command('dump',folder/'before.bin')
            try:s.command('level_project',bad)
            except RuntimeError:pass
            else:raise AssertionError('Invalid atlas reference accepted')
            s.command('dump',folder/'after.bin');assert (folder/'before.bin').read_bytes()==(folder/'after.bin').read_bytes()
            passed('Malformed atlas index rejected atomically; active native picture remains unchanged')
            # Native sprite visibility survives host background composition.
            s.command('enemy','workshop on');s.command('enemy','capture on');play.advance(s.lua,1)
            snap=s.snapshot();assert any(a['type']==18 for a in snap['actors'])
            low=Image.open(folder/'mixed.png').convert('RGB');slot=next(a['slot'] for a in snap['actors'] if a['type']==18)
            ax,ay=s.read(slot+0xa)-cx,s.read(slot+0xe)-cy
            s.command('screenshot',folder/'actor.png');actor_image=Image.open(folder/'actor.png').convert('RGB')
            native_visible=0
            for y in range(max(96-cy,ay-20),min(192-cy,ay+20)):
                for x in range(max(160-cx,ax-12),min(256-cx,ax+12)):
                    wx,wy=x+cx,y+cy;n,layer,w=resolve(r['layers']['front'][wy//8*64+wx//8],0,'front');pixel=assets[n].tile(w,layer).getpixel((wx%8,wy%8))
                    if pixel[3] and actor_image.getpixel((x,y))!=pixel[:3]:native_visible+=1
            assert native_visible>5
            passed('Original enemy OAM and visible native sprite pixels remain in front of low-priority mixed artwork')
            # Raising only the original BG priority must cover that same
            # native actor on the back gameplay plane, without changing colors.
            for y in range(12,24):
                for x in range(20,32):r['layers']['front'][y*64+x]|=0x2000
            high,_=compile_project(p.data,folder/'high-priority');s.command('level_project',high);play.advance(s.lua,61)
            cx,cy=s.read(0x1c),s.read(0x1e)
            s.command('screenshot',folder/'high.png');high_image=Image.open(folder/'high.png').convert('RGB');covered=0
            for y in range(104-cy,184-cy):
                for x in range(168-cx,240-cx):
                    pixel=assets[1].tile(back_word|0x2000,'back').getpixel(((x+cx)%8,(y+cy)%8))
                    if pixel[3]:assert high_image.getpixel((x,y))==pixel[:3];covered+=1
            assert covered>500
            passed('Native background priority correctly hides the back-plane monster behind opaque foreign artwork')
            s.write({0x54a:425,0x54e:160});play.advance(s.lua,2);assert s.command('level_room')=='1';play.advance(s.lua,50);assert s.read(0x54e)==165
            passed('Mixed-source room transition installs the next room artwork and keeps native floor collision')
        finally:g.close()
        report['passed']=True
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:(folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(folder,flush=True)
    return report


if __name__=='__main__':check()
