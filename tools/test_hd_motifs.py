"""ROM-free motif registration, flip, guard and editing roundtrip tests."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent / 'hd'))
import hd_common as hd
from hd_motifs import build_recipe


def main():
    with tempfile.TemporaryDirectory(prefix='hd-motifs-') as tmp:
        root = Path(tmp)
        layer = np.zeros((224, 256, 4), dtype=np.uint8)
        yy, xx = np.indices((8, 8))
        original = np.stack((xx*31, yy*31, (xx+yy)*15, np.where(xx < 6, 255, 0)), axis=2).astype(np.uint8)
        occurrences = []
        key = '0123456789abcdef'
        for flip in range(4):
            tile = original[:, ::-1] if flip & 1 else original
            tile = tile[::-1] if flip & 2 else tile
            layer[16:24, 8*flip:8*flip+8] = tile
            occurrences.append(f'{8*flip}\t16\t{key}\t{flip}\n')
        hd.save_rgba(layer, root / 'layer.png')
        (root / 'layer.tsv').write_text(''.join(occurrences))
        Image.fromarray(layer[16:24, :32].repeat(10, 0).repeat(10, 1)).save(root / 'art.png')
        recipe = {'version': 1, 'scale': 10, 'motifs': [{'name': 'flips', 'reference': 'layer.png',
                  'rect': [0, 16, 32, 8], 'artwork': 'art.png'}]}
        path = root / 'recipe.json'; path.write_text(json.dumps(recipe))
        tiles, receipt = build_recipe(path, root / 'pack')
        expected = original.repeat(10, 0).repeat(10, 1)
        assert len(tiles) == 4 and all(np.array_equal(v, expected) for v in tiles.values())
        assert len(receipt['duplicate_occurrences']) == 3
        meta = json.loads((root / 'pack/pack.json').read_text())
        assert len(meta['contexts'][key]) == 4
        # Exporting, editing and rebuilding must preserve placement guards.
        tool = hd.ROOT / 'tools/hd/hd_tiles.py'
        subprocess.run([sys.executable, str(tool), 'export', '--pack', str(root/'pack'),
                        '--out', str(root/'edit')], check=True)
        subprocess.run([sys.executable, str(tool), 'build', '--tiles', str(root/'edit'),
                        '--pack', str(root/'rebuilt'), '--scale', '10'], check=True)
        assert json.loads((root/'rebuilt/pack.json').read_text()) == meta
        before = (root / 'pack/pack.json').read_bytes()
        try:
            build_recipe(path, root / 'pack')
            raise AssertionError('overwrote existing artwork')
        except ValueError:
            pass
        assert (root / 'pack/pack.json').read_bytes() == before
        Image.new('RGBA', (319, 80)).save(root / 'art.png')
        try:
            build_recipe(path, root / 'undersized')
            raise AssertionError('accepted undersized art')
        except ValueError:
            pass
        assert not (root / 'undersized').exists()
        print('PASS: motif flips, alpha, independent context images, editing roundtrip, '
              'overwrite protection and minimum artwork resolution')


if __name__ == '__main__':
    main()
