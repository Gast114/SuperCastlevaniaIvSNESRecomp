"""List and inspect debug markers recorded in game (Ctrl+D / pad Select+L3).

  python tools/debug_markers.py                 # newest first: id, scene, note
  python tools/debug_markers.py show [id]       # one marker in full (default: newest)
  python tools/debug_markers.py --dir build-dev/debug_markers ...

A marker folder holds state.sav (load with `sciv_play.py loadfile <path>`),
screen.png (the presented field with widescreen margins), video.bin
(tools/re/render_map.py), wram.bin, marker.json and note.md.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def markers(folder):
    if not folder.is_dir():
        return []
    found = [d for d in folder.iterdir() if (d / 'marker.json').is_file()]
    return sorted(found, key=lambda d: d.name, reverse=True)


def load(marker):
    return json.loads((marker / 'marker.json').read_text(encoding='utf-8', errors='replace'))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dir', type=Path, default=ROOT / 'build' / 'debug_markers')
    parser.add_argument('command', nargs='?', default='list', choices=('list', 'show'))
    parser.add_argument('id', nargs='?')
    args = parser.parse_args()
    found = markers(args.dir)
    if not found:
        print(f'no markers in {args.dir}')
        return
    if args.command == 'list':
        for marker in found:
            data = load(marker)
            state = data.get('state', {})
            first = (data.get('note') or '(ohne Beschreibung)').splitlines()[0]
            print(f"{marker.name}  frame {data.get('frame')}  mode {state.get('game_mode')}/"
                  f"{state.get('mode_step')} block {state.get('block')} cam {state.get('camera_x')}"
                  f"  ws={data.get('widescreen')}  {first}")
        return
    marker = next((m for m in found if not args.id or m.name.startswith(args.id)), None)
    if not marker:
        raise SystemExit(f'no marker {args.id!r} in {args.dir}')
    print(marker.resolve())
    print(json.dumps(load(marker), indent=2, ensure_ascii=False))
    print('files:', ', '.join(sorted(p.name for p in marker.iterdir())))


if __name__ == '__main__':
    main()
