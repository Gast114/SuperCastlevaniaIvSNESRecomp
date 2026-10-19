"""Shared library: repeated captures, palette variants and preservation of edits."""
import json
from pathlib import Path
import sys
import tempfile

import numpy as np

sys.path.insert(0, str(Path(__file__).parent / 'hd'))
import hd_common as hd
from hd_catalog import catalog


def main():
    with tempfile.TemporaryDirectory(prefix='hd-catalog-') as tmp:
        root = Path(tmp)
        keys = ['0123456789abcdef', 'fedcba9876543210']
        dumps = [root/'first', root/'second']
        for dump in dumps:
            dump.mkdir()
            (dump/'tiles.tsv').write_text('\n'.join(
                f'{k}\t2\t0000{color}00000000\t' + '1'*64
                for k, color in zip(keys, ('001f', '03e0'))))
            frame = dump/'captures/level/bg1_001.png'
            hd.save_rgba(np.zeros((224, 256, 4), np.uint8), frame)
            frame.with_suffix('.tsv').write_text(
                f'0\t0\t{keys[0]}\t0\n8\t0\t{keys[0]}\t1\n16\t0\t{keys[1]}\t0\n')
        output = root/'library'
        first = catalog(dumps, output)
        assert first['summary'] == dict(unique_tiles=2, recorded_occurrences=6,
                                       shared_artwork_ready=0, palette_families=1)
        # Palette family is information only: both original keys survive.
        assert len(first['tiles']) == 2
        art = np.full((80, 80, 4), (41, 97, 153, 255), np.uint8)
        path = output/'shared'/f'{keys[0]}.png'
        hd.save_rgba(art, path); before = path.read_bytes()
        second = catalog(dumps, output)
        assert second['summary']['shared_artwork_ready'] == 1
        assert path.read_bytes() == before
        index = json.loads((output/'shared_tiles.json').read_text())
        assert index == {keys[0]: f'shared/{keys[0]}.png'}
        hd.save_rgba(art[:79], path)
        try:
            catalog(dumps, output)
            raise AssertionError('accepted wrong artwork size')
        except ValueError:
            pass
        assert path.read_bytes() != before  # Invalid edited source is preserved too.
    print('PASS: repeated captures, distinct palette variants, reusable index and edit preservation')


if __name__ == '__main__':
    main()
