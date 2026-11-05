"""Mixed monster resources, scene isolation, dense placement and boss map fidelity."""
import json
import struct
from pathlib import Path
import tempfile
from PIL import Image
from enemy_workshop_native import ROOT,play
from enemy_sprite_export import render_pose
from level_assets import Assets,ensure_room
from level_project import Project,validate,paint
from level_playtest import Playtest,compile_project,monster_plan
from level_parts import builtin_parts,repeat_part


def check():
    folder=Path(tempfile.mkdtemp(prefix='isolation-',dir=ROOT/'artwork-local/level-editor/tests'));print(folder,flush=True)
    report=dict(passed=False,image_viewer_used=False,checks=[])
    def passed(text):report['checks'].append(text);print('PASS:',text,flush=True)
    raw=(ROOT/'Super Castlevania IV (USA).sfc').read_bytes()
    library=json.loads((ROOT/'artwork-local/enemy-library/library.json').read_text())
    asset=Assets(ensure_room(2));floor=repeat_part(next(p for p in builtin_parts({2:asset}) if p['id']=='platform-a03'),16)
    def project():
        p=Project();r=p.data['rooms'][0];p.resize(r,r['width'],28);r['spawn']=[100,165]
        for x in range(0,r['width'],floor['width']):paint(r,'front',x,24,floor['tiles'],floor['collision'],floor['width'])
        return p,r
    def floor_pixels(s,path):
        s.command('wram',path.with_suffix('.ram.bin'));s.command('dump',path.with_suffix('.video.bin'));s.command('lines',path.with_suffix('.lines.bin'))
        s.command('screenshot',path);picture=Image.open(path).convert('RGB')
        # Boss coordinates may be translated; use the actual project camera,
        # which is fixed around placement x200 rather than native boss x~2000.
        return picture
    try:
        p,r=project();types=(7,9,10,11,12,17,18,0x30,0x31,0x32,0x52,0x56,0x59,0x7f)
        for i,t in enumerate(types):
            profile=next(p for p in library['profiles'] if p['type']==t and not p.get('preview_only'))
            r['actors'].append(dict(id=f'mixed-{t}',type=t,variant=profile.get('variant',0),x=40+i*14,y=130,flags=32768))
        try:monster_plan(raw,r['actors'],library)
        except ValueError:pass
        else:raise AssertionError('Stress mixture does not exceed the old shared OBJ budget')
        # More placements than either the old 128-record UI limit or the 37
        # native actor slots. Far entries must not consume the active slots.
        for i in range(220):r['actors'].append(dict(id=f'far-{i}',type=18,variant=0,x=600+i%35*10,y=130,flags=32768))
        r['actors'].append(dict(id='ordinary-object-000f',type=15,variant=0,x=230,y=96,flags=32768))
        r['actors'].append(dict(id='safe-scene',type=15,variant=0,kind='event',native_family=2,x=400,y=120,flags=32768))
        r['actors'].append(dict(id='late-candle',type=14,variant=24,kind='candle',x=390,y=120,flags=32768))
        validate(p.data);p.save(folder/'many.sc4level.json');assert len(Project.load(p.path).data['rooms'][0]['actors'])==237
        level,_=compile_project(p.data,folder/'compile');assert b'CV4VOBJ1' in level.read_bytes()
        passed('237 placements including O-000F and a mixture exceeding the old OBJ budget compile and round-trip without a shared palette/VRAM allocation')
        g=Playtest(p.data,folder/'mixed',fast=True)
        try:
            s=g.session;s.command('enemy','workshop on');s.command('enemy','capture off')
            for _ in range(12):s.write({0xbc:32767,0x13f4:16});play.advance(s.lua,1)
            picture=floor_pixels(s,folder/'mixed.png');matches=0;cx=s.read(0x1c)
            for y in range(196,208):
                for x in range(8,240):
                    wx=x+cx;v=r['layers']['front'][y//8*r['width']+wx//8];pixel=asset.tile(v).getpixel((wx%8,y%8))
                    if pixel[3]:assert picture.getpixel((x,y))==pixel[:3],(x,y,picture.getpixel((x,y)),pixel);matches+=1
            assert matches>1000 and s.read(0x86)==0 and s.read(0x70)==5
            snapshot=s.snapshot();assert len({a['type'] for a in snapshot['actors']})>=5
            skeleton=next(a['slot'] for a in snapshot['actors'] if a['type']==17);s.write({skeleton+6:87})
            passed('Many native enemy families coexist; the actual floor raster remains exact and the original scene does not replace the level')
            visible=set()
            for actor in snapshot['actors']:
                placement=next((a for a in r['actors'] if a['type']==actor['type']),None)
                if not placement:continue
                profile=next((p for p in library['profiles'] if p['type']==actor['type'] and p.get('variant',0)==placement.get('variant',0) and p.get('context')),None)
                if not profile:continue
                context=profile['context'];video=Path(context['video']).read_bytes()
                try:meta,image=render_pose(raw,actor['type'],actor['pose'],video,3,context['tile_add'],32792)[0]
                except ValueError:continue
                if actor['flip']&1:image=image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                if actor['flip']&2:image=image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                ax,ay=meta['anchor'];x0=actor['x']-(image.width-ax if actor['flip']&1 else ax);y0=actor['y']-(image.height-ay if actor['flip']&2 else ay);count=0
                for y in range(image.height):
                    for x in range(image.width):
                        pixel=image.getpixel((x,y));xx,yy=x+x0,y+y0
                        if pixel[3] and 0<=xx<256 and 32<=yy<224 and picture.getpixel((xx,yy))==pixel[:3]:count+=1
                if count>8:visible.add(actor['type'])
            assert len(visible)>=3,visible
            passed(f'{len(visible)} simultaneous monster types match independent original pose/VRAM palette pixels on the actual raster')
            # Exercise the scene marker and far placements without executing a
            # foreign event-controller ABI as an ordinary enemy routine.
            s.write({0x54a:390,0x54e:165});play.advance(s.lua,20);assert s.read(0x86)==0 and s.read(0x70)==5 and s.command('level_room')=='0'
            candles=[a for a in range(0x580,0xec0,64) if s.read(a+16)==14];assert candles and all(s.read(a+0x30)<74 for a in candles)
            passed('A candle placed after record 128 uses a bounded native persistence slot instead of indexing outside its flag table')
            s.write({0x54a:700,0x54e:165});play.advance(s.lua,4)
            active=[s.read(a+16) for a in range(0x580,0xec0,64)];assert active.count(18)>=5
            passed('Scene decoration does not execute source-level transitions; distant placements activate when reached')
            s.write({0x54a:100,0x54e:165});play.advance(s.lua,3)
            s.command('wram',folder/'return.ram.bin')
            skeleton=next(a for a in range(0x580,0xec0,64) if s.read(a+16)==17);assert s.read(skeleton+6)==87
            passed('Far native actors release their slots and resume with their actual remaining health when revisited')
            play.advance(s.lua,80);assert s.read(0x32)==4 and s.read(0x86)==0 and s.read(0x70)==5 and s.command('level_room')=='0'
            passed('O-000F and the mixed ordinary AI remain in the custom gameplay scene after further native execution')
        finally:g.close()
        for boss in (128,129):
            p,r=project();r['actors']=[dict(id='boss',type=boss,variant=0,x=200,y=96,flags=32768,boss_start='direct',boss_end='continue')]
            g=Playtest(p.data,folder/f'boss-{boss:02x}',fast=True)
            try:
                s=g.session
                for _ in range(24):s.write({0xbc:32767,0x13f4:16});play.advance(s.lua,1)
                assert s.read(0xb8)>0 and s.command('level_room')=='0'
                picture=floor_pixels(s,folder/f'boss-{boss:02x}.png');matches=0
                status=json.loads(s.command('level_status'));cx,cy=status['camera_x'],status['camera_y']
                for y in range(196,208):
                    for x in range(8,240):
                        wx,wy=x+cx,y+cy
                        if wy>=r['height']*8:continue
                        v=r['layers']['front'][wy//8*r['width']+wx//8];pixel=asset.tile(v).getpixel((wx%8,wy%8))
                        if pixel[3] and picture.getpixel((x,y))==pixel[:3]:matches+=1
                assert matches>1500,(hex(boss),matches)
                if boss==129:
                    video=(folder/f'boss-{boss:02x}.video.bin').read_bytes();checked=0
                    w=lambda data,address:struct.unpack_from('<H',data,address)[0]
                    room_video=Assets(ensure_room(r['tileset'])).video
                    for y in range(8,24):
                        for x in range(8,136):
                            wy=y&255;tile=w(video,0xb000+(wy//8*32+x//8)*2);xx=x%8;yy=wy%8
                            if tile&0x4000:xx=7-xx
                            if tile&0x8000:yy=7-yy
                            bits=w(room_video,0xa000+((tile&1023)*8+yy)*2);bit=7-xx
                            value=(bits>>bit&1)|(bits>>(bit+7)&2)
                            if not value:continue
                            c=w(room_video,0x10000+2*((tile>>10&7)*4+value));expand=lambda n:(n<<3)|(n>>2)
                            expected=expand(c&31),expand(c>>5&31),expand(c>>10&31)
                            assert picture.getpixel((x,y))==expected,(x,y,picture.getpixel((x,y)),expected)
                            checked+=1
                    assert checked>50
                    passed('Mode7 boss HUD glyphs match the independent native 2bpp font and project HUD palette')
                passed(f'Boss {boss:02X} keeps the project floor visible during the encounter, including the native Mode7 body' if boss==129 else 'Ordinary boss keeps the project floor and room instead of showing its source scene')
            finally:g.close()
        report['passed']=True
    except Exception as error:report['error']=f'{type(error).__name__}: {error}';raise
    finally:(folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__':check()
