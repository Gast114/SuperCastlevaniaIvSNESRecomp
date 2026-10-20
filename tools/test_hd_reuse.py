"""Cached and uncached HD output must match through animation/load/settings changes."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time
import sciv_play as play
import sciv_test_support as sciv


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','pack','bridge','whip','death'):
        p.add_argument('--'+name,type=Path,required=True)
    sciv.add_build_arg(p);a=p.parse_args();build=sciv.build_dir(a);work=sciv.work_dir(build,'hd-reuse-')
    runs=[]
    for reuse in (False,True):
        folder=work/str(int(reuse));exe=sciv.prepare(folder,build,{'Graphics':{'Widescreen':1},'General':{'DisableFrameDelay':1}})
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        env=sciv.clean_env(SNESRECOMP_LUA_PORT=port,SNESRECOMP_LUA_PAUSED=1,SNESRECOMP_CV4_CPU_TIMING=0)
        if reuse:env.pop('SCIV_HD_NO_REUSE',None)
        else:env['SCIV_HD_NO_REUSE']='1'
        lua=None;samples=[]
        with (folder/'game.log').open('w') as log:
            proc=subprocess.Popen([str(exe),str(a.rom.resolve())],cwd=folder,env=env,stdout=log,stderr=log,startupinfo=sciv.hidden_window())
            try:
                for _ in range(200):
                    try:lua=play.LuaClient(port=port);lua.command('ping');break
                    except OSError:
                        assert proc.poll() is None;time.sleep(.05)
                assert lua
                def cmd(n,arg=''):return lua.eval(f'return game.command({json.dumps(n)},{json.dumps(str(arg))})')['values'][0]
                def sample(label):
                    state=play.read_state(lua);state.pop('frame');state.pop('paused')
                    cmd('screenshot',folder/'native.png')
                    samples.append({'label':label,'state':state,'hd':cmd('hdhash'),
                        'native':hashlib.sha256((folder/'native.png').read_bytes()).hexdigest()})
                cmd('hd','pack '+str(a.pack.resolve()));cmd('hd','on');cmd('hd','scale 10')
                for label,fixture,total,buttons in [('bridge',a.bridge,360,('Right',)),('whip',a.whip,112,('Y',)),('death',a.death,192,())]:
                    cmd('loadfile',fixture.resolve())
                    for n in range(0,total,4):
                        play.advance(lua,4,buttons if label!='whip' or n<12 else ())
                        sample(f'{label}-{n+4}')
                    cmd('hdshot',folder/(label+'-hd.png'))
                for scale in (2,10,4,10):
                    cmd('hd',f'scale {scale}');play.advance(lua,2);sample('scale-'+str(scale))
                cmd('loadfile',a.bridge.resolve());play.advance(lua,2);sample('load')
                cmd('hd','layers 0');play.advance(lua,2);sample('layers-off')
                cmd('hd','layers 31');play.advance(lua,2);sample('layers-on')
                cmd('hd','off');play.advance(lua,4);cmd('hd','on');play.advance(lua,2);sample('toggle')
                cmd('hd','pack '+str(a.pack.resolve()));play.advance(lua,2);sample('reload')
            finally:
                if lua:lua.close()
                proc.terminate();proc.wait(timeout=10)
        runs.append(samples)
    for uncached,cached in zip(*runs):assert uncached==cached,(uncached,cached)
    assert len(runs[0])==len(runs[1])
    (work/'report.json').write_text(json.dumps({'passed':True,'samples':runs[1]},indent=2))
    print('PASS:',len(runs[1]),'full-resolution HD checksums, native pixels and named states identical with/without reuse')


if __name__=='__main__':main()
