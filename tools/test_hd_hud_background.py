"""HD scenery behind the HUD, retaining native text and simulation.

All captures are compared as arrays; no image viewer is opened.
"""
import argparse
import configparser
import json
from pathlib import Path
import tempfile
import numpy as np
from PIL import Image
from enemy_workshop_native import ROOT,NativeSession,play


def pixels(file):return np.array(Image.open(file).convert('RGB'))


def run(build,pack):
    folder=Path(tempfile.mkdtemp(prefix='hud-background-',dir=build))
    diagnostic=folder/'diagnostic';diagnostic.mkdir()
    yy,xx=np.indices((640,3840));rgba=np.empty((640,3840,4),np.uint8)
    rgba[...,0]=30+(xx%10)*20;rgba[...,1]=40+(yy%10)*19;rgba[...,2]=170;rgba[...,3]=255
    Image.fromarray(rgba).save(diagnostic/'background.png')
    (diagnostic/'pack.json').write_text(json.dumps(dict(version=1,scale=10,tile_size=80,atlas_size=2048,tiles={},scene_block=0,
        requires=['scene-regions-v1'],regions=[dict(layer=1,image='background.png',coordinates='world',x=-64,y=0,wrap_x=0,wrap_y=0,priority=0x7100)])))
    session=NativeSession(build=build,folder=folder/'game');report=dict(passed=False,image_viewer_used=False,checks=[])
    config=configparser.ConfigParser();config.read(session.folder/'config.ini');config['Graphics']['Widescreen']='1'
    with (session.folder/'config.ini').open('w') as f:config.write(f)
    try:
        s=session.start();s.command('enemy','workshop off');s.command('hd','scale 10')
        def capture(label,enabled=True,layers=31,fixture=None):
            s.command('hd','on' if enabled else 'off');s.command('layers',layers);s.command('loadfile',fixture or s.base);play.advance(s.lua,1)
            s.command('screenshot',folder/(label+'-native.png'))
            if enabled:s.command('hdshot',folder/(label+'-hd.png'))
            s.command('wram',folder/(label+'-ram.bin'))
            return pixels(folder/(label+'-native.png')),pixels(folder/(label+'-hd.png')) if enabled else None
        s.command('hd','pack '+str(diagnostic))
        original,_=capture('original',False);hud,_=capture('hud-only',False,4);backdrop,_=capture('backdrop',False,0)
        native,high=capture('diagnostic')
        assert np.array_equal(native,original)
        assert (folder/'original-ram.bin').read_bytes()==(folder/'diagnostic-ram.bin').read_bytes()
        nearest=original.repeat(10,0).repeat(10,1)
        mask=np.any(hud[:32]!=backdrop[:32],axis=2)&np.all(hud[:32]==original[:32],axis=2)
        assert int(mask.sum())>100
        high_mask=mask.repeat(10,0).repeat(10,1)
        assert np.array_equal(high[:320][high_mask],nearest[:320][high_mask]),'Native HUD glyphs changed'
        changed=np.any(high[:320]!=nearest[:320],axis=2)&~high_mask
        assert int(changed.sum())>10000,'Scenery behind HUD still bypasses HD'
        cells=high[:320].reshape(32,10,high.shape[1]//10,10,3)
        detail=np.any(cells!=cells[:,:1,:,:1,:],axis=(1,3,4))
        assert int(detail.sum())>100,'HUD background contains no real HD subpixel detail'
        report['checks'].append(dict(name='HD scenery behind native HUD; exact glyphs, native frame and full WRAM preserved',hud_pixels=int(mask.sum()),changed_hd_pixels=int(changed.sum()),detailed_cells=int(detail.sum())))
        # A disabled category or wrong scene must fall back cleanly, including
        # previously cached HUD rows.
        s.command('hd','layers 0');_,disabled=capture('disabled');assert np.array_equal(disabled,nearest)
        s.command('hd','layers 31');meta=json.loads((diagnostic/'pack.json').read_text());meta['scene_block']=1
        wrong=folder/'wrong-scene';wrong.mkdir();(wrong/'pack.json').write_text(json.dumps(meta));(wrong/'background.png').write_bytes((diagnostic/'background.png').read_bytes())
        s.command('hd','pack '+str(wrong));_,wrong_pixels=capture('wrong-scene');assert np.array_equal(wrong_pixels,nearest)
        report['checks'].append(dict(name='Category off and wrong-scene guards retain native HUD rows after cache reuse'))
        if pack:
            s.command('hd','pack '+str(pack));bridge=ROOT/'artwork-local/stage01-user-v2/fixtures/bridge/state.sav'
            # Actual entrance/bridge art retains the native HUD foreground.
            original,_=capture('installed-native',False,fixture=bridge);hud,_=capture('installed-hud',False,4,bridge);backdrop,_=capture('installed-backdrop',False,0,bridge)
            native,high=capture('installed',fixture=bridge);nearest=original.repeat(10,0).repeat(10,1)
            mask=np.any(hud[:32]!=backdrop[:32],axis=2)&np.all(hud[:32]==original[:32],axis=2)
            assert np.array_equal(high[:320][mask.repeat(10,0).repeat(10,1)],nearest[:320][mask.repeat(10,0).repeat(10,1)])
            assert np.array_equal(native,original)
            report['checks'].append(dict(name='Installed entrance pack keeps visible HUD glyphs and native scene intact',hud_pixels=int(mask.sum())))
            fixture=ROOT/'artwork-local/a02-layer-audit-2026-10-23/user-saves/F3.sav'
            original,_=capture('a02-native',False,fixture=fixture);hud,_=capture('a02-hud',False,4,fixture);backdrop,_=capture('a02-backdrop',False,0,fixture)
            native,high=capture('a02',fixture=fixture);nearest=original.repeat(10,0).repeat(10,1)
            mask=np.any(hud[:32]!=backdrop[:32],axis=2)&np.all(hud[:32]==original[:32],axis=2);mask=mask.repeat(10,0).repeat(10,1)
            assert np.array_equal(high[:320][mask],nearest[:320][mask]),'A02 HUD changed'
            changed=np.any(high[:320]!=nearest[:320],axis=2)&~mask
            assert int(changed.sum())>10000,'Installed A02 landscape behind HUD remained native'
            assert np.array_equal(native,original) and (folder/'a02-native-ram.bin').read_bytes()==(folder/'a02-ram.bin').read_bytes()
            report['checks'].append(dict(name='Installed A02 landscape renders behind exact HUD, native frame and full WRAM unchanged',changed_hd_pixels=int(changed.sum())))
        report['passed']=True
    except Exception as exc:report['error']=str(exc);raise
    finally:
        session.close();(folder/'report.json').write_text(json.dumps(report,indent=2));print(folder,flush=True)
    print(json.dumps(report,indent=2),flush=True);return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build',type=Path,default=ROOT/'build-lua');parser.add_argument('--pack',type=Path,default=ROOT/'build/hd_packs/stage-01-user-a02-v3');args=parser.parse_args();run(args.build.resolve(),args.pack.resolve())
