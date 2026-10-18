"""The whole offline half of the HD pipeline in one go (docs/HD_PIPELINE.md):
upscale what the game collected, build the HD pack, preview the newest debug
marker with it.

  python tools/hd/hd_pipeline.py [--build build] [--method realesrgan|nearest] [--model ...]

--build is the game folder holding hd_dump/ (and debug_markers/); the work
folder and the pack are written next to it (hd_work/, hd_pack/).
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def run(script, *args):
    print('>', script, *args, flush=True)
    subprocess.run([sys.executable, str(HERE / script), *map(str, args)], check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--build', type=Path, default=ROOT / 'build')
    p.add_argument('--method', choices=('realesrgan', 'nearest', 'command'), default='realesrgan')
    p.add_argument('--command', help='upscaler command template, for --method command')
    p.add_argument('--model', default='realesrgan-x4plus-anime')
    p.add_argument('--scale', type=int, choices=range(1, 5), default=4)
    p.add_argument('--force', action='store_true')
    args = p.parse_args()
    if args.method == 'command' and not args.command:
        p.error('--method command requires --command')
    b = args.build
    upscale = ['--dump', b / 'hd_dump', '--work', b / 'hd_work', '--method', args.method,
               '--model', args.model, '--scale', args.scale]
    if args.command:
        upscale += ['--command', args.command]
    run('hd_upscale.py', *upscale, *(['--force'] if args.force else []))
    run('hd_build_pack.py', '--dump', b / 'hd_dump', '--work', b / 'hd_work', '--pack', b / 'hd_pack')
    markers = b / 'debug_markers'
    if markers.is_dir() and any(markers.glob('*/lines.bin')):
        run('hd_preview.py', '--markers', markers, '--pack', b / 'hd_pack')


if __name__ == '__main__':
    main()
