"""Native boss AI/combat in independent contexts, with an unchanged shared map."""
import json
from pathlib import Path
import tempfile
import time
from PIL import Image
from enemy_workshop_native import ROOT,play
from level_assets import Assets,ensure_room
from level_parts import builtin_parts,repeat_part
from level_project import Project,paint
from level_playtest import Playtest


def check():
    folder=Path(tempfile.mkdtemp(prefix='free-bosses-',dir=ROOT/'artwork-local/level-editor/tests'))
    print(folder,flush=True);report=dict(passed=False,image_viewer_used=False,checks=[],bosses=[])
    asset=Assets(ensure_room(2));floor=repeat_part(next(p for p in builtin_parts({2:asset}) if p['id']=='platform-a03'),16)
    def project(actors):
        p=Project();r=p.data['rooms'][0];p.resize(r,128,28);r['spawn']=[50,165]
        for x in range(0,r['width'],floor['width']):paint(r,'front',x,24,floor['tiles'],floor['collision'],floor['width'])
        r['actors']=actors;return p
    def actor(t,x,y,hp=333,**extra):return dict(id=f'{t}-{x}',type=t,variant=0,x=x,y=y,flags=32768,boss_mode='free',stats=dict(hp=hp,contact_damage=7),**extra)
    def status(s):return json.loads(s.command('level_status'))
    def passed(message):report['checks'].append(message);print('PASS:',message,flush=True)
    try:
        # Identical ordinary types with different values must not share a UI
        # default or lose overrides to their native initialization routine.
        p=project([actor(11,90,165,111),actor(11,230,165,222)])
        g=Playtest(p.data,folder/'ordinary',fast=True)
        try:
            s=g.session;play.advance(s.lua,12)
            slots=[b for b in range(0x580,0xec0,64) if s.read(b+16)==11]
            assert sorted(s.read(b+6) for b in slots)==[111,222]
            s.write({slots[0]+6:70});play.advance(s.lua,16);assert s.read(slots[0]+6)==70
            passed('Ordinary per-instance HP overrides survive native initialization; taking damage does not refill health')
        finally:g.close()

        p=project([actor(128,110,152,100),actor(128,200,152,150),actor(18,235,165,777)])
        g=Playtest(p.data,folder/'mixed',fast=True)
        try:
            s=g.session;seen=set()
            for _ in range(8):
                s.write({0xbc:32767,0x13f4:16});play.advance(s.lua,30)
                v=status(s);assert v['boss_encounter']==-1 and s.read(0xb8)==0
                assert len(v['free_actors'])==2 and [a['hp'] for a in v['free_actors']]==[100,150]
                assert all(not a['error'] and not a['dead'] for a in v['free_actors'])
                seen.add(tuple((a['state'],a['timer'],a['x'],a['y']) for a in v['free_actors']))
            assert len(seen)>4 and any(s.read(b+16)==18 for b in range(0x580,0xec0,64))
            s.write({0x54a:380,0x54e:165});play.advance(s.lua,2);assert status(s)['camera_x']>=250 and s.read(0xa0)==0
            passed('Two copies of the same boss keep independent HP and native movement alongside a normal monster; the real camera remains free to scroll')
        finally:g.close()

        p=project([actor(128,110,152,111),actor(129,160,110,222),actor(137,210,160,444),actor(18,235,165,777)])
        g=Playtest(p.data,folder/'different-bosses',fast=True)
        try:
            s=g.session
            for _ in range(6):
                s.write({0xbc:32767,0x13f4:16});play.advance(s.lua,30);v=status(s)
                assert v['boss_encounter']==-1 and s.read(0xb8)==0
                assert [a['hp'] for a in v['free_actors']]==[111,222,444]
                assert all(not a['error'] and a['drawn']>0 for a in v['free_actors']),v
                assert v['free_actors'][1]['body_pixels']>300
                assert any(s.read(b+16)==18 for b in range(0x580,0xec0,64))
            passed('Three different boss families, including Mode7, coexist with independent native states and a normal skeleton')
        finally:g.close()

        p=project([actor(137,150,160)])
        g=Playtest(p.data,folder/'combat',fast=True)
        try:
            s=g.session;s.write({0xbc:0,0x13f4:16,0x54a:150,0x54e:165});play.advance(s.lua,4)
            assert s.read(0x13f4)==9,s.read(0x13f4)
            for _ in range(16):
                a=status(s)['free_actors'][0];s.write({0xbc:32767,0x13f4:16,0x54a:max(24,a['x']-24),0x54e:165})
                play.advance(s.lua,4,('Y',));play.advance(s.lua,4)
                if status(s)['free_actors'][0]['hp']<333:break
            assert status(s)['free_actors'][0]['hp']<333
            passed('A free boss deals the configured seven HP of contact damage, and the real native whip removes boss HP')
        finally:g.close()

        # A fresh one-HP boss dies to a real whip without ending the room or
        # removing the other ordinary actors from the shared native scene.
        p=project([actor(137,150,160,1),actor(18,235,165,777)])
        g=Playtest(p.data,folder/'death',fast=True)
        try:
            s=g.session
            for _ in range(24):
                a=status(s)['free_actors'][0];s.write({0xbc:32767,0x13f4:16,0x54a:max(24,a['x']-24),0x54e:165})
                play.advance(s.lua,4,('Y',));play.advance(s.lua,4)
                if not status(s)['free_actors'][0]['hp']:break
            assert status(s)['free_actors'][0]['hp']==0
            s.write({0xbc:32767,0x13f4:16});play.advance(s.lua,200)
            assert status(s)['free_actors'][0]['dead'] and s.read(0x70)==5 and s.command('level_room')=='0'
            passed('A free boss can die and finish its own death state without a level-clear sequence or room transition')
        finally:g.close()

        for t in range(128,142):
            p=project([actor(t,150,155 if t in (128,133,137,138) else 110),actor(18,235,165,777)])
            g=Playtest(p.data,folder/f'boss-{t:02x}',fast=True);start=time.monotonic();states=set();visible=0
            try:
                s=g.session
                for _ in range(6):
                    s.write({0xbc:32767,0x13f4:16});play.advance(s.lua,30);v=status(s);a=v['free_actors'][0]
                    assert not a['error'] and a['hp']==333 and v['boss_encounter']==-1 and s.read(0xb8)==0,(t,v)
                    states.add((a['state'],a['timer'],a['x'],a['y']));visible=max(visible,a['drawn'])
                    if t==129:assert 300<a['body_pixels']<256*224,a
                assert len(states)>1 and visible>0,(t,states,visible)
                s.command('screenshot',folder/f'{t:02x}.png');picture=Image.open(folder/f'{t:02x}.png').convert('RGB')
                # These far-left floor pixels are outside every placed body.
                matches=possible=0
                for y in range(200,216):
                    for x in range(8,40):
                        word=p.data['rooms'][0]['layers']['front'][y//8*128+x//8];pixel=asset.tile(word).getpixel((x%8,y%8))
                        if pixel[3]:
                            possible+=1
                            if picture.getpixel((x,y))==pixel[:3]:matches+=1
                assert possible>=256 and matches>=possible*.9,(hex(t),matches,possible)
                row=dict(type=t,distinct_native_states=len(states),visible_parts=visible,floor_pixels=matches,simulation_seconds=round(time.monotonic()-start,3));report['bosses'].append(row);print(row,flush=True)
            finally:g.close()
        passed('All 14 free native boss groups move and render without replacing the shared floor; Mode7 has a real sampled transparent body')
        report['passed']=True
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:(folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':check()
