"""Private native/WRAM replay, water clock and scene guards for A03/A04/A05."""
import argparse
import configparser
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time

import numpy as np
from PIL import Image
from enemy_workshop_native import ROOT, NativeSession, play


def pixels(path):
    return np.array(Image.open(path).convert('RGB'))


def test(pack, reference=None):
    out=Path(tempfile.mkdtemp(prefix='hd-later-stage01-',dir=ROOT/'build-lua'))
    print(out,flush=True)
    saves=out/'fixtures';saves.mkdir()
    for stage,slot in [('A03',2),('A04',3),('A05',4)]:
        shutil.copy2(ROOT/f'build-play/game/saves/save{slot}.sav',saves/(stage+'.sav'))
    s=NativeSession(folder=out/'game')
    config=configparser.ConfigParser();config.read(s.folder/'config.ini')
    config['Graphics']['Widescreen']='1'
    with (s.folder/'config.ini').open('w') as f:config.write(f)
    report={'pack':str(pack),'cases':[]}
    try:
        s.start(saves/'A03.sav');s.command('enemy','workshop off')
        loaded=s.command('hd','pack '+str(pack));print('load',loaded,flush=True)
        s.command('hd','scale 4')
        for stage in ('A03','A04','A05'):
            for name,frames,buttons in [('idle',1,()),('walk',90,('Right',)),('attack',35,('Y',))]:
                runs=[]
                for enabled in (False,True):
                    s.command('hd','on' if enabled else 'off');s.command('loadfile',saves/(stage+'.sav'))
                    start=time.perf_counter();play.advance(s.lua,frames,buttons);elapsed=time.perf_counter()-start
                    state=play.read_state(s.lua);state.pop('frame');state.pop('paused')
                    stem=f'{stage}-{name}-{int(enabled)}'
                    native=out/(stem+'-native.png');ram=out/(stem+'-wram.bin')
                    s.command('screenshot',native);s.command('wram',ram)
                    runs.append((state,hashlib.sha256(pixels(native).tobytes()).hexdigest(),hashlib.sha256(ram.read_bytes()).hexdigest()))
                    if enabled:
                        hd=out/(stem+'-hd.png');s.command('hdshot',hd)
                        status=json.loads(s.command('hd'))
                        assert status['matched']>1000,(stage,name,status)
                        painted=pixels(hd);original=pixels(native).repeat(4,0).repeat(4,1)
                        if reference:
                            assert np.array_equal(painted,pixels(reference/hd.name)),(stage,name,'optimized HD pixels differ')
                        changed=int(np.count_nonzero(np.any(painted!=original,axis=2)))
                        assert changed>30000,(stage,name,'no substantial HD coverage')
                        report['cases'].append(dict(stage=stage,case=name,matched=status['matched'],hd_changed_pixels=changed,unthrottled_ms_per_frame=elapsed*1000/frames))
                assert runs[0]==runs[1],(stage,name,'native state/raster/WRAM changed')
                print(report['cases'][-1],flush=True)
        # Reload determinism and native palette animation, including rewind-like loads.
        water=[]
        for frames in (1,5,33,1):
            s.command('loadfile',saves/'A04.sav');play.advance(s.lua,frames)
            path=out/f'A04-water-{frames}-{len(water)}.png';s.command('hdshot',path)
            water.append(pixels(path))
        assert np.array_equal(water[0],water[3]),'Reload did not restore exact HD picture'
        assert not np.array_equal(water[0][136*4:157*4],water[1][136*4:157*4]),'Water did not animate'
        assert not np.array_equal(water[1][136*4:157*4],water[2][136*4:157*4]),'Third water state missing'
        report.update(native_raster_state_and_wram_identical=True,water_animated=True,reload_hd_identical=True)
        # A02 remains byte-preserved in the collection and must still select correctly.
        fixture=ROOT/'artwork-local/a02-layer-audit-2026-10-23/user-saves/F3.sav'
        s.command('loadfile',fixture);play.advance(s.lua,1)
        assert json.loads(s.command('hd'))['matched']>1000,'A02 disappeared'
        report['A02_still_selected']=True
        deaths=[]
        for stage in ('A03','A04','A05'):
            runs=[]
            for enabled in (False,True):
                s.command('hd','on' if enabled else 'off');s.command('loadfile',saves/(stage+'.sav'))
                play.advance(s.lua,1);s.write({0x54e:260})
                states=[];fades=[]
                for _ in range(200):
                    play.advance(s.lua,1)
                    state=play.read_state(s.lua);state.pop('frame');state.pop('paused');states.append(state)
                    if enabled and state['level_phase']==6:fades.append(json.loads(s.command('hd'))['matched'])
                runs.append(states)
                if enabled:
                    assert fades and max(fades)>1000,(stage,'outgoing HD lost during fade')
                    assert states[-1]['level_phase']==5,(stage,'restart failed')
            assert runs[0]==runs[1],(stage,'death/restart native logic changed')
            deaths.append(dict(stage=stage,fade_frames=len(fades),restarted=True))
        report['deaths']=deaths
        report['optimized_pixels_identical_to_reference']=bool(reference)
    finally:s.close()
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pack',type=Path,required=True)
    p.add_argument('--reference',type=Path)
    args=p.parse_args();test(args.pack.resolve(),args.reference.resolve() if args.reference else None)
