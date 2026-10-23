"""Exercise only isolated temporary game folders; never install into player data."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from hd.install_character_pack import install_pack, sha


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='sciv-pack-install-')
        self.root = Path(self.temporary.name)
        self.pack = self.root/'new-hd-pack'
        self.pack.mkdir()
        Image.new('RGBA', (129, 258), 'green').save(self.pack/'art.png')
        Image.new('RGBA', (768, 3072)).save(self.pack/'body.png')
        (self.pack/'character.json').write_text(json.dumps({'version': 1, 'frames': [
            {'id': 'pose', 'hd': {'image': 'art.png', 'display_size': [32, 64]}}]}))
        self.targets = [self.root/'game-one', self.root/'game-two']
        for target in self.targets:
            (target/'characters/previous').mkdir(parents=True)
            (target/'characters/previous/keep.txt').write_text('old character artwork')
            (target/'characters/selected.txt').write_bytes(b'previous\r\n')
            (target/'saves').mkdir()
            (target/'saves/save1.sav').write_bytes(b'original save data')
            (target/'config.ini').write_bytes(b'graphics settings')
            (target/'keybinds.ini').write_bytes(b'original key bindings')
        self.before = {str(p): sha(p) for target in self.targets for p in target.rglob('*') if p.is_file()}
        self.backup = self.root/'backup'

    def tearDown(self):
        self.temporary.cleanup()

    def unchanged(self, selection=True):
        for name, checksum in self.before.items():
            if selection or Path(name).name != 'selected.txt':
                self.assertEqual(sha(name), checksum, name)

    def test_character_two_targets_hashes_backup_and_protected_data(self):
        source_before = {p.name: sha(p) for p in self.pack.iterdir()}
        report = install_pack(self.pack, self.targets, self.backup)
        self.assertEqual(len(report['targets']), 2)
        for index, target in enumerate(self.targets):
            self.assertEqual((target/'characters/selected.txt').read_text().strip(), self.pack.name)
            self.assertEqual((self.backup/f'{index:02d}-selected.txt').read_bytes(), b'previous\r\n')
            for name, checksum in source_before.items():
                self.assertEqual(sha(target/'characters'/self.pack.name/name), checksum)
                self.assertEqual(sha(self.pack/name), checksum)
        self.unchanged(selection=False)
        self.assertTrue((self.backup/'install.json').is_file())

    def test_enemy_two_targets_create_collection_and_leave_character_choice(self):
        (self.pack/'enemies.json').write_text(json.dumps({'version': 1, 'frames': [{'id': 'enemy-pose', 'image': 'art.png'}]}))
        report = install_pack(self.pack, self.targets, self.backup, kind='enemy')
        self.assertEqual(report['kind'], 'enemy')
        for target in self.targets:
            self.assertEqual((target/'enemy_packs/selected.txt').read_text().strip(), self.pack.name)
            self.assertEqual(sha(target/'enemy_packs'/self.pack.name/'art.png'), sha(self.pack/'art.png'))
        self.unchanged()

    def test_second_destination_collision_aborts_before_any_write(self):
        (self.targets[1]/'characters'/self.pack.name).mkdir()
        with self.assertRaises(FileExistsError):
            install_pack(self.pack, self.targets, self.backup)
        self.assertFalse(self.backup.exists())
        self.assertFalse((self.targets[0]/'characters'/self.pack.name).exists())
        self.unchanged()

    def test_second_selection_failure_rolls_back_both_copies_and_first_selection(self):
        original_replace = Path.replace
        count = 0

        def fail_second_selection(path, target):
            nonlocal count
            if path.name.startswith('.selected-'):
                count += 1
                if count == 2:
                    raise OSError('simulated second selection write failure')
            return original_replace(path, target)

        with patch.object(Path, 'replace', fail_second_selection):
            with self.assertRaisesRegex(OSError, 'simulated'):
                install_pack(self.pack, self.targets, self.backup)
        self.unchanged()
        for target in self.targets:
            self.assertFalse((target/'characters'/self.pack.name).exists())
            self.assertFalse(list((target/'characters').glob('.*install*')))

    def test_invalid_kind_cannot_change_arbitrary_collection(self):
        with self.assertRaisesRegex(ValueError, 'kind'):
            install_pack(self.pack, self.targets, self.backup, kind='../saves')
        self.assertFalse(self.backup.exists())
        self.unchanged()


if __name__ == '__main__':
    unittest.main()
