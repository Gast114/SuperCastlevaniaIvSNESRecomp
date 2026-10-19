"""Shared sheets retain native geometry and reuse one edit across guarded scenes."""
import json
import itertools
from pathlib import Path
import sys
import tempfile

import numpy as np

sys.path.insert(0, str(Path(__file__).parent/'hd'))
import hd_common as hd
from hd_shared import extract, register, compact_contexts
from hd_tiles import write_pack


def rejects(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError('accepted invalid input')


def main():
    # All combinations of neighbor keys/flips, including missing neighbors,
    # keep the same acceptance under each reflection used by the live renderer.
    a, b = '0123456789abcdef', 'fedcba9876543210'
    choices = [
        {'image':a, 'flip':0, 'neighbors':[[1,0,a,0], [0,1,b,1]]},
        {'image':a, 'flip':0, 'neighbors':[[1,0,a,0]]},
        {'image':a, 'flip':1, 'neighbors':[[1,0,b,2], [0,1,b,1]]},
    ]
    compact = compact_contexts(choices)
    assert len(compact) == 2
    values = [None] + list(itertools.product((a,b), range(4)))
    for reflect in range(4):
        for environment in itertools.product(values, repeat=4):
            neighbors = dict(zip(((1,0),(-1,0),(0,1),(0,-1)), environment))
            def matches(contexts):
                for c in contexts:
                    r = reflect ^ c['flip']
                    if all(neighbors.get((dx*(-1 if r&1 else 1),dy*(-1 if r&2 else 1))) == (k, f^r)
                           for dx,dy,k,f in c['neighbors']):
                        return True
                return False
            assert matches(choices) == matches(compact)
    rejects(lambda: compact_contexts(choices + [{'image':b,'flip':0,'neighbors':[[1,0,a,0]]}]))
    with tempfile.TemporaryDirectory(prefix='hd-shared-') as tmp:
        root = Path(tmp); dump = root/'dump'; dump.mkdir()
        key, other = '0123456789abcdef', 'fedcba9876543210'
        pixels = '0' + '1'*63
        (dump/'tiles.tsv').write_text('\n'.join(
            f'{k}\t2\t0000001f03e07c00\t{pixels}' for k in (key, other)))
        native = hd.load_tiles(dump)[key].rgba()
        for scene, layer in (('level_b00','bg1'), ('wrong','bg1'), ('level_b00','bg2')):
            for frame in range(2):
                path = dump/'captures'/scene/f'{layer}_{frame}.png'
                hd.save_rgba(np.zeros((224,256,4), np.uint8), path)
                path.with_suffix('.tsv').write_text(''.join(
                    f'{i*8}\t16\t{key}\t{i}\n' for i in range(4)))
        art = np.full((160,160,4), (10,80,140,255), np.uint8)
        hd.save_rgba(art, root/'art.png'); hd.save_rgba(native, root/'reference.png')
        recipe = {'version':1, 'scale':10, 'sheets':[
            {'image':'art.png', 'reference':'reference.png', 'columns':1, 'keys':[key], 'opaque_material':True}]}
        path = root/'recipe.json'; path.write_text(json.dumps(recipe))
        tiles = extract(path, dump, root/'library')
        assert tiles[key].shape == (80,80,4)
        assert np.all(tiles[key][:10,:10,3] == 0)  # Native cutout retained.
        assert tuple(tiles[key][20,20]) == (10,80,140,255)
        rejects(lambda: extract(path, dump, root/'library'))
        hd.save_rgba(art[:79,:79], root/'art.png')
        rejects(lambda: extract(path, dump, root/'small'))
        assert not (root/'small').exists()
        hd.save_rgba(art, root/'art.png')
        translucent = art.copy(); translucent[...,3] = 128
        hd.save_rgba(translucent, root/'art.png')
        rejects(lambda: extract(path, dump, root/'translucent'))
        assert not (root/'translucent').exists()
        hd.save_rgba(art, root/'art.png')
        hd.save_rgba(native[:,::-1], root/'reference.png')
        rejects(lambda: extract(path, dump, root/'misregistered'))
        assert not (root/'misregistered').exists()
        # A pre-existing unrelated motif must survive while the selected key's
        # old variants are retired, not left earlier in the context search.
        old, preserved = '1111111111111111', '2222222222222222'
        base = root/'base'
        image = np.full((80,80,4), (20,30,40,255), np.uint8)
        write_pack({old:image, preserved:image}, base, 10)
        meta = json.loads((base/'pack.json').read_text())
        meta.update(requires=['tile-context-v1'], contexts={
            key:[{'image':old,'flip':0,'neighbors':[[1,0,key,1]]}],
            other:[{'image':preserved,'flip':0,'neighbors':[[1,0,key,1]]}]})
        (base/'pack.json').write_text(json.dumps(meta))
        index = root/'library/shared_tiles.json'
        first, receipt = register(index, [dump], 'level_b00', ['bg1'], root/'first', base)
        assert receipt['recorded_occurrences'] == {key:8}  # Other scenes/layers excluded.
        assert receipt['unique_contexts'] == {key:4}  # Identical frames deduplicated.
        assert len({c['image'] for c in first['contexts'][key]}) == 1
        assert {c['flip'] for c in first['contexts'][key]} == {0,1,2,3}
        assert first['contexts'][other] == meta['contexts'][other]
        assert old not in first['tiles']
        source = root/'library/shared'/f'{key}.png'
        edited = hd.load_rgba(source).copy(); edited[...,0]=150
        hd.save_rgba(edited, source)
        second, _ = register(index, [dump], 'level_b00', ['bg1'], root/'second', base)
        _, _, packed = hd.load_pack(root/'second')
        for c in second['contexts'][key]: assert np.array_equal(packed[c['image']], edited)
        assert np.array_equal(packed[preserved], image)
        rejects(lambda: register(index, [dump], 'missing', ['bg1'], root/'missing', base))
        assert not (root/'missing').exists()
        rejects(lambda: register(index, [dump], 'level_b00', ['bg1'], root/'first', base))
        # Fractional source-cell boundaries are valid at an exact grid aspect;
        # explicit null cells pad the atlas without inventing original keys.
        hd.save_rgba(np.full((161,322,4), (30,60,90,255), np.uint8), root/'fractional.png')
        padded = {'version':1, 'scale':10, 'sheets':[{'image':'fractional.png',
                  'columns':4, 'keys':[key]+[None]*7, 'opaque_material':True}]}
        path.write_text(json.dumps(padded))
        result = extract(path, dump, root/'fractional')
        assert list(result) == [key] and tuple(result[key][20,20]) == (30,60,90,255)
    print('PASS: registered sheet geometry, native alpha, minimum resolution, guarded reuse/flips, '
          'capture deduplication, scene/layer filters, base preservation and shared edits')


if __name__ == '__main__':
    main()
