"""Inventory local downloaded sprite/background sheets without modifying them.

  python tools/hd/hd_sources.py --source "$HOME/Downloads/assets"

Writes an index, not an in-game pack. Sheets with labels or coloured separator
backgrounds still need region selection and matching to the collected tiles.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path.home() / 'Downloads/assets')
    parser.add_argument('--out', type=Path,
                        default=Path(__file__).resolve().parents[2] / 'build/hd_work/source_sheets.json')
    args = parser.parse_args()
    source = args.source.resolve()
    if not source.is_dir():
        parser.error(f'sheet folder does not exist: {source}')
    entries = []
    for path in sorted(source.rglob('*.png')):
        with Image.open(path) as im:
            entries.append(dict(file=path.relative_to(source).as_posix(), width=im.width,
                                height=im.height, mode=im.mode,
                                top_left=list(im.convert('RGBA').getpixel((0, 0))),
                                sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    if not entries:
        parser.error(f'no PNG sheets in {source}')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(dict(version=1, source=str(source), sheets=entries),
                                   ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(entries)} sheets indexed in {args.out}')
    print('Sources unchanged. This index records provenance; it does not import labels '
          'or separator colours into the HD pack.')


if __name__ == '__main__':
    main()
