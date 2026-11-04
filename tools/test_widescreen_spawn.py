"""F10 regression: a platform skeleton must not activate before its collision column."""
import argparse
import configparser
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from enemy_workshop_native import ROOT, NativeSession, play


def run(build, fixture, folder, wide):
    session=NativeSession(build=build,folder=folder)
    config=configparser.ConfigParser();config.read(folder/'config.ini');config['Graphics']['Widescreen']=str(wide)
    with (folder/'config.ini').open('w') as f:config.write(f)
    rows=[]
    try:
        session.start(fixture);session.command('enemy','workshop off');session.command('hd','off');session.command('loadfile',fixture)
        for frame in range(161):
            if frame:play.advance(session.lua,1,('Right',))
            actors=session.lua.eval('local t={} for a=0x580,0xe80,0x40 do if mainmemory.read_u16_le(a+0x10)==17 then t[#t+1]=string.format("[%d,%d,%d,%d]",mainmemory.read_u16_le(a+0xa),mainmemory.read_u16_le(a+0xe),mainmemory.read_u16_le(a+0x12),mainmemory.read_u16_le(a+0x14)) end end return "["..table.concat(t,",").."]"')['values'][0]
            state=play.read_state(session.lua);state.pop('frame');state.pop('paused')
            # A02 back-plane collision ring, world (1120,160), not a visual HD tile.
            x,y=1120&511,160
            index=((x&256)<<2)|((x>>3)&31)|((y&256)<<3)|((y<<2)&0x3e0)
            rows.append(dict(frame=frame,actors=json.loads(actors),state=state,platform_collision=session.read(0xa000+index*2)))
        session.command('wram',folder/'final-ram.bin');session.command('screenshot',folder/'final-native.png')
        digest={n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in ('final-ram.bin','final-native.png')}
    finally:session.close()
    return rows,digest


def reverse_and_exit_checks(build,fixture,work):
    folder=work/'reverse-exits';session=NativeSession(build=build,folder=folder)
    config=configparser.ConfigParser();config.read(folder/'config.ini');config['Graphics']['Widescreen']='1'
    with (folder/'config.ini').open('w') as f:config.write(f)
    spawns=0;present=False;maximum=0
    try:
        session.start(fixture);session.command('enemy','workshop off');session.command('hd','off')
        session.command('loadfile',fixture)
        for buttons,frames in [(('Right',),100),(('Left',),150),(('Right',),200)]:
            for _ in range(frames):
                play.advance(session.lua,1,buttons)
                count=int(session.lua.eval('local n=0 for a=0x580,0xe80,0x40 do if mainmemory.read_u16_le(a+0x10)==17 then n=n+1 end end return n')['values'][0])
                maximum=max(maximum,count)
                if count and not present:spawns+=1
                present=count>0
                assert count<=1,'reverse traversal spawned duplicate skeletons'
        assert spawns>=2,('reverse route did not despawn and respawn',spawns)
        # Historical native exit regression: keep the widened actor lifetime,
        # while leaving both directions of the event reader at retail bounds.
        broken=ROOT/'artwork-local/stage01-user-v4/fixtures/F5.sav'
        ready=ROOT/'artwork-local/stage01-user-v4/F5-recovered.sav'
        exits=lambda:int(session.lua.eval('local n=0 for a=0x580,0xe80,0x40 do if mainmemory.read_u16_le(a+0x10)==0x15 then n=n+1 end end return n')['values'][0])
        session.command('loadfile',broken);assert exits()==0
        session.write({0x54a:828,0x1c:700,0x1280:700,0x94:0x83e0})
        for _ in range(8):
            play.advance(session.lua,1);assert exits()==1,'exit culled after reverse spawn'
        session.command('loadfile',ready);assert exits()==1
        play.advance(session.lua,80,('Up',));state=play.read_state(session.lua)
        assert state['block']==6 and state['level_phase']==5 and state['player_y']<256,state
        play.advance(session.lua,10,('Right',));assert play.read_state(session.lua)['player_x']!=state['player_x']
    finally:session.close()
    return dict(skeleton_spawns=spawns,max_skeletons=maximum,native_stair_exit_survives=True,room_transition_resumes=True)


def check(build,fixture,reference=None):
    work=Path(tempfile.mkdtemp(prefix='wide-spawn-check-',dir=ROOT/'build-lua'));print(work,flush=True)
    original=hashlib.sha256(fixture.read_bytes()).hexdigest();shutil.copy2(fixture,work/'F10.sav')
    narrow,narrow_hash=run(build,work/'F10.sav',work/'narrow',0)
    wide,_=run(build,work/'F10.sav',work/'wide',1)
    first=[]
    for label,rows in [('4:3',narrow),('16:9',wide)]:
        spawned=next(v for v in rows if v['actors'])
        assert spawned['platform_collision']!=0,(label,'spawned before platform collision',spawned)
        assert spawned['actors'][0][:2]==[1120,136],(label,'incorrect spawn position')
        assert all(a[1]==136 for v in rows for a in v['actors']),(label,'fell through its platform')
        first.append(spawned['frame'])
    assert first==[74,74],('spawn timing changed',first)
    assert [v['actors'] for v in narrow]==[v['actors'] for v in wide],'widescreen changed skeleton physics/AI'
    assert [v['state'] for v in narrow]==[v['state'] for v in wide],'player/camera state changed'
    if reference:
        baseline,baseline_hash=run(reference,work/'F10.sav',work/'reference-narrow',0)
        assert baseline==narrow and baseline_hash==narrow_hash,'4:3 retail behavior changed'
    edges=reverse_and_exit_checks(build,work/'F10.sav',work)
    assert hashlib.sha256(fixture.read_bytes()).hexdigest()==original
    report=dict(passed=True,fixture_sha256=original,spawn_frame=first,spawn_xy=[1120,136],
                platform_collision_present=True,skeleton_trajectory_identical=True,
                reference_4x3_identical=bool(reference),frames_checked=161,reverse_and_exits=edges)
    (work/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture',type=Path,required=True)
    p.add_argument('--build',type=Path,default=ROOT/'build-lua')
    p.add_argument('--reference-build',type=Path)
    a=p.parse_args();check(a.build.resolve(),a.fixture.resolve(),a.reference_build.resolve() if a.reference_build else None)
