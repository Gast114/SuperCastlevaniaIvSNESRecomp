"""Death/reload must not select another room that shares native map addresses."""
import argparse,hashlib,json,tempfile
from pathlib import Path
from enemy_workshop_native import ROOT,NativeSession,play

def run(f4):
 folder=Path(tempfile.mkdtemp(prefix='hd-death-room-',dir=ROOT/'build-lua'));print(folder,flush=True)
 s=NativeSession(folder=folder/'game');report=[]
 try:
  s.start(f4);s.command('enemy','workshop off');s.command('hd','pack '+str(ROOT/'build/hd_packs/stage-01-user-a02-v4-placement'));s.command('hd','scale 4')
  for name,fixture,death in [('A03',f4,True),('A02',ROOT/'artwork-local/a02-layer-audit-2026-10-23/user-saves/F3.sav',True),('bridge',ROOT/'artwork-local/stage01-user-v2/fixtures/bridge/state.sav',False)]:
   runs=[]
   for enabled in (False,True):
    s.command('hd','on' if enabled else 'off');s.command('loadfile',fixture);play.advance(s.lua,1)
    if death:s.write({0x54e:260})
    samples=[];fades=[];captures=[];seen=set()
    for i in range(200):
     play.advance(s.lua,1,() if death else ('Right',))
     state=play.read_state(s.lua);state.pop('frame');state.pop('paused')
     samples.append(state);phase=state['level_phase'];hd=json.loads(s.command('hd'))
     if enabled and phase==6:fades.append(hd['matched'])
     if enabled and name=='A03':assert hd['matched']==0,(name,i,state,hd)
     if phase in (6,3,4,5) and phase not in seen:
      seen.add(phase);files=[]
      for cmd,ext in [('screenshot','png'),('wram','bin')]:
       path=folder/(name+'-'+str(int(enabled))+'-'+str(phase)+'.'+ext);s.command(cmd,path);files.append(hashlib.sha256(path.read_bytes()).hexdigest())
      captures.append((phase,files))
    runs.append((samples,captures))
    if enabled:
     assert fades,(name,'fade not reached')
     if name!='A03':assert max(fades)>1000,(name,'outgoing HD lost')
     if death:assert samples[-1]['level_phase']==5,(name,'restart did not finish')
     report.append(dict(name=name,fade_frames=len(fades),max_fade_matches=max(fades),restarted=death))
   assert runs[0]==runs[1],name+' native simulation/captures changed'
 finally:s.close()
 (folder/'report.json').write_text(json.dumps(dict(passed=True,cases=report,native_and_wram_identical=True,image_viewer_used=False),indent=2));print(report,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--f4',type=Path,required=True);a=p.parse_args();run(a.f4.resolve())
