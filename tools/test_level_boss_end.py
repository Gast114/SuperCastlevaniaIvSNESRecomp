"""Encounter intro, return, exit and death reset preserve the custom project."""
import json
from pathlib import Path
import tempfile
from enemy_workshop_native import ROOT,play
from level_assets import Assets,ensure_room
from level_parts import builtin_parts,repeat_part
from level_project import Project,paint
from level_playtest import Playtest

def check(cases=((128,'sequence','continue'),(129,'direct','continue'),(128,'direct','exit'))):
    folder=Path(tempfile.mkdtemp(prefix='boss-end-',dir=ROOT/'artwork-local/level-editor/tests'));print(folder,flush=True)
    report=dict(passed=False,cases=[])
    floor=repeat_part(next(p for p in builtin_parts({2:Assets(ensure_room(2))}) if p['id']=='platform-a03'),16)
    try:
        for kind,start,end in cases:
            p=Project();r=p.data['rooms'][0];r['spawn']=[100,165]
            for x in range(0,r['width'],floor['width']):paint(r,'front',x,24,floor['tiles'],floor['collision'],floor['width'])
            target=p.add_room();p.data['start_room']=r['id']
            r['actors']=[dict(id='skeleton',type=17,variant=0,x=120,y=165,flags=32768),dict(id='boss',type=kind,variant=0,x=500,y=96,flags=32768,boss_start=start,boss_end=end)]
            r['doors']=[dict(id='out',x=900,y=120,w=32,h=48,target=target['id'],target_x=128,target_y=128,trigger='up')]
            g=Playtest(p.data,folder/f'{kind:02x}-{start}-{end}',fast=True)
            try:
                s=g.session;play.advance(s.lua,3);s.command('dump',g.folder/'initial.bin');initial=(g.folder/'initial.bin').read_bytes();assert s.read(0xb8)==0
                s.write({0x54a:450})
                history=[]
                for _ in range(50):
                    s.write({0xbc:32767,0x13f4:16});play.advance(s.lua,1)
                    history.append(s.lua.eval('return mainmemory.read_u16_le(0xb8),mainmemory.read_u16_le(0x590),mainmemory.read_u16_le(0x586),mainmemory.read_u16_le(0x70),mainmemory.read_u16_le(0x54a),mainmemory.read_u16_le(0x54e)')['values'])
                assert s.read(0xb8)>0,history
                s.write({0x1500:0xbeef,0x70:7});play.advance(s.lua,3)
                assert s.read(0xb8)==0 and s.read(0x1500)!=0xbeef
                assert s.command('level_room')==('1' if end=='exit' else '0')
                s.command('dump',g.folder/'returned.bin');returned=(g.folder/'returned.bin').read_bytes();assert returned[0xd400:0x10000]==initial[0xd400:0x10000],'ordinary OBJ resources not restored'
                if end=='continue':
                    s.command('level_project',g.folder/'level.bin');play.advance(s.lua,2);s.write({0x54a:450})
                    for _ in range(8):s.write({0xbc:32767,0x13f4:16});play.advance(s.lua,1)
                    assert s.read(0xb8)>0
                    s.write({0x13f4:0});play.advance(s.lua,3);assert s.command('level_room')=='0' and s.read(0xb8)==0 and s.read(0x13f4)==16
                    assert abs(s.read(0x54a)-100)<4,'death did not return to own spawn'
                    s.write({0x54a:450});play.advance(s.lua,3);assert s.read(0xb8)>0
                    s.write({0x70:12,0x13f4:16});play.advance(s.lua,2);assert s.read(0xb8)==0 and abs(s.read(0x54a)-100)<4,'pit death counted as boss victory'
                row=dict(type=kind,start=start,end=end,original_objects_restored=True,death_reset_checked=end=='continue',pit_death_checked=end=='continue');report['cases'].append(row);print('PASS',row,flush=True)
            finally:g.close()
        report['passed']=True
    finally:(folder/'report.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':check()
