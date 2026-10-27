"""A02 authored grass footing and visible eyes, without opening images."""
import argparse,configparser,json,tempfile,os
from pathlib import Path
import numpy as np
from PIL import Image
from enemy_workshop_native import ROOT,NativeSession,play

def run(pack,before_build):
 folder=Path(tempfile.mkdtemp(prefix='a02-footing-',dir=ROOT/'build-lua'));print(folder,flush=True)
 fixtures=ROOT/'artwork-local/a02-layer-audit-2026-10-23/user-saves'
 reports=[];runs=[]
 for label,build,art in [('before',before_build,ROOT/'build/hd_packs/stage-01-user-a02-v3'),('after',ROOT/'build-lua',pack)]:
  s=NativeSession(build=build,folder=folder/label)
  cfg=configparser.ConfigParser();cfg.read(s.folder/'config.ini');cfg['Graphics']['Widescreen']='1'
  with (s.folder/'config.ini').open('w') as f:cfg.write(f)
  captures={}
  try:
   s.start(fixtures/'F3.sav');s.command('enemy','workshop off');s.command('hd','pack '+str(art));s.command('hd','scale 4');s.command('hd','on')
   def capture(name):
    paths={}
    for cmd,ext in [('hdshot','hd.png'),('screenshot','native.png'),('wram','ram.bin')]:
     path=folder/(label+'-'+name+'-'+ext);s.command(cmd,path);paths[ext]=path
    captures[name]={k:np.array(Image.open(v).convert('RGB')) if k.endswith('png') else v.read_bytes() for k,v in paths.items()}
   for fixture,buttons in [('F2',()),('F3',('Up',))]:
    s.command('loadfile',fixtures/(fixture+'.sav'));play.advance(s.lua,1)
    for i in range(5):
     if i:play.advance(s.lua,40,buttons)
     capture(fixture+'-'+str(i*40))
   s.command('loadfile',fixtures/'F3.sav');play.advance(s.lua,1,('B',));s.write({0x54a:1980,0x54e:50});play.advance(s.lua,500)
   capture('end');state=play.read_state(s.lua);assert state['camera_x']==1792
   ppu=json.loads(s.command('ppu'))
   # Present each supplied eye image through the real compositor. Select all
   # native phases for this diagnostic only; the installed probe stays fixed.
   meta=json.loads((art/'a02/pack.json').read_text());statues=[r for r in meta['regions'] if r.get('a02_kind')==3]
   for phase in (1,2):
    variant=folder/(label+'-eye-'+str(phase));variant.mkdir()
    chosen=next(r for r in statues if r['phase']==phase)
    for image in (art/'a02').glob('*.png'):os.link(image,variant/image.name)
    diagnostic=dict(meta);diagnostic['regions']=[r for r in meta['regions'] if r.get('a02_kind')!=3]
    diagnostic['regions'] += [dict(chosen,phase=p) for p in (0,1,2)]
    (variant/'pack.json').write_text(json.dumps(diagnostic));result=s.command('hd','pack '+str(variant));assert 'Pack not loaded' not in result,result
    play.advance(s.lua,1);capture('eye'+str(phase))
    image=np.array(Image.open(art/'a02'/chosen['image']).convert('RGBA'));rgb=image[:,:,:3].astype(int)
    # Eye patch common to both variants, measured from the supplied red eyes.
    red=next(r for r in statues if r['phase']==1);ra=np.array(Image.open(art/'a02'/red['image']).convert('RGBA'));rr=ra[:,:,:3].astype(int)
    yy,xx=np.nonzero((rr[:,:,0]>rr[:,:,1]*1.6)&(rr[:,:,0]>rr[:,:,2]*1.6)&(rr[:,:,0]>110)&(ra[:,:,3]>240))
    origin=state['camera_x']+(ppu['layers'][1]['h']-state['camera_x']+512)%1024-512
    screen=captures['eye'+str(phase)]['hd.png'];sx=(chosen['x']-origin+ppu['extra'])*4+xx;sy=chosen['y']*4+yy
    error=np.max(np.abs(screen[sy,sx].astype(int)-rgb[yy,xx]),axis=1)
    visible=int((error<20).sum());reports.append(dict(run=label,phase=phase,visible=visible,total=len(xx)))
    if label=='after':assert visible>=15,reports[-1]
  finally:s.close()
  runs.append(captures)
 for name in runs[0]:
  assert np.array_equal(runs[0][name]['native.png'],runs[1][name]['native.png']),name
  assert runs[0][name]['ram.bin']==runs[1][name]['ram.bin'],name
 changes=[]
 for name in ('F2-160','F3-0','end'):
  a=runs[0][name]['hd.png'];b=runs[1][name]['hd.png']
  changed=int(np.any(a[193*4:213*4]!=b[193*4:213*4],axis=2).sum());changes.append(dict(name=name,footing_pixels=changed));assert changed>100,changes[-1]
 report=dict(passed=True,eyes=reports,footing=changes,native_and_full_wram_identical=True,image_viewer_used=False)
 (folder/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pack',type=Path,required=True)
 p.add_argument('--before-build',type=Path,required=True,help='Archived pre-fix Lua executable folder')
 a=p.parse_args();run(a.pack.resolve(),a.before_build.resolve())
