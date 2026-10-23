"""Practical regression of live workshop PNGs using recorded native action fields.

Only new folders under artwork-local/enemy-workshop are written. User artwork,
player settings and running games are never touched. This checks the Python
preview/export path; it does not claim a new emulator or renderer replay.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageChops, ImageDraw, ImageOps

from enemy_workshop import preview
from enemy_workshop_assets import Workspace
from enemy_hd import prepare

ROOT = Path(__file__).resolve().parents[1]
CONFIG = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pixels(image):
    return hashlib.sha256(image.tobytes()).hexdigest()


def different(left, right):
    return ImageChops.difference(left, right).getbbox() is not None


class WorkshopLiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = CONFIG['recording']/'enemy_packs/native-template'
        cls.actions = json.loads((CONFIG['recording']/'native-actions.json').read_text())
        cls.snapshots = [s for action in cls.actions for s in action['frames']]
        cls.allowed = {identifier for snapshot in cls.snapshots for actor in snapshot['actors']
                       for identifier in [actor['id']]+[p['id'] for p in actor['parts']]}
        cls.fixture = next(s for s in cls.snapshots if any(a['slot'] == 0x580 and len(a['parts']) >= 3 for a in s['actors']))
        cls.actor = next(a for a in cls.fixture['actors'] if a['slot'] == 0x580)
        cls.native_source_before = {p.name: sha(p) for p in cls.source.iterdir() if p.is_file()}

    @classmethod
    def tearDownClass(cls):
        assert cls.native_source_before == {p.name: sha(p) for p in cls.source.iterdir() if p.is_file()}, 'Native capture source changed'

    def setUp(self):
        self.folder = CONFIG['out']/self._testMethodName
        self.folder.mkdir()
        self.workspace = Workspace(self.folder/'workspace')
        self.workspace.ingest(self.source, self.allowed)
        self.assertTrue(self.allowed <= self.workspace.frames.keys(), 'A recorded native pose/component is missing')
        self.original_hashes = {p.name: sha(p) for p in (self.workspace.folder/'references').iterdir()}

    def tearDown(self):
        self.assertEqual(self.original_hashes,
                         {p.name: sha(p) for p in (self.workspace.folder/'references').iterdir()},
                         'Live editing changed a native reference')

    def view(self, custom=False, snapshot=None):
        return preview(snapshot or self.fixture, self.workspace, custom, (512, 448), follow=True)

    def native_oam_oracle(self, snapshot):
        """Compose raw native pieces globally, independently of actor grouping.

        Lower OAM numbers win OBJ overlap; OBJ priority describes depth versus
        backgrounds, not a replacement for global OAM ordering on this canvas.
        """
        image = Image.new('RGBA', (512, 448), '#19212c')
        main = next((a for a in snapshot['actors'] if a['slot'] == 0x580), None)
        origin = (128-main['x'], 128-main['y']) if main else (0, 0)
        parts = [(part, actor) for actor in snapshot['actors'] for part in actor['parts']]
        for part, actor in sorted(parts, key=lambda pair: pair[0]['oam'], reverse=True):
            frame = self.workspace.frames[part['id']]
            source = self.workspace.image(part['id'], False)
            dw, dh = frame['display_size']
            ax, ay = frame['anchor']
            if actor['flip'] & 1:
                source = ImageOps.mirror(source)
            if actor['flip'] & 2:
                source = ImageOps.flip(source)
            source = source.resize((dw*2, dh*2), Image.Resampling.NEAREST)
            x = actor['x']+origin[0]-(dw-ax if actor['flip'] & 1 else ax)
            y = actor['y']+origin[1]-(dh-ay if actor['flip'] & 2 else ay)
            image.alpha_composite(source, (x*2, y*2))
        return image.convert('RGB')

    def artwork(self, identifier):
        return self.workspace.folder/'artwork'/self.workspace.frames[identifier]['image']

    def save(self, image, path):
        # Explicit timestamp movement avoids depending on filesystem granularity.
        previous = path.stat().st_mtime_ns if path.exists() else 0
        image.save(path)
        current = max(path.stat().st_mtime_ns, previous+1_000_000)
        os.utime(path, ns=(current, current))

    def color(self, identifier, color, full_canvas=False):
        original = self.workspace.image(identifier, False)
        image = Image.new('RGBA', original.size, color)
        if not full_canvas:
            image.putalpha(original.getchannel('A'))
        return image.resize(tuple(round(n*129/32) for n in original.size), Image.Resampling.NEAREST)

    def edit(self, identifier, color, full_canvas=False):
        image = self.color(identifier, color, full_canvas)
        self.save(image, self.artwork(identifier))
        return image

    def test_original_and_unedited_redesign_share_all_native_fields(self):
        self.assertEqual({a['action'] for a in self.actions}, {'Gehen', 'Werfen', 'Zerfallen'})
        self.assertTrue(any(a['type'] == 2 for s in self.snapshots for a in s['actors']), 'No native bone projectile recorded')
        self.assertTrue(any(a['type'] == 45 for s in self.snapshots for a in s['actors']), 'No native disintegration effect recorded')
        self.assertGreater(len({(a['x'], a['y']) for s in self.snapshots for a in s['actors'] if a['slot'] == 0x580}), 10)
        for snapshot in self.snapshots:
            left, right = self.view(False, snapshot), self.view(True, snapshot)
            self.assertEqual(pixels(left), pixels(right), f'Unedited reference differs at native tick {snapshot["tick"]}')
        samples = []
        for action in self.actions:
            snapshot = max(action['frames'], key=lambda s: len(s['actors']))
            pair = Image.new('RGB', (1024, 476), '#19212c')
            pair.paste(self.view(False, snapshot), (0, 28))
            pair.paste(self.view(True, snapshot), (512, 28))
            ImageDraw.Draw(pair).text((8, 8), f'{action["action"]}: Original | unedited PNG / native field {snapshot["tick"]}', fill='white')
            samples.append(pair)
        contact = Image.new('RGB', (1024, 476*len(samples)))
        for number, sample in enumerate(samples):
            contact.paste(sample, (0, number*476))
        contact.save(self.folder/'native-action-comparison.png')

    def test_live_whole_png_partial_save_missing_file_and_recovery(self):
        identifier = self.actor['id']
        original = self.view(False)
        self.assertEqual(pixels(original), pixels(self.view(True)))
        self.edit(identifier, 'magenta')
        changed = self.view(True)
        self.assertTrue(different(changed, original), 'Edited complete pose did not appear live')
        self.assertEqual(pixels(original), pixels(self.view(False)))
        self.edit(identifier, 'lime')
        second = self.view(True)
        self.assertTrue(different(changed, second), 'Second valid save was cached indefinitely')
        target = self.artwork(identifier)
        valid_bytes = target.read_bytes()
        target.write_bytes(b'\x89PNG\r\n\x1a\nPARTIAL SAVE')
        self.assertEqual(pixels(second), pixels(self.view(True)), 'Partial save discarded last good artwork')
        self.assertTrue(self.workspace.last_error)
        target.unlink()
        self.assertEqual(pixels(second), pixels(self.view(True)), 'Temporary file replacement lost last good artwork')
        target.write_bytes(valid_bytes)
        self.edit(identifier, 'cyan')
        third = self.view(True)
        self.assertTrue(different(second, third), 'Valid PNG after partial save did not recover')
        self.assertEqual(pixels(original), pixels(self.view(False)))
        # A different captured pose must not retain this pose's HD image.
        other = next(s for s in self.snapshots if s['actors'] and all(a['id'] != identifier for a in s['actors']))
        self.assertEqual(pixels(self.view(False, other)), pixels(self.view(True, other)))
        original.save(self.folder/'original.png')
        third.save(self.folder/'live-recovered.png')

    def test_native_preview_respects_global_oam_between_skeleton_and_bone(self):
        differences = []
        for snapshot in self.snapshots:
            expected = self.native_oam_oracle(snapshot)
            actual = self.view(False, snapshot)
            box = ImageChops.difference(actual, expected).getbbox()
            if box:
                differences.append({'tick': snapshot['tick'], 'bounds': list(box)})
                if len(differences) == 1:
                    actual.save(self.folder/'actor-order-actual.png')
                    expected.save(self.folder/'native-global-oam-expected.png')
            self.assertEqual(pixels(actual), pixels(self.view(True, snapshot)))
        (self.folder/'global-oam-differences.json').write_text(json.dumps(differences, indent=2))
        self.assertEqual(len(differences), 0, f'{len(differences)} fields disagree with native global OAM order; first: {differences[:2]}')

    def test_whole_pose_precedes_component_and_native_neighbours_survive(self):
        identifier = self.actor['id']
        part = next(p['id'] for p in self.actor['parts']
                    if self.workspace.frames[p['id']]['image'] != self.workspace.frames[identifier]['image'])
        pristine = self.artwork(identifier).read_bytes()
        original = self.view(False)
        self.edit(identifier, 'cyan')
        whole_only = self.view(True)
        self.edit(part, 'orange', full_canvas=True)
        self.assertEqual(pixels(whole_only), pixels(self.view(True)), 'Component incorrectly overlaid a complete replacement pose')
        # Restore the untouched enlarged full-pose template. Only the part now wins.
        self.artwork(identifier).write_bytes(pristine)
        self.assertFalse(self.workspace.edited(identifier))
        component_only = self.view(True)
        self.assertTrue(different(component_only, original), 'Component-only replacement did not appear')
        self.assertTrue(different(component_only, whole_only))
        # Make just that one component invisible: remaining parts must survive.
        with Image.open(self.artwork(part)) as image:
            transparent = Image.new('RGBA', image.size)
        self.save(transparent, self.artwork(part))
        removed = self.view(True)
        self.assertTrue(different(removed, original))
        self.assertTrue(different(removed, component_only))
        background = Image.new('RGB', removed.size, '#19212c')
        self.assertTrue(different(removed, background), 'Replacing one part erased the entire native actor')
        self.assertEqual(pixels(original), pixels(self.view(False)))
        component_only.save(self.folder/'component-only.png')
        removed.save(self.folder/'one-component-transparent.png')
        whole_only.save(self.folder/'whole-pose-priority.png')

    def test_replacement_validation_history_and_source_bytes(self):
        identifier = self.actor['id']
        target = self.artwork(identifier)
        before = target.read_bytes()
        replacement = self.folder/'finished-403125.png'
        self.color(identifier, 'yellow').save(replacement)
        source_hash = sha(replacement)
        self.workspace.replace(identifier, replacement)
        self.assertEqual(sha(target), source_hash, 'Replacement was resized or reencoded')
        self.assertEqual(sha(replacement), source_hash, 'Artist source was modified')
        backups = list((self.workspace.folder/'history').rglob('*.png'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), before)
        current = target.read_bytes()
        wrong_aspect = self.folder/'cropped.png'
        Image.new('RGBA', (387, 200), 'red').save(wrong_aspect)
        partial = self.folder/'invalid.png'
        partial.write_bytes(b'partial')
        for invalid in (wrong_aspect, partial):
            with self.assertRaises((ValueError, OSError)):
                self.workspace.replace(identifier, invalid)
            self.assertEqual(target.read_bytes(), current, 'Rejected PNG damaged current artwork')
        self.workspace.replace(identifier, target)
        self.assertEqual(target.read_bytes(), current)
        # A cropped direct Photoshop save must also keep the last good
        # preview and stop export before an unusable destination is created.
        last_good=self.workspace.image(identifier,True)
        target.write_bytes(wrong_aspect.read_bytes())
        self.assertEqual(pixels(self.workspace.image(identifier,True)),pixels(last_good))
        rejected=self.folder/'cropped-export'
        with self.assertRaises(ValueError):self.workspace.build_pack(rejected)
        self.assertFalse(rejected.exists())

    def test_mixed_priority_or_color_math_declines_whole_pose_like_core(self):
        identifier = self.actor['id']
        part = next(p['id'] for p in self.actor['parts']
                    if self.workspace.frames[p['id']]['image'] != self.workspace.frames[identifier]['image'])
        self.edit(part, 'orange')
        expected_parts = self.view(True)
        self.edit(identifier, 'cyan', full_canvas=True)
        uniform_whole = self.view(True)
        self.assertTrue(different(uniform_whole, expected_parts))
        for kind in ('priority', 'math'):
            with self.subTest(mixed=kind):
                snapshot = copy.deepcopy(self.fixture)
                actor = next(a for a in snapshot['actors'] if a['id'] == identifier)
                for piece in actor['parts']:
                    piece['math'] = 0
                if kind == 'priority':
                    actor['parts'][0]['priority'] = (actor['parts'][0]['priority']+1)%4
                else:
                    actor['parts'][0]['math'] = 1
                actual = self.view(True, snapshot)
                self.assertEqual(pixels(actual), pixels(expected_parts),
                                 f'Mixed {kind} accepted a complete replacement pose which the native core declines')
        uniform_math = copy.deepcopy(self.fixture)
        for actor in uniform_math['actors']:
            for piece in actor['parts']:
                piece['math'] = 1
        self.assertEqual(pixels(self.view(True, uniform_math)), pixels(uniform_whole))

    def test_existing_prepare_project_keeps_workshop_labels_and_native_baselines(self):
        destination = self.folder/'older-import-project'
        prepare(self.source, destination, work_size=387)
        # prepare() intentionally creates a standalone import project, without
        # the workshop's editor-only labels and component flags.
        manifest = json.loads((destination/'project.json').read_text())
        self.assertTrue(any('label' not in frame for frame in manifest['frames']))
        workspace = Workspace(destination)
        self.assertTrue(all(frame.get('label') for frame in workspace.frames.values()))
        self.assertTrue(all(frame['component'] == ('__teil-' in frame['id']) for frame in workspace.frames.values()))
        self.assertEqual(pixels(preview(self.fixture, workspace, False, (512, 448))),
                         pixels(preview(self.fixture, workspace, True, (512, 448))))
        self.assertFalse(any(workspace.edited(identifier) for identifier in workspace.frames))
        with self.assertRaisesRegex(ValueError, 'No changed artwork'):
            workspace.build_pack(self.folder/'unedited-legacy-export')
        self.assertFalse((self.folder/'unedited-legacy-export').exists())

    def test_pack_contains_changed_poses_and_parts_at_exact_source_resolution(self):
        identifier = self.actor['id']
        part = next(p['id'] for p in self.actor['parts']
                    if self.workspace.frames[p['id']]['image'] != self.workspace.frames[identifier]['image'])
        self.edit(identifier, 'cyan')
        self.edit(part, 'orange')
        destination = self.folder/'prepared-pack'
        self.workspace.build_pack(destination)
        packed = json.loads((destination/'enemies.json').read_text())['frames']
        self.assertIn(identifier, {f['id'] for f in packed})
        self.assertIn(part, {f['id'] for f in packed})
        self.assertEqual({f['id'] for f in packed},
                         {i for i in self.workspace.frames if self.workspace.edited(i)})
        for frame in packed:
            self.assertEqual(sha(destination/frame['image']), sha(self.workspace.folder/'artwork'/frame['image']))
            self.assertEqual(frame['display_size'], self.workspace.frames[frame['id']]['display_size'])
            self.assertEqual(frame['anchor'], self.workspace.frames[frame['id']]['anchor'])
        reload = Workspace(self.workspace.folder)
        self.assertEqual(pixels(self.view(True)), pixels(preview(self.fixture, reload, True, (512, 448))))
        self.assertEqual(reload.ingest(self.source, self.allowed), 0)
        # Export must refuse an unfinished save, keeping the live preview intact.
        last_good = self.view(True)
        self.artwork(identifier).write_bytes(b'PNG currently being saved')
        invalid_destination = self.folder/'partial-export'
        with self.assertRaises((ValueError, OSError)):
            self.workspace.build_pack(invalid_destination)
        self.assertFalse(invalid_destination.exists())
        self.assertEqual(pixels(self.view(True)), pixels(last_good))

    def test_legacy_workspace_without_work_template_metadata_ingests_new_pose(self):
        legacy = self.folder/'legacy-workspace'
        legacy.mkdir()
        (legacy/'project.json').write_text(json.dumps({'version': 1, 'name': 'Old valid project', 'frames': []}))
        workspace = Workspace(legacy)
        count = workspace.ingest(self.source, {self.actor['id']})
        self.assertEqual(count, 1)
        self.assertIn(self.actor['id'], workspace.frames)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recording', type=Path, default=ROOT/'artwork-local/enemy-workshop/session-ie7cbyp8')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    parent = ROOT/'artwork-local/enemy-workshop'
    parent.mkdir(parents=True, exist_ok=True)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=False)
        output = args.out.resolve()
    else:
        output = Path(tempfile.mkdtemp(prefix='live-check-', dir=parent)).resolve()
    CONFIG.update(recording=args.recording.resolve(), out=output)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WorkshopLiveTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'passed': result.wasSuccessful(), 'tests_run': result.testsRun,
              'recording': str(CONFIG['recording']), 'artifacts': str(output),
              'failures': [{'test': str(test), 'details': details} for test, details in result.failures+result.errors],
              'scope': 'Python live preview/export using recorded true-engine snapshots; no new engine replay or player data changes'}
    (output/'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'tests': result.testsRun, 'artifacts': str(output)}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    main()
