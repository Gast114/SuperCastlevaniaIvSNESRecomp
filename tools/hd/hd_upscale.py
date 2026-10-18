"""Upscale the collected layer pictures (hd_dump/captures) into hd_work/up.

  python tools/hd/hd_upscale.py [--dump build/hd_dump] [--work build/hd_work]
        [--method realesrgan|nearest|command] [--model realesrgan-x4plus-anime]
        [--scale 4] [--command "mytool -i {input} -o {output} -s {scale}"] [--force]

Colour and transparency are upscaled separately: transparent pixels are first
filled from their opaque neighbours (so no dark fringe bleeds into edges), and
the transparency mask goes through the same upscaler as a grey picture, then
is sharpened back towards hard edges. Pictures already upscaled with the same
settings are skipped, so collecting more and running again only does the new
ones.

Methods: realesrgan = Real-ESRGAN ncnn-vulkan from ../tools-external/realesrgan
(GPU, AMD/NVIDIA/Intel); nearest = plain pixel enlargement, for testing the
pipeline; command = any tool that takes a folder in and writes a folder out.
"""
import argparse
import hashlib
import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hd_common as hd  # noqa: E402


def fill_transparent(rgba):
    """RGB with transparent pixels replaced by the mean of nearby opaque ones."""
    rgb = rgba[..., :3].astype(np.float32)
    known = rgba[..., 3] > 0
    if known.all() or not known.any():
        return rgba[..., :3].copy()
    acc, cnt = rgb * known[..., None], known.astype(np.float32)
    for _ in range(12):
        if known.all():
            break
        s = np.zeros_like(acc)
        c = np.zeros_like(cnt)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            # Do not wrap the right edge into the left edge (or top/bottom).
            shifted = np.roll(acc, (dy, dx), (0, 1))
            counts = np.roll(cnt, (dy, dx), (0, 1))
            if dy:
                shifted[0 if dy > 0 else -1, :] = 0
                counts[0 if dy > 0 else -1, :] = 0
            if dx:
                shifted[:, 0 if dx > 0 else -1] = 0
                counts[:, 0 if dx > 0 else -1] = 0
            s += shifted
            c += counts
        grow = ~known & (c > 0)
        acc[grow] = s[grow] / c[grow, None]
        cnt[grow] = 1
        known = known | grow
    if not known.all():
        acc[~known] = rgb[rgba[..., 3] > 0].mean(axis=0)
    return np.clip(acc, 0, 255).astype(np.uint8)


def run_upscaler(args, src, dst):
    dst.mkdir(parents=True, exist_ok=True)
    if args.method == 'nearest':
        for f in src.glob('*.png'):
            im = Image.open(f)
            im.resize((im.width * args.scale, im.height * args.scale), Image.NEAREST).save(dst / f.name)
        return
    if args.method == 'realesrgan':
        exe = hd.find_realesrgan()
        if not exe:
            raise SystemExit('Real-ESRGAN not found in ../tools-external/realesrgan')
        cmd = [str(exe), '-i', str(src), '-o', str(dst), '-n', args.model, '-s', str(args.scale), '-f', 'png']
    else:
        cmd = shlex.split(args.command, posix=True)
        cmd = [arg.format(input=src, output=dst, scale=args.scale) for arg in cmd]
    print('running', ' '.join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=str(exe.parent) if args.method == 'realesrgan' else None)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--dump', type=Path, default=hd.ROOT / 'build' / 'hd_dump')
    p.add_argument('--work', type=Path, default=hd.ROOT / 'build' / 'hd_work')
    p.add_argument('--method', choices=('realesrgan', 'nearest', 'command'), default='realesrgan')
    p.add_argument('--model', default='realesrgan-x4plus-anime')
    p.add_argument('--scale', type=int, choices=range(1, 11), default=4)
    p.add_argument('--command', help='for --method command; {input} {output} {scale} are folders')
    p.add_argument('--force', action='store_true')
    args = p.parse_args()
    args.dump, args.work = args.dump.resolve(), args.work.resolve()
    if args.method == 'command' and not args.command:
        p.error('--method command requires --command')
    if args.method == 'realesrgan' and args.model.startswith('realesrgan-x4') and args.scale != 4:
        p.error('this Real-ESRGAN model requires --scale 4')

    settings = {'method': args.method, 'model': args.model if args.method == 'realesrgan' else None,
                'scale': args.scale, 'command': args.command}
    meta_path = args.work / 'upscale.json'
    sources_path = args.work / 'sources.json'
    sources = json.loads(sources_path.read_text()) if sources_path.exists() else {}
    if meta_path.exists() and json.loads(meta_path.read_text()) != settings:
        print('settings changed: upscaling everything again')
        args.force = True
    todo = []
    for scene, stem, png, _tsv in hd.captures(args.dump):
        out = args.work / 'up' / scene / f'{stem}.png'
        ident = f'{scene}/{stem}'
        digest = hashlib.sha256(png.read_bytes()).hexdigest()
        if args.force or not out.exists() or sources.get(ident) != digest:
            todo.append((scene, stem, png, out))
        sources[ident] = digest
    print(f'{len(todo)} pictures to upscale', flush=True)
    if not todo:
        return
    args.work.mkdir(parents=True, exist_ok=True)
    # Own only this newly created scratch directory; keep previous outputs.
    with tempfile.TemporaryDirectory(prefix='upscale-', dir=args.work) as scratch:
        prep, raw = Path(scratch) / 'prep', Path(scratch) / 'raw'
        prep.mkdir()
        for scene, stem, png, _ in todo:
            rgba = hd.load_rgba(png)
            if rgba.shape[:2] != (hd.FIELD_H, hd.FIELD_W):
                raise SystemExit(f'{png}: expected 256x224')
            Image.fromarray(fill_transparent(rgba)).save(prep / f'{scene}__{stem}__rgb.png')
            alpha = rgba[..., 3]
            Image.fromarray(np.dstack([alpha] * 3)).save(prep / f'{scene}__{stem}__alpha.png')
        run_upscaler(args, prep, raw)
        for scene, stem, _png, out in todo:
            rgb = np.asarray(Image.open(raw / f'{scene}__{stem}__rgb.png').convert('RGB'))
            a = np.asarray(Image.open(raw / f'{scene}__{stem}__alpha.png').convert('L')).astype(np.float32)
            expected = (hd.FIELD_H * args.scale, hd.FIELD_W * args.scale)
            if rgb.shape[:2] != expected or a.shape != expected:
                raise SystemExit(f'{stem}: upscaler output must be {expected[1]}x{expected[0]}')
            a = np.clip((a - 128) * 3 + 128, 0, 255).astype(np.uint8)
            hd.save_rgba(np.dstack([rgb, a]), out)
    meta_path.write_text(json.dumps(settings))
    sources_path.write_text(json.dumps(sources))
    print(f'upscaled {len(todo)} pictures into {args.work / "up"}')


if __name__ == '__main__':
    main()
