"""Make local transparent walking PNGs and a six-frame review, without rescaling assets.

Uses the public ISNet-Anime ONNX foreground model. All frames retain one shared
crop and coordinate system. Does not install a game pack or change native timing.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--poses', type=Path, required=True)
    parser.add_argument('--native-pack', type=Path)
    parser.add_argument('--lock-upper-body', action='store_true',
                        help='Reuse phase 1 face and upper armor to prevent appearance flicker')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('Use a new package directory')
    sources = sorted(args.source.glob('Walking-[0-9][0-9].png'))
    if len(sources) != 6:
        raise ValueError('Expected exactly six rendered walking phases')
    import onnxruntime as ort
    settings = ort.SessionOptions()
    settings.intra_op_num_threads = os.cpu_count() or 1
    session = ort.InferenceSession(str(args.model), sess_options=settings,
                                   providers=['CPUExecutionProvider'])
    poses = json.loads(args.poses.read_text(encoding='utf-8'))
    native = {}
    if args.native_pack:
        data = json.loads((args.native_pack / 'character.json').read_text(encoding='utf-8-sig'))
        native = {row.get('label'): row['id'] for row in data['frames']}
    args.out.mkdir(parents=True)
    (args.out / 'rgba-full').mkdir()
    (args.out / 'frames').mkdir()
    images, boxes = [], []
    for path in sources:
        image = Image.open(path).convert('RGB')
        if list(image.size) != poses['canvas']:
            raise ValueError('All source frames must share the pose canvas')
        pixels = np.asarray(image.resize((1024, 1024), Image.Resampling.BILINEAR), dtype=np.float32)
        pixels /= max(float(pixels.max()), 1.)
        pixels -= np.array([.485, .456, .406], dtype=np.float32)
        tensor = pixels.transpose(2, 0, 1)[None].copy()
        prediction = session.run(None, {session.get_inputs()[0].name: tensor})[0][0, 0]
        prediction = (prediction - prediction.min()) / max(float(np.ptp(prediction)), 1e-8)
        mask = Image.fromarray(np.uint8(np.clip(prediction * 255, 0, 255))).resize(
            image.size, Image.Resampling.LANCZOS)
        alpha = np.asarray(mask, dtype=np.float32) / 255
        alpha[alpha < .012] = 0
        alpha[alpha > .985] = 1
        # Keep the character component near the hip anchor, plus soft edge
        # coverage; discard faint detached matte noise around the canvas.
        solid = Image.fromarray(np.uint8(alpha > .1) * 255).copy()
        ys, xs = np.nonzero(alpha > .1)
        if not len(xs):
            raise ValueError('Foreground model returned an empty character: ' + path.name)
        nearest = np.argmin((xs - poses['root'][0])**2 + (ys - poses['root'][1])**2)
        seed = (int(xs[nearest]), int(ys[nearest]))
        ImageDraw.floodfill(solid, seed, 128)
        connected = Image.fromarray(np.uint8(np.asarray(solid) == 128) * 255)
        connected = connected.filter(ImageFilter.MaxFilter(7))
        alpha[np.asarray(connected) == 0] = 0
        # Remove neutral matte color only at the soft silhouette edge. Core
        # armor colors stay untouched; pixels are never moved or rescaled.
        rgb = np.asarray(image, dtype=np.float32) / 255
        border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
        background = np.median(border, axis=0)
        edge = (alpha > .04) & (alpha < .985)
        recovered = (rgb - (1 - alpha[..., None]) * background) / np.maximum(alpha[..., None], .04)
        rgb[edge] = np.clip(recovered[edge], 0, 1)
        rgba = Image.fromarray(np.uint8(np.concatenate([rgb, alpha[..., None]], axis=2) * 255))
        box = rgba.getchannel('A').point(lambda value: 255 if value > 8 else 0).getbbox()
        if not box:
            raise ValueError('Foreground model returned an empty character: ' + path.name)
        rgba.save(args.out / 'rgba-full' / path.name)
        images.append(rgba)
        boxes.append(box)
        print('Transparent:', path.name, flush=True)
    if args.lock_upper_body:
        reference = images[0]
        first_nose_y = poses['poses'][0]['points'][0][1]
        boxes = []
        for i, image in enumerate(images):
            # Keep the small authored walking bob while reusing exactly the
            # same face, shoulder armor, torso and guarded arm position.
            dy = round(poses['poses'][i]['points'][0][1] - first_nose_y)
            shifted = Image.new('RGBA', image.size)
            shifted.alpha_composite(reference, (0, dy))
            split = 270 + dy
            weights = np.clip((split + 5 - np.arange(image.height)) / 10, 0, 1)
            weight = weights[:, None, None]
            upper = np.asarray(shifted, dtype=np.float32) / 255
            lower = np.asarray(image, dtype=np.float32) / 255
            opacity = upper[..., 3:] * weight + lower[..., 3:] * (1 - weight)
            premultiplied = (upper[..., :3] * upper[..., 3:] * weight
                             + lower[..., :3] * lower[..., 3:] * (1 - weight))
            color = np.divide(premultiplied, opacity, out=np.zeros_like(premultiplied), where=opacity > 1e-8)
            combined = np.concatenate([color, opacity], axis=2)
            # Do not fade a silhouette into a differently shaped silhouette:
            # that makes a translucent gray flap at the join. Pick one clean
            # contour there, and blend only the overlapping body interior.
            contour = np.abs(upper[..., 3] - lower[..., 3]) > .1
            selected = np.where(weight >= .5, upper, lower)
            combined[contour] = selected[contour]
            images[i] = Image.fromarray(np.uint8(np.rint(np.clip(combined, 0, 1) * 255)))
            images[i].save(args.out / 'rgba-full' / sources[i].name)
            boxes.append(images[i].getchannel('A').point(lambda value: 255 if value > 8 else 0).getbbox())
    crop = [math.floor((min(b[0] for b in boxes) - 10) / 10) * 10,
            math.floor((min(b[1] for b in boxes) - 10) / 10) * 10,
            math.ceil((max(b[2] for b in boxes) + 10) / 10) * 10,
            math.ceil((max(b[3] for b in boxes) + 10) / 10) * 10]
    frames, records = [], []
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    for path, image in zip(sources, images):
        frame = image.crop(crop)
        name = path.stem + '_HD_10x.png'
        target = args.out / 'frames' / name
        frame.save(target)
        frames.append(frame)
        records.append({'image': 'frames/' + name, 'source': str(path.resolve()),
                        'source_sha256': sha(path), 'sha256': sha(target),
                        'native_pose_reference': native.get(path.stem)})
    frames[0].save(args.out / 'Animation.webp', save_all=True, append_images=frames[1:],
                   duration=110, loop=0, lossless=True, background=(0, 0, 0, 0))
    sheet = Image.new('RGB', (1080, 1080), '#dadada')
    draw = ImageDraw.Draw(sheet)
    for i, frame in enumerate(frames):
        thumb = frame.copy()
        thumb.thumbnail((340, 500), Image.Resampling.LANCZOS)
        x = (i % 3) * 360 + (360 - thumb.width) // 2
        y = (i // 3) * 540 + 18
        sheet.paste(thumb, (x, y), thumb)
        draw.text(((i % 3) * 360 + 18, (i // 3) * 540 + 520), f'Walking-{i+1:02d}', fill='black')
    sheet.save(args.out / 'Alle_Gehposen.png')
    manifest = {'method': 'local SDXL LoRA + IP-Adapter + OpenPose + ISNet-Anime',
        'scale': 10, 'source_canvas': poses['canvas'], 'shared_crop': crop,
        'root_in_png': [poses['root'][0] - crop[0], poses['root'][1] - crop[1]],
        'ground_y_in_png': poses['ground_y'] - crop[1], 'frame_size': list(frames[0].size),
        'preview_frame_ms': 110, 'preview_timing_is_not_native_game_timing': True,
        'upper_body_reference': sources[0].name if args.lock_upper_body else None,
        'upper_body_split_y': 270 if args.lock_upper_body else None,
        'per_frame_rescaling': False, 'game_pack_installed': False,
        'native_offsets_still_need_review': True, 'matting_model_sha256': sha(args.model),
        'images': records}
    (args.out / 'placement.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    filenames = json.dumps([row['image'] for row in records])
    page = '''<!doctype html><meta charset="utf-8"><title>Simon – sechs Gehposen</title>
<style>body{font:18px system-ui;background:#24262b;color:#fff;text-align:center}img{max-height:75vh;background:#aaa}button,input{font:inherit;margin:8px;padding:8px}a{color:#adcfff}</style>
<h1>Simon – sechs Gehposen</h1><p>Lokale Vorschau. Das Tempo hier ändert das Spiel nicht.</p>
<img id="bild"><p><button id="prev">Zurück</button><button id="play">Abspielen</button><button id="next">Nächstes Bild</button></p>
<label>Tempo: <input id="fps" type="range" min="1" max="20" value="9"></label><p id="nummer"></p>
<p><a href="Alle_Gehposen.png">Alle sechs Bilder ansehen</a> · <a href="placement.json">Größe und Position</a></p>
<script>const frames=FILES;let index=0,timer=null;const img=document.querySelector('#bild');function show(){img.src=frames[index];document.querySelector('#nummer').textContent=`Bild ${index+1} von ${frames.length}`}
function stop(){clearInterval(timer);timer=null;document.querySelector('#play').textContent='Abspielen'}function start(){stop();timer=setInterval(()=>{index=(index+1)%frames.length;show()},1000/+document.querySelector('#fps').value);document.querySelector('#play').textContent='Anhalten'}
document.querySelector('#next').onclick=()=>{stop();index=(index+1)%frames.length;show()};document.querySelector('#prev').onclick=()=>{stop();index=(index+frames.length-1)%frames.length;show()};document.querySelector('#play').onclick=()=>timer?stop():start();document.querySelector('#fps').oninput=()=>{if(timer)start()};show();</script>'''.replace('FILES', filenames)
    (args.out / 'Vorschau.html').write_text(page, encoding='utf-8')
    with zipfile.ZipFile(args.out / 'Gehposen_10x.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        paths = [args.out / row['image'] for row in records]
        paths += [args.out / name for name in (
            'placement.json', 'Animation.webp', 'Alle_Gehposen.png', 'Vorschau.html')]
        for path in paths:
            archive.write(path, path.relative_to(args.out).as_posix())
    print(json.dumps({'frames': len(frames), 'size': list(frames[0].size), 'out': str(args.out.resolve())}), flush=True)


if __name__ == '__main__':
    main()
