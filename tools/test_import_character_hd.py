"""Focused import contract checks: fractional input, original bytes, exact identity."""
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw

from import_character_hd import import_poses, make_workspace, sha


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='sciv-hd-import-')
        self.root = Path(self.temporary.name)
        self.template = self.root/'template'
        self.template.mkdir()
        self.native = Image.new('RGBA', (32, 64))
        draw = ImageDraw.Draw(self.native)
        draw.polygon([(0, 0), (31, 0), (31, 63), (0, 63), (0, 47), (15, 32), (0, 17)], fill='white')
        sheet = Image.new('RGBA', (768, 3072))
        sheet.paste(self.native, (31, 16))
        sheet.save(self.template/'body.png')
        self.manifest = {'version': 1, 'cell_size': 96, 'name': 'Captured', 'gameplay': {'walk_percent': 100},
                         'frames': [{'id': '8000-0123456789abcdef', 'cell': 0, 'label': 'Idle',
                                     'anchor': [48, 48], 'hand': [36, 30]}]}
        self.save_manifest()
        self.references = self.root/'Original'
        self.artwork = self.root/'HD'
        self.references.mkdir()
        self.artwork.mkdir()
        self.native.save(self.references/'Standing.png')

    def tearDown(self):
        self.temporary.cleanup()

    def save_manifest(self):
        (self.template/'character.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def test_fractional_403125_keeps_png_and_native_registration(self):
        artwork = self.artwork/'Standing.png'
        self.native.resize((129, 258)).save(artwork)
        before = sha(artwork)
        output = self.root/'pack'
        receipts = import_poses(self.template, self.artwork, output, native=self.references)
        frame = json.loads((output/'character.json').read_text())['frames'][0]
        self.assertEqual(frame['hd']['display_size'], [32, 64])
        self.assertEqual(frame['hd']['offset'], [31, 16])
        self.assertEqual(frame['anchor'], [48, 48])
        self.assertEqual(frame['hand'], [36, 30])
        self.assertEqual(receipts[0]['working_scale'], [4.03125, 4.03125])
        self.assertEqual(before, sha(output/'Standing.png'))
        self.assertEqual(before, sha(artwork))
        with Image.open(output/'Standing.png') as copied:
            self.assertEqual(copied.size, (129, 258))
        self.assertTrue((output/'preview.html').is_file())

    def test_old_10x_pair_still_maps_and_keeps_bytes(self):
        self.native.save(self.artwork/'Standing.png')
        image = self.artwork/'Standing_HD_10x_320x640.png'
        self.native.resize((320, 640)).save(image)
        output = self.root/'legacy'
        records = import_poses(self.template, self.artwork, output)
        self.assertEqual(records[0]['working_scale'], [10, 10])
        self.assertEqual(sha(image), sha(output/image.name))

    def test_workspace_resolves_identical_captured_silhouettes(self):
        sheet = Image.open(self.template/'body.png').convert('RGBA')
        sheet.paste(self.native, (96+31, 16))
        sheet.save(self.template/'body.png')
        self.manifest['frames'].append({**self.manifest['frames'][0], 'id': '8100-0123456789abcdef', 'cell': 1})
        self.save_manifest()
        self.native.resize((129, 258)).save(self.artwork/'Standing.png')
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            import_poses(self.template, self.artwork, self.root/'ambiguous', native=self.references)
        self.assertFalse((self.root/'ambiguous').exists())
        workspace = make_workspace(self.template, self.root/'workspace')
        records = json.loads((workspace/'workspace.json').read_text())['poses']
        for record in records:
            self.native.resize((129, 258)).save(workspace/'HD'/record['file'])
        result = import_poses(self.template, None, self.root/'exact', workspace=workspace)
        self.assertEqual({r['pose'] for r in result}, {r['pose'] for r in records})

    def test_canvas_distortion_stops_before_publishing(self):
        self.native.resize((129, 300)).save(self.artwork/'Standing.png')
        with self.assertRaisesRegex(ValueError, 'aspect ratio'):
            import_poses(self.template, self.artwork, self.root/'bad', native=self.references)
        self.assertFalse((self.root/'bad').exists())

    def test_changed_workspace_reference_stops_import(self):
        workspace = make_workspace(self.template, self.root/'workspace')
        record = json.loads((workspace/'workspace.json').read_text())['poses'][0]
        original = workspace/'Original'/record['file']
        self.native.resize((129, 258)).save(workspace/'HD'/record['file'])
        original.write_bytes(original.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError, 'modified'):
            import_poses(self.template, None, self.root/'bad', workspace=workspace)
        self.assertFalse((self.root/'bad').exists())

    def test_existing_output_never_overwritten(self):
        self.native.resize((129, 258)).save(self.artwork/'Standing.png')
        output = self.root/'existing'
        output.mkdir()
        (output/'keep.txt').write_text('keep')
        with self.assertRaises(FileExistsError):
            import_poses(self.template, self.artwork, output, native=self.references)
        self.assertEqual((output/'keep.txt').read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
