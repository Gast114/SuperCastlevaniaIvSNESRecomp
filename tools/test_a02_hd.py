"""Verify the delivered A02 art against F2/F3 and the existing entrance.

Runs copied executables in an isolated folder. Player saves/config/art stay put.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time

import numpy as np
from PIL import Image, ImageDraw

import sciv_play as play
import sciv_test_support as sciv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sciv.add_build_arg(parser)
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--f2', type=Path, required=True)
    parser.add_argument('--f3', type=Path, required=True)
    parser.add_argument('--rom', type=Path, default=sciv.ROOT / 'Super Castlevania IV (USA).sfc')
    parser.add_argument('--supplemental', action='store_true', help='Depth-placement and real room-transition probes only')
    parser.add_argument('--registration', action='store_true', help='Check the visible terminal gargoyle against actual runtime coordinates')
    args = parser.parse_args()
    work = sciv.work_dir(sciv.build_dir(args), 'a02-hd-check-')
    exe = sciv.prepare(work / 'game', sciv.build_dir(args), {'General': {'DisableFrameDelay': 1}, 'Graphics': {'Widescreen': 1}})
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    lua = None
    report = {'passed': False, 'runs': {}, 'checks': []}
    with (work / 'game/game.log').open('w') as log:
        proc = subprocess.Popen([str(exe), str(args.rom.resolve())], cwd=work / 'game',
            env=sciv.clean_env(SNESRECOMP_LUA_PORT=port, SNESRECOMP_LUA_PAUSED=1),
            stdout=log, stderr=log, startupinfo=sciv.hidden_window())
        try:
            for _ in range(200):
                try:
                    lua = play.LuaClient(port=port)
                    lua.command('ping')
                    break
                except OSError:
                    if proc.poll() is not None:
                        raise RuntimeError('Game exited; see log')
                    time.sleep(.05)
            if lua is None:
                raise RuntimeError('No Lua connection')

            def command(name, arg=''):
                result = lua.eval(f'return game.command({json.dumps(name)},{json.dumps(str(arg))})')
                if result.get('error'):
                    raise RuntimeError(result)
                return result['values'][0]

            command('hd', 'pack ' + str(args.pack.resolve()))
            command('hd', 'scale 10')
            if args.registration:
                command('hd', 'on')
                command('loadfile', args.f3.resolve())
                play.advance(lua, 1)
                play.advance(lua, 1, ('B',))
                lua.eval('mainmemory.write_u16_le(0x54A,1980);mainmemory.write_u16_le(0x54E,50)')
                play.advance(lua, 500)
                state = play.read_state(lua)
                assert state['camera_x'] == 1792, ('Camera did not reach the end', state)
                ppu = json.loads(command('ppu'))
                command('hdshot', work / 'exit-hd.png')
                command('screenshot', work / 'exit-native.png')
                command('dump', work / 'exit-video.bin')
                native_hash = hashlib.sha256((work / 'exit-native.png').read_bytes()).hexdigest()
                # Check actual visible art, not just a successful pack load.
                actual = np.array(Image.open(work / 'exit-hd.png').convert('RGB'))
                manifest = json.loads((args.pack / 'a02/pack.json').read_text())
                density = manifest['scale']; output_scale = 10
                camera = state['camera_x']; hs = ppu['layers'][1]['h']
                bg_origin = camera + (hs-camera+512)%1024-512
                scores = []
                for region in manifest['regions']:
                    if region.get('a02_kind') != 3: continue
                    image = np.array(Image.open(args.pack / 'a02' / region['image']).convert('RGBA'))
                    yy = np.arange(image.shape[0]//density*output_scale)*density//output_scale
                    xx = np.arange(image.shape[1]//density*output_scale)*density//output_scale
                    expected = image[yy[:,None], xx[None,:]]
                    left = (region['x']-bg_origin+ppu['extra'])*output_scale
                    top = region['y']*output_scale
                    seen = actual[top:top+expected.shape[0],left:left+expected.shape[1]]
                    assert seen.shape[:2] == expected.shape[:2], 'Statue outside visible frame'
                    mask = expected[:,:,3] == 255
                    hits = int((np.all(seen == expected[:,:,:3],axis=2)&mask).sum())
                    scores.append({'phase':region['phase'],'visible_exact_pixels':hits,
                                   'opaque_pixels':int(mask.sum()),'fraction':hits/max(1,int(mask.sum()))})
                assert max(s['fraction'] for s in scores) > .2, scores
                report['registration'] = {'state':state,'ppu':ppu,'background_origin':bg_origin,'statue_scores':scores,
                                          'synthetic_relocation':True,'native_screenshot_sha256':native_hash}
                report['checks'].append('Terminal gargoyle visibly matches supplied artwork at runtime BG2 coordinates')
                report['passed'] = True
                print('PASS:', '; '.join(report['checks']))
                return
            if args.supplemental:
                command('hd', 'on')
                depth = {}
                priorities = {}
                for side in ('front', 'back'):
                    command('loadfile', args.f3.resolve())
                    play.advance(lua, 80 if side == 'back' else 1, ('Up',) if side == 'back' else ())
                    # Synthetic relocation, then normal native scrolling/fall.
                    play.advance(lua, 1, ('B',))
                    lua.eval('mainmemory.write_u16_le(0x54A,1200);mainmemory.write_u16_le(0x54E,50)')
                    play.advance(lua, 220)
                    # Collision columns stream with the camera. Drop again
                    # after it has reached the destination, not off-screen.
                    play.advance(lua, 1, ('B',))
                    lua.eval('mainmemory.write_u16_le(0x54E,50)')
                    play.advance(lua, 80)
                    depth[side] = play.read_state(lua)
                    priorities[side] = int(lua.eval('return mainmemory.read_u16_le(0x542)')['values'][0])
                    command('hdshot', work / f'platform-{side}-hd.png')
                # Warping does not enter the native stair traversal state, so
                # these are layout views, not proof of a naturally climbed route.
                assert priorities['front'] != priorities['back'], priorities
                assert depth['back']['player_y'] < depth['front']['player_y'], depth
                report['depth_probe'] = {'synthetic_relocation': True, 'natural_stair_route_verified': False,
                                         'states': depth, 'priorities': priorities}
                report['checks'].append('Mid-level layout views retain native front/back depth and ground heights')
                play.advance(lua, 1, ('B',))
                lua.eval('mainmemory.write_u16_le(0x54A,1980);mainmemory.write_u16_le(0x54E,50)')
                play.advance(lua, 300)
                command('hdshot', work / 'exit-hd.png')
                command('dump', work / 'exit-video.bin')
                report['exit_probe'] = play.read_state(lua)
                bridge = sciv.ROOT / 'artwork-local/stage01-user-v2/fixtures/bridge/state.sav'
                command('loadfile', bridge)
                transition = []
                for _ in range(30):
                    play.advance(lua, 8, ('Right',))
                    s = play.read_state(lua)
                    h = json.loads(command('hd'))
                    transition.append({'state': s, 'hd': h})
                assert any(t['state']['block']==1 and t['state']['level_phase']==6 and t['hd']['art_scale']==10 for t in transition), 'Outgoing entrance lost art'
                assert any(t['state']['block']==1 and t['state']['level_phase']==5 and t['hd']['art_scale']==4 and t['hd']['matched']>1000 for t in transition), 'A02 did not switch automatically'
                report['transition_probe'] = transition
                report['checks'].append('Real entrance->A02 transition selects both source densities, retains 10x output')
                report['passed'] = True
                print('PASS:', '; '.join(report['checks']))
                return
            for label, fixture, checkpoints, buttons in [
                ('F2', args.f2, [0,16,32,48,64,80,104,128,160], ()),
                ('F3', args.f3, [0,8,16,24,32,40,56,80,120], ('Up',))]:
                runs = []
                for enabled in (False, True):
                    command('hd', 'on' if enabled else 'off')
                    command('loadfile', fixture.resolve())
                    play.advance(lua, 1)
                    samples = []
                    previous = 0
                    for frame in checkpoints:
                        if frame > previous:
                            play.advance(lua, frame-previous, buttons)
                        previous = frame
                        state = play.read_state(lua)
                        state.pop('frame'); state.pop('paused')
                        command('screenshot', work / 'native.png')
                        native = np.array(Image.open(work / 'native.png'))
                        pixels = hashlib.sha256(native.tobytes()).hexdigest()
                        priority = int(lua.eval('return mainmemory.read_u16_le(0x542)')['values'][0])
                        samples.append({'frame': frame, 'state': state, 'priority': priority, 'native_sha256': pixels})
                        if enabled:
                            path = work / f'{label}-{frame:03d}-hd.png'
                            command('hdshot', path)
                            actual = np.array(Image.open(path))
                            assert np.array_equal(actual[:320], native.repeat(10,0).repeat(10,1)[:320]), 'HUD changed'
                            if frame >= 32:
                                assert int(json.loads(command('hd'))['matched']) > 1000, 'A02 art absent'
                    runs.append(samples)
                assert runs[0] == runs[1], f'{label}: HD changed guest state or original pixels'
                report['runs'][label] = runs[1]
                report['checks'].append(label + ': native field/state identity, 10x art, original HUD')
            assert len({s['priority'] for s in report['runs']['F3']}) == 2, 'Gate did not change side'
            report['checks'].append('F3 native gate switches player depth')

            bridge = sciv.ROOT / 'artwork-local/stage01-user-v2/fixtures/bridge/state.sav'
            hashes = []
            for pack in (args.pack / 'entrance', args.pack):
                command('hd', 'pack ' + str(pack.resolve()))
                command('loadfile', bridge)
                play.advance(lua, 1)
                hashes.append(command('hdhash'))
            assert hashes[0] == hashes[1], 'Collection changed existing entrance'
            report['checks'].append('Existing entrance HD checksum unchanged')

            sheets = []
            for label, picks in [('F2',[16,48,80,128]),('F3',[0,16,24,80])]:
                sheet = Image.new('RGB', (1368, 936), (24,24,28))
                draw = ImageDraw.Draw(sheet)
                for k, frame in enumerate(picks):
                    image = Image.open(work / f'{label}-{frame:03d}-hd.png')
                    image = image.resize((684,448), Image.Resampling.LANCZOS)
                    x, y = k%2*684, k//2*468
                    sheet.paste(image,(x,y+20))
                    draw.text((x+5,y+3), f'{label} +{frame} frames', fill='white')
                sheet.save(work / f'{label}-review.png')
            report['passed'] = True
            print('PASS:', '; '.join(report['checks']))
        finally:
            (work / 'report.json').write_text(json.dumps(report, indent=2))
            if lua:
                lua.close()
            proc.terminate(); proc.wait(timeout=10)


if __name__ == '__main__':
    main()
