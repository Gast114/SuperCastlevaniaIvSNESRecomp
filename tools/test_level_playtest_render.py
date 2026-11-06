"""Regression for the user's A01 playtest markers: hidden boot and foreign OBJ.

Checks actual raster pixels without opening an image viewer. Also poisons the
unused native BG3 map to catch HUD/CHR leaking into the custom playfield.
"""
import configparser
import json
from pathlib import Path
import struct
import tempfile
import time

import numpy as np
from PIL import Image
from enemy_workshop_native import ROOT,NativeSession,play
from enemy_sprite_export import Graphics,descriptor
from level_assets import Assets,ensure_room
from level_playtest import Playtest,compile_project
from level_project import Project


def check():
    folder=Path(tempfile.mkdtemp(prefix='marker-render-',dir=ROOT/'artwork-local/level-editor/tests'))
    print(folder,flush=True)
    report=dict(passed=False,image_viewer_used=False,checks=[])
    def passed(text):report['checks'].append(text);print('PASS:',text,flush=True)
    p=Project();r=Assets(ensure_room(0)).import_room(include_objects=True)
    p.data['rooms']=[r];p.data['start_room']=r['id']
    for i,(t,x,y) in enumerate(((11,96,173),(11,145,175),(7,107,124),(9,64,189))):
        r['actors'].append(dict(id=f'marker-{i}',type=t,variant=0,x=x,y=y,flags=32768))
    level,bundle=compile_project(p.data,folder/'compile')
    packet=level.read_bytes();count=struct.unpack_from('<I',packet,14)[0]
    atlas=np.frombuffer(packet,dtype='<u2',count=count*64,offset=18).reshape(count,8,8)
    room_at=20+count*128;video_at=room_at+22;maps_at=video_at+0x10200
    maps=np.frombuffer(packet,dtype='<u4',count=2*r['width']*r['height'],offset=maps_at).reshape(2,r['height'],r['width'])
    at=packet.index(b'CV4VOBJ1')+10+32768;contexts={}
    for _ in range(struct.unpack_from('<H',packet,at-32768-2)[0]):
        t,var,add,pose,w,h,ax,ay=struct.unpack_from('<8H',packet,at);at+=16
        contexts[t,var]=(add,packet[at:at+0x10200],w,h,ax,ay);at+=0x10200+w*h*4
    yy,xx=np.indices((224,256));total=0
    def verify(s,tag):
        nonlocal total
        s.command('screenshot',folder/f'{tag}.png');s.command('dump',folder/f'{tag}.video.bin')
        video=(folder/f'{tag}.video.bin').read_bytes();image=np.array(Image.open(folder/f'{tag}.png').convert('RGB'))
        status=json.loads(s.command('level_status'));cx,cy=status['camera_x'],status['camera_y']
        assert cy==0 and s.read(0xa6)==0,(tag,status,s.read(0xa6))
        wx,wy=xx+cx,yy+cy;depth=np.zeros((224,256),dtype=np.uint16)
        expected=np.full((224,256),struct.unpack_from('<H',packet,video_at+0x10000)[0],dtype=np.uint16)
        for layer in (1,0):
            value=maps[layer,wy//8,wx//8];color=atlas[value&0x7fffffff,wy%8,wx%8]
            z=np.where(value&0x80000000,0xb100 if layer else 0xc000,0x7100 if layer else 0x8000)
            take=((color&0x8000)!=0)&(z>depth);expected[take]=color[take]&32767;depth[take]=z[take]
        rgb=np.stack([(expected>>shift)&31 for shift in (0,5,10)],axis=-1);rgb=((rgb<<3)|(rgb>>2)).astype('uint8')
        mask=yy>=32
        for n in range(128):
            x,y,attr=struct.unpack_from('<BBH',video,0x10200+n*4);hi=video[0x10400+n//4]>>(n%4*2)&3
            x+=256*(hi&1);x=x-512 if x>=256 else x;size=16 if hi&2 else 8
            mask &= ~((xx>=x)&(xx<x+size)&(yy>=y)&(yy<y+size))
        for a in r['actors']:
            if a.get('kind')!='event':continue
            _,_,w,h,ax,ay=contexts.get((a['type'],a['variant']),(0,b'',0,0,0,0))
            x,y=a['x']-cx-ax,a['y']-cy-ay
            mask &= ~((xx>=x)&(xx<x+w)&(yy>=y)&(yy<y+h))
        bad=mask&np.any(image!=rgb,axis=-1)
        assert not bad.any(),(tag,int(bad.sum()),np.argwhere(bad)[:5].tolist())
        assert int(mask.sum())>15000
        assert status['sampled_lines']==192 and status['failed_lines']==0,status
        total+=int(mask.sum())
        return image
    def moving_sprite(s):
        # Reproduce a measured one-pixel RAM/OAM discrepancy from the user's
        # combination. Decode the actual emitted OBJ with the independent
        # source context, rather than expecting it at the newer RAM position.
        s.command('wram',folder/'moving.ram.bin');ram=(folder/'moving.ram.bin').read_bytes()
        video=(folder/'moving-foreign.video.bin').read_bytes();image=Image.open(folder/'moving-foreign.png').convert('RGB')
        word=lambda at:struct.unpack_from('<H',ram,at)[0]
        base=next(b for b in range(0x580,0xec0,64) if word(b+16)==9)
        profile=next(p for p in json.loads((ROOT/'artwork-local/enemy-library/library.json').read_text())['profiles'] if p['type']==9 and p.get('context') and not p.get('preview_only'))
        context=profile['context'];graphics=Graphics(Path(context['video']).read_bytes(),context['obsel'])
        attrs=set();flip=word(base+4);priority=word(base+2)
        for x,y,raw in descriptor((ROOT/'Super Castlevania IV (USA).sfc').read_bytes(),word(base)):
            attr=(raw|0x2000)^flip
            if priority&0x8000:attr=(attr&0xcfff)|((priority*2&255)<<8)
            attrs.add((attr+word(base+38))&65535)
        matches=0
        for n in range(128):
            x,y,attr=struct.unpack_from('<BBH',video,0x10200+n*4);hi=video[0x10400+n//4]>>(n%4*2)&3
            x+=256*(hi&1);x=x-512 if x>=256 else x;size=16 if hi&2 else 8
            if attr not in attrs:continue
            for dy in range(size):
                for dx in range(size):
                    xx,yy=x+dx,y+dy
                    value,color=graphics.pixel(attr,size,dx,dy)
                    if value and 0<=xx<256 and 32<=yy<224 and image.getpixel((xx,yy))==color[:3]:matches+=1
        assert matches>16,matches
        report['moving_sprite_pixels_matched']=matches
    try:
        g=Playtest(p.data,folder/'ready',fast=True)
        try:
            s=g.session
            assert json.loads(s.command('window','status'))['visible']==0
            assert json.loads(s.command('level_status'))['active']
            assert any(s.read(b+16)==11 and s.read(b)>=32768 for b in range(0x580,0xec0,64))
            verify(s,'ready')
            g.show();assert json.loads(s.command('window','status'))['visible']>0
            s.command('window','hide')
            passed('F5 stays hidden during bootstrap; the first exposed field already contains the project and initialized foreign monsters')
            s.write({0xbc:32767,0x13f4:16});play.advance(s.lua,14);verify(s,'moving-foreign');moving_sprite(s)
            passed('Moving M-0009 uses its own original texture at the actual emitted OBJ position even when native RAM has already moved')
            for i in range(12):
                s.write({0xbc:32767,0x13f4:16});play.advance(s.lua,24,('Right','Y') if i%2 else ('Right',))
                verify(s,f'walk-{i}')
            # Real collision/damage, not an invulnerable capture-only arena.
            target=next(b for b in range(0x580,0xec0,64) if s.read(b+16)==11)
            s.write({0x54a:s.read(target+10),0x54e:s.read(target+14),0xbc:0,0x13f4:16})
            play.advance(s.lua,8);assert s.read(0x13f4)<16
            verify(s,'contact')
            s.lua.command('resume');time.sleep(.5);s.lua.command('pause');verify(s,'continuous')
            passed('The user marker combination preserves background and transparent air while walking, whipping, taking contact damage and running continuously with workshop capture disabled')
        finally:g.close()
        # Foreign upload residue must never turn BG3 into a second HUD below
        # the real HUD, nor occlude an immutable custom background tile.
        poison=bytearray(packet)
        for row in range(4,32):
            for col in range(32):struct.pack_into('<H',poison,video_at+0xb000+2*(row*32+col),0x2041)
        badfile=folder/'native-bg3-residue.bin';badfile.write_bytes(poison)
        s=NativeSession(folder=folder/'reference-config')
        cfg=configparser.ConfigParser();cfg.read(s.folder/'config.ini');cfg['Graphics']['NewRenderer']='0'
        with (s.folder/'config.ini').open('w') as f:cfg.write(f)
        try:
            s.start(defer_show=True);s.command('enemy','workshop off');s.command('enemy','capture off')
            s.command('enemy_resources',bundle);s.lua.eval('for a=0x13a0,0x13b5 do mainmemory.write_u8(a,255) end')
            s.command('level_project',badfile);play.advance(s.lua,12)
            verify(s,'bg3-residue-reference-config')
            # The host restores the configured flag after drawing. The
            # custom compositor must work without changing that preference.
            assert json.loads(s.command('level_status'))['requested_render_flags']==0
            passed('A reference-renderer configuration and deliberately stale high-priority BG3 glyphs cannot remove the level or leak native CHR into the playfield')
        finally:s.close()
        report['background_pixels_checked']=total;report['passed']=True
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:(folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':check()
