"""Replay the reported bridge marker and reject a wrapped HD background."""
import argparse,hashlib,json,socket,subprocess,time
from pathlib import Path
import numpy as np
from PIL import Image
import sciv_play as play,sciv_test_support as sciv

p=argparse.ArgumentParser(description=__doc__)
sciv.add_build_arg(p)
p.add_argument('--rom',type=Path,required=True);p.add_argument('--pack',type=Path,required=True)
p.add_argument('--fixture',type=Path,required=True);args=p.parse_args()
build=sciv.build_dir(args);work=sciv.work_dir(build,'bridge-repeat-check-')
exe=sciv.prepare(work/'game',build,{'General':{'DisableFrameDelay':1},'Graphics':{'Widescreen':1}})
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
lua=None;report={'passed':False}
with (work/'game/game.log').open('w') as log:
 proc=subprocess.Popen([str(exe),str(args.rom.resolve())],cwd=work/'game',env=sciv.clean_env(SNESRECOMP_LUA_PORT=port,SNESRECOMP_LUA_PAUSED=1),stdout=log,stderr=log,startupinfo=sciv.hidden_window())
 try:
  for _ in range(200):
   try:lua=play.LuaClient(port=port);lua.command('ping');break
   except OSError:time.sleep(.05)
  def cmd(n,a=''):return lua.eval(f'return game.command({json.dumps(n)},{json.dumps(str(a))})')['values'][0]
  cmd('hd','pack '+str(args.pack.resolve()));cmd('hd','scale 10');cmd('hd','layers 31')
  native=[];states=[]
  for on in [False,True]:
   cmd('hd','on' if on else 'off');cmd('loadfile',args.fixture.resolve());play.advance(lua,1)
   path=work/('native-on.png' if on else 'native-off.png');cmd('screenshot',path)
   native.append(np.array(Image.open(path).convert('RGB')))
   state=play.read_state(lua);state.pop('frame');state.pop('paused');states.append(state)
  cmd('hdshot',work/'fixed-hd.png');hd=np.array(Image.open(work/'fixed-hd.png').convert('RGB'))
  assert states[0]==states[1] and np.array_equal(native[0],native[1]),'Native simulation changed'
  base=native[1].repeat(10,0).repeat(10,1)
  assert np.array_equal(hd[:320],base[:320]),'HUD changed'
  # The marker exposes open sky here in the original. A wrapped replacement
  # used to put a tall copy of the starting rock wall across this rectangle.
  area=(slice(400,700),slice(3230,3410))
  assert np.array_equal(hd[area],base[area]),'Background start repeated at right edge'
  report.update(passed=True,state=states[1],native_sha256=hashlib.sha256(native[1].tobytes()).hexdigest(),checks=['reported right-edge sky preserved','native field and state unchanged','HUD unchanged'])
  print('PASS: bridge marker has open right-edge sky; native field/state/HUD unchanged')
 finally:
  (work/'report.json').write_text(json.dumps(report,indent=2))
  if lua:lua.close()
  proc.terminate();proc.wait(timeout=10)
