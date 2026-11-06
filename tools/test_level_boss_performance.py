"""Real-time boss regression with audio enabled and uninterrupted simulation.

Optional --marker replays the user's level packet and debug state in a private
session. This does not load or modify anything in the player's running game.
"""
import argparse
import configparser
import json
import os
from pathlib import Path
import tempfile
import time
from enemy_workshop_native import ROOT,NativeSession,play
from level_assets import Assets,ensure_room
from level_playtest import compile_project,start_playtest_session
from level_project import Project


def measure(folder,level,monsters,build,marker=None):
    session=NativeSession(build=build,folder=folder/'game')
    cfg=configparser.ConfigParser();cfg.read(session.folder/'config.ini')
    cfg['General'].update(DisableFrameDelay='0',RunAhead='0')
    cfg['Graphics']['WindowScale']='4';cfg['Sound']['EnableAudio']='1';cfg['Rewind']={'Enabled':'0'}
    with (session.folder/'config.ini').open('w') as file:cfg.write(file)
    try:
        start_playtest_session(session)
        session.command('enemy','workshop off');session.command('enemy','capture off')
        session.command('enemy_resources',monsters)
        session.lua.eval('for a=0x13a0,0x13b5 do mainmemory.write_u8(a,255) end')
        session.command('level_project',level);play.advance(session.lua,2)
        if marker:session.command('loadfile',marker/'state.sav')
        session.write({0xbc:32767,0x13f4:16});session.command('window','show')
        play.advance(session.lua,60)  # Complete the one legitimate load's audio priming.
        before=json.loads(session.command('level_status'))
        first=int(session.lua.eval('return emu.framecount()')['values'][0])
        session.lua.command('resume');start=time.perf_counter();previous=start;frame=first;samples=[]
        for _ in range(8):
            time.sleep(.5)
            next_frame=int(session.lua.eval('return emu.framecount()')['values'][0]);now=time.perf_counter()
            samples.append((next_frame-frame)/(now-previous));previous=now;frame=next_frame
        duration=previous-start;session.lua.command('pause')
        after=json.loads(session.command('level_status'))
        result=dict(fps=(frame-first)/duration,half_second_fps=samples,seconds=duration,
                    boss_count=after['free_bosses'],boss_states=after['free_actors'])
        for field in ('audio_underflows','audio_priming','audio_consumed'):
            if field in after:result[field+'_delta']=after[field]-before[field]
        # Exercise the movement/whip path as well as a stationary hero. Short
        # alternating walks keep the bosses near the camera throughout.
        move_start=time.perf_counter()
        session.lua.run('for i=1,240 do local left=i%60<30 joypad.set({Left=left,Right=not left,Y=i%16<8},1) emu.frameadvance() end')
        play.wait_idle(session.lua)
        result['walk_and_whip_fps']=240/(time.perf_counter()-move_start)
        (folder/'timing.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result),flush=True)
        assert result['fps']>=55 and min(samples)>=48,result
        assert result['walk_and_whip_fps']>=55,result
        assert after['free_bosses'] and all(not a['error'] for a in after['free_actors']),after
        if 'audio_priming_delta' in result:
            assert result['audio_priming_delta']<=3 and result['audio_underflows_delta']<=2,result
            assert result['audio_consumed_delta']>=duration*24000,result
        return result
    finally:session.close()


def check(build=None,marker=None):
    folder=Path(tempfile.mkdtemp(prefix='boss-realtime-',dir=ROOT/'artwork-local/level-editor/tests'))
    print(folder,flush=True);report=dict(passed=False,audio_enabled=True,audio_driver=os.environ.get('SDL_AUDIODRIVER','default'),image_viewer_used=False,cases={})
    try:
        if marker:
            marker=Path(marker).resolve();packet=marker.parents[2]
            report['cases']['user-marker']=measure(folder/'user-marker',packet/'level.bin',packet/'monsters.bin',build,marker)
        for count in ((3,) if marker else (1,3)):
            project=Project();r=Assets(ensure_room(0)).import_room(include_objects=True)
            project.data['rooms']=[r];project.data['start_room']=r['id'];r['spawn']=[157,165]
            for n,t in enumerate((137,128,129)[:count]):
                r['actors'].append(dict(id=f'free-{t}',type=t,variant=0,x=150+n*40,y=120 if t==129 else 165,
                    flags=32768,boss_mode='free',stats=dict(hp=16384,contact_damage=7)))
            level,monsters=compile_project(project.data,folder/f'compile-{count}',build=build)
            result=measure(folder/f'bosses-{count}',level,monsters,build)
            assert result['boss_count']==count,result
            report['cases'][str(count)]=result
        report['passed']=True
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:(folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build',type=Path);parser.add_argument('--marker',type=Path)
    parser.add_argument('--audio-driver',help='SDL audio backend; dummy exercises callbacks/queue pacing without an output device')
    args=parser.parse_args()
    if args.audio_driver:os.environ['SDL_AUDIODRIVER']=args.audio_driver
    check(args.build,args.marker)
