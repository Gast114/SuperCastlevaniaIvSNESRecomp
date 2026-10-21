"""Targeted walking alias and single-frame inspection check (10x only)."""
import argparse,json,shutil,socket,subprocess,time
from pathlib import Path
import sciv_play as p
import sciv_test_support as s

def main():
 a=argparse.ArgumentParser(description=__doc__)
 for name in ('rom','character','pack','fixture'):a.add_argument('--'+name,type=Path,required=True)
 a.add_argument('--native-trace',type=Path)
 s.add_build_arg(a);a=a.parse_args();build=s.build_dir(a);work=s.work_dir(build,'walking-inspection-')
 exe=s.prepare(work,build,{'Graphics':{'Widescreen':1},'General':{'DisableFrameDelay':1}})
 shutil.copytree(a.character,work/'characters/probe');(work/'characters/selected.txt').write_text('probe')
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 old=json.loads(a.native_trace.read_text()) if a.native_trace else None
 frames={f['id'] for f in json.loads((a.character/'character.json').read_text())['frames']}
 lua=None;rows=[];aliases=set()
 with (work/'game.log').open('w') as log:
  proc=subprocess.Popen([str(exe),str(a.rom.resolve())],cwd=work,env=s.clean_env(SNESRECOMP_LUA_PORT=port,SNESRECOMP_LUA_PAUSED=1,SNESRECOMP_CHARACTER_TRACE=1),stdout=log,stderr=log,startupinfo=s.hidden_window())
  try:
   for _ in range(200):
    try:lua=p.LuaClient(port=port);lua.command('ping');break
    except OSError:assert proc.poll() is None;time.sleep(.05)
   assert lua
   def cmd(n,arg=''):return lua.eval(f'return game.command({json.dumps(n)},{json.dumps(str(arg))})')['values'][0]
   cmd('hd','pack '+str(a.pack.resolve()));cmd('hd','scale 10');cmd('hd','on')
   for face in ('Right','Left'):
    cmd('loadfile',a.fixture.resolve())
    for i in range(300):
     p.advance(lua,1,[face]);state=p.read_state(lua);char=json.loads(cmd('characterhd'))
     if old:assert state==old[len(rows)]['state'],(face,i,'gameplay changed')
     rows.append({'face':face,'i':i,'char':char,'state':state})
     # A load can precede the first valid OAM assembly. Check every subsequent field.
     if i>1:assert char['active'],(face,i,char)
     if char['active'] and char['pose'] not in frames:aliases.add(char['pose'])
   assert {'9e0c-e4c4686f3649c330','9bb9-1168be4736083938'}<=aliases,aliases
   baseline=p.read_state(lua);cmd('frameinspect','on');lua.command('resume');time.sleep(.1)
   frozen=p.read_state(lua);assert frozen['frame']==baseline['frame']
   for _ in range(12):
    before=p.read_state(lua);cmd('frameinspect','step');deadline=time.monotonic()+5
    while p.read_state(lua)['frame']==before['frame']:
     assert time.monotonic()<deadline,'single step never ran';time.sleep(.01)
    time.sleep(.04);after=p.read_state(lua);assert after['frame']==before['frame']+1,(before,after)
    assert json.loads(cmd('frameinspect'))['enabled']==1
   cmd('hdshot',work/'inspection.png')
   lua.command('pause');cmd('frameinspect','off');assert json.loads(cmd('frameinspect'))['enabled']==0
   # Lua pause still holds the guest; leaving inspection must not spend queued steps.
   held=p.read_state(lua);time.sleep(.05);assert p.read_state(lua)==held
   (work/'report.json').write_text(json.dumps({'passed':True,'walking_fields':600,'aliases':sorted(aliases),'native_trace_identical':bool(old),'single_steps':12,'work':str(work)},indent=2))
   (work/'frames.json').write_text(json.dumps(rows,indent=2))
  finally:
   if lua:lua.close()
   proc.terminate();proc.wait(timeout=10)
 print('PASS: 600 walking fields, both aliases replaced, native states unchanged; pause and 12 exact single steps; '+str(work))

if __name__=='__main__':main()
