"""Replay the user's whip upgrade and death with HD on/off in isolation."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import time

import numpy as np
from PIL import Image
import sciv_play as play
import sciv_test_support as sciv


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--pack',type=Path,required=True)
    p.add_argument('--whip',type=Path,required=True)
    p.add_argument('--death',type=Path,required=True)
    sciv.add_build_arg(p);a=p.parse_args()
    build=sciv.build_dir(a);work=sciv.work_dir(build,'hd-effects-')
    folder=work/'game';exe=sciv.prepare(folder,build,{'Graphics':{'Widescreen':1},'General':{'DisableFrameDelay':1}})
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    lua=None;report={}
    with (folder/'game.log').open('w') as log:
        proc=subprocess.Popen([str(exe),str(a.rom.resolve())],cwd=folder,
            env=sciv.clean_env(SNESRECOMP_LUA_PORT=port,SNESRECOMP_LUA_PAUSED=1),
            startupinfo=sciv.hidden_window(),stdout=log,stderr=log)
        try:
            for _ in range(200):
                if proc.poll() is not None:raise RuntimeError('Game exited')
                try:lua=play.LuaClient(port=port);lua.command('ping');break
                except OSError:time.sleep(.05)
            assert lua
            def command(n,arg=''):
                return lua.eval(f'return game.command({json.dumps(n)},{json.dumps(str(arg))})')['values'][0]
            command('hd','pack '+str(a.pack.resolve()));command('hd','scale 10')
            for name,fixture,total,target in [('upgrade',a.whip,112,10),('death',a.death,192,12)]:
                runs=[];seen=set()
                for enabled in (False,True):
                    command('hd','on' if enabled else 'off');command('loadfile',fixture.resolve())
                    samples=[]
                    for n in range(0,total,4):
                        play.advance(lua,4,('Y',) if name=='upgrade' and n<12 else ())
                        state=play.read_state(lua)
                        state.pop('frame');state.pop('paused')
                        shot=work/f'{name}-{int(enabled)}-{n:03}.png';command('screenshot',shot)
                        pixels=np.array(Image.open(shot).convert('RGB'))
                        hd=json.loads(command('hd'))
                        phase=state['level_phase']
                        if enabled and phase in (5,10,12) and np.ptp(pixels[40:].astype(int))>20:
                            assert hd['matched']>0,(name,n,phase,'visible frame fell back to native')
                            if phase not in seen:
                                command('hdshot',work/f'{name}-phase{phase}-hd.png');seen.add(phase)
                        samples.append({'state':state,'sha':__import__('hashlib').sha256(pixels.tobytes()).hexdigest(),'hd':hd})
                    runs.append(samples)
                assert target in seen,(name,'fixture missed target phase',seen)
                for original,hd in zip(*runs):
                    assert original['state']==hd['state'],(name,'HD changed simulation')
                    assert original['sha']==hd['sha'],(name,'HD changed native image')
                report[name]={'phases_with_hd':sorted(seen),'samples':runs[1]}
            report['passed']=True
            (work/'report.json').write_text(json.dumps(report,indent=2))
            print('PASS: whip phase 10, death phase 12 retain HD; native frames and named simulation fields identical')
        finally:
            if lua:lua.close()
            proc.terminate();proc.wait(timeout=10)


if __name__=='__main__':main()
