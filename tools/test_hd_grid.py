"""Check registration endpoints, alpha filtering and strict 4x/8x source contracts."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent / 'hd'))
from prepare_stage01_grid import register_plane
from build_stage01_later import grid_asset


class GridTests(unittest.TestCase):
    def test_panel_endpoints_and_bottom_overhang(self):
        # Unequal authored widths must still land on the exact native grid.
        image = Image.new('RGBA', (35, 10), (90, 120, 150, 255))
        image.paste((255, 0, 0, 255), (0, 9, 35, 10))
        spec = {'source_panel_widths': [9, 10], 'native_panel_widths': [2, 2]}
        recipe = {'source_margin': 8, 'margin_native': 2, 'native_height': 2, 'source_height': 9}
        result, panels = register_plane(image, spec, recipe)
        self.assertEqual(result.size, (32, 8))
        self.assertEqual([p['output_box'] for p in panels],
                         [[0, 0, 8, 8], [8, 0, 16, 8], [16, 0, 24, 8], [24, 0, 32, 8]])
        self.assertEqual([p['source_box'][:3:2] for p in panels], [[0, 8], [8, 17], [17, 27], [27, 35]])
        # The authored row outside the original height must not become a floor row.
        self.assertTrue(np.all(np.array(result)[:, :, 0] < 150))

    def test_exact_inputs_are_not_filtered_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            data = np.random.default_rng(7).integers(0, 256, (64, 64, 4), dtype=np.uint8)
            Image.fromarray(data).save(root / 'motif.png')
            spec = dict(image='motif.png', source_scale=4, native_size=[16, 16])
            _, output = grid_asset(root, spec, (16, 16))
            self.assertTrue(np.array_equal(data, np.array(output)))

    def test_8x_keeps_footprint_and_rejects_bad_contracts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            Image.new('RGBA', (128, 128), (90, 180, 70, 255)).save(root / 'motif.png')
            spec = dict(image='motif.png', source_scale=8, native_size=[16, 16])
            _, output = grid_asset(root, spec, (16, 16))
            self.assertEqual(output.size, (64, 64))
            self.assertEqual(output.getpixel((32, 32)), (90, 180, 70, 255))
            for changes in ({'source_scale': 4}, {'source_scale': 5}, {'native_size': [8, 8]}, {'image': '../motif.png'}):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    grid_asset(root, {**spec, **changes}, (16, 16))


if __name__ == '__main__':
    unittest.main()
