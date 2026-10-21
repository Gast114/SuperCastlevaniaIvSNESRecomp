"""Crop fixed-camera Blender renders without changing their size or origin.

Makes a local review page and placement manifest, never installs a game pack.
Requires Pillow. Input is the scene.json written by sprite_pilot.py.
"""
import argparse
import json
import math
from pathlib import Path

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    scene = json.loads(args.scene.read_text(encoding='utf-8'))
    scale = scene['scale']
    width, height = scene['canvas']
    if scale != 10 or width % scale or height % scale:
        raise ValueError('Expected a 10x studio canvas')
    if not scene['frames'] or not scene.get('rendered', False):
        raise ValueError('This studio has no rendered frames yet')
    if args.out.exists():
        raise FileExistsError('Use a new output folder: ' + str(args.out))
    # Read/validate everything before creating the output folder.
    frames = []
    for frame in scene['frames']:
        source = (args.scene.parent / frame['file']).resolve()
        if not source.is_relative_to(args.scene.parent.resolve()):
            raise ValueError('Frame outside scene folder')
        with Image.open(source) as opened:
            image = opened.convert('RGBA')
        if image.size != (width, height):
            raise ValueError('Unexpected canvas: ' + str(source))
        alpha = image.getchannel('A')
        box = alpha.getbbox()
        if not box:
            raise ValueError('Empty render: ' + str(source))
        if box[0] == 0 or box[1] == 0 or box[2] == width or box[3] == height:
            raise ValueError('Character touches canvas edge: check camera framing')
        # Preserve all alpha, including antialiasing. Round outward to native pixels.
        left, top = [(v // scale) * scale for v in box[:2]]
        right, bottom = [math.ceil(v / scale) * scale for v in box[2:]]
        crop = (left, top, right, bottom)
        frames.append((frame, image, crop, box))
    args.out.mkdir(parents=True)
    manifest = {
        'status': 'preview_requires_native_pose_mapping',
        'source_scene': str(args.scene.resolve()),
        'scale': scale, 'canvas': [width, height],
        'native_origin': scene['native_origin'],
        'ground_native': scene['ground_native'],
        'frames': [],
    }
    figures = []
    common = (min(f[2][0] for f in frames), min(f[2][1] for f in frames),
              max(f[2][2] for f in frames), max(f[2][3] for f in frames))
    full = args.out / 'full'
    full.mkdir()
    stage = args.out / 'stage'
    stage.mkdir()
    for i, (frame, image, crop, box) in enumerate(frames, 1):
        name = f'Pilot-{i:02d}.png'
        image.crop(crop).save(args.out / name)
        image.save(full / name)
        image.crop(common).save(stage / name)
        manifest['frames'].append({
            'image': name, 'scale': scale,
            'offset': [crop[0] // scale, crop[1] // scale],
            'display_size': [(crop[2] - crop[0]) // scale, (crop[3] - crop[1]) // scale],
            'opaque_bounds_on_canvas': list(box),
            'source_frame': frame['source_frame'],
        })
        figures.append(f'<figure><img src="stage/{name}"><figcaption>Bild {i} · '
                       f'Quellbild {frame["source_frame"]:.2f}</figcaption></figure>')
    (args.out / 'placement.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    animation = [f[1].crop(common) for f in frames]
    duration = 160
    if len(frames) > 1:
        delta = frames[1][0]['source_frame'] - frames[0][0]['source_frame']
        duration = max(40, round(1000 * delta / scene.get('source_fps', 60)))
    animation[0].save(args.out / 'Animation.webp', save_all=True,
                      append_images=animation[1:], lossless=True, duration=duration, loop=0)
    names = json.dumps([f'stage/Pilot-{i:02d}.png' for i in range(1, len(frames) + 1)])
    page = '''<!doctype html><html lang="de"><meta charset="utf-8">
<title>Simon – Blender-Pilot</title><style>
body{background:#171421;color:#eee;font:17px system-ui;max-width:1100px;margin:32px auto;padding:0 24px}
button,input{font:inherit;margin:6px;padding:8px}img{width:320px;height:320px;object-fit:contain}
.stage{display:block;width:auto;height:auto;max-width:100%;background:repeating-conic-gradient(#272530 0% 25%,#34303e 0% 50%) 50%/24px 24px;border-radius:8px}
.grid{display:flex;flex-wrap:wrap}figure{margin:8px}figcaption{font-size:14px;color:#cbc3d4}
</style><h1>Simon – Blender-Pilot</h1>
<p>Dies ist eine Vorschau. Die Figur ist noch nicht ins Spiel eingebaut.
Kamera, Größe und Bezugspunkt bleiben bei allen Bildern gleich.</p>
<img class="stage" id="current" alt="Animationsvorschau">
<p><button id="play">Abspielen</button><button id="next">Nächstes Bild</button>
<label>Millisekunden je Bild <input id="speed" type="number" min="40" max="2000" value="160"></label>
<span id="counter"></span></p><p>Die Geschwindigkeit hier dient nur zum Ansehen.
Im Spiel bestimmt die Originalanimation das Tempo.</p><div class="grid">FIGURES</div>
<script>const frames=FRAMES;let index=0,timer=null;
const img=document.querySelector('#current'),play=document.querySelector('#play');
function show(){img.src=frames[index];document.querySelector('#counter').textContent=(index+1)+' / '+frames.length}
function stop(){clearInterval(timer);timer=null;play.textContent='Abspielen'}
document.querySelector('#next').onclick=()=>{stop();index=(index+1)%frames.length;show()};
play.onclick=()=>{if(timer){stop();return}play.textContent='Anhalten';timer=setInterval(()=>{index=(index+1)%frames.length;show()},Math.max(40,Number(document.querySelector('#speed').value)||160))};
document.querySelector('#speed').onchange=stop;show();</script></html>'''
    page = page.replace('FIGURES', ''.join(figures)).replace('FRAMES', names)
    page = page.replace('value="160"', f'value="{duration}"')
    (args.out / 'Vorschau.html').write_text(page, encoding='utf-8')
    print(args.out.resolve() / 'Vorschau.html')


if __name__ == '__main__':
    main()
