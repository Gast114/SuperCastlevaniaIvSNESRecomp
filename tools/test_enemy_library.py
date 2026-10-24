"""Check persistent library/artist-workspace integration with real native PNGs.

No player folder or existing artist workspace is changed. The cache-resume
probe forbids starting an emulator. Fixture pixels come from earlier retail
engine recordings, including the boss 8B body stored as actor 09.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import enemy_workshop_library as library
from enemy_workshop_assets import Workspace
from enemy_workshop_native import NativeSession
from enemy_catalog_profiles import boss_profiles

ROOT = Path(__file__).resolve().parents[1]
CONFIG = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def bundle(source, actor_type):
    frames = read(source/'enemies.json')['frames']
    whole = next(frame for frame in frames if frame['actor_type'] == actor_type and '__teil-' not in frame['id'])
    return [frame for frame in frames if frame['id'] == whole['id'] or frame['id'].startswith(whole['id']+'__teil-')]


def clone_frames(source, frames, destination):
    destination.mkdir(parents=True)
    for frame in frames:
        shutil.copy2(source/frame['reference'], destination/frame['reference'])
    write(destination/'enemies.json', {'version': 1, 'name': 'Real recorded PNG test subset', 'frames': frames})


class LibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sessions = ROOT/'artwork-local/enemy-workshop'
        cls.catalog_source = sessions/'session-2yn_426z/enemy_packs/native-template'
        cls.boss_source = sessions/'session-w5os5_vb/enemy_packs/native-template'
        cls.ordinary = bundle(cls.catalog_source, 17)+bundle(cls.catalog_source, 9)
        cls.orphan = bundle(cls.catalog_source, 7)
        cls.boss = bundle(cls.boss_source, 9)
        cls.source_hashes = {str(source/frame['reference']): sha(source/frame['reference'])
                             for source, frames in ((cls.catalog_source, cls.ordinary+cls.orphan), (cls.boss_source, cls.boss))
                             for frame in frames}

    @classmethod
    def tearDownClass(cls):
        for path, checksum in cls.source_hashes.items():
            assert sha(path) == checksum, 'A real native capture was changed'

    def setUp(self):
        self.folder = CONFIG['out']/self._testMethodName
        self.folder.mkdir()
        self.normal_subset = self.folder/'catalog-native'
        self.boss_subset = self.folder/'boss-native'
        clone_frames(self.catalog_source, self.ordinary+self.orphan, self.normal_subset)
        clone_frames(self.boss_source, self.boss, self.boss_subset)
        self.destination = self.folder/'library'
        library.merge_sources(self.destination, [self.normal_subset, self.boss_subset])
        self.profiles = []
        for entry, frames in (({'type': 17, 'variant': 0, 'boss': False, 'name': 'Skelett'}, [f for f in self.ordinary if f['actor_type'] == 17]),
                              ({'type': 9, 'variant': 0, 'boss': False, 'name': 'Flugkreatur'}, [f for f in self.ordinary if f['actor_type'] == 9]),
                              ({'type': 0x8b, 'variant': 0, 'boss': True, 'main_type': 9, 'name': 'Boss 8B'}, self.boss)):
            identifiers = [frame['id'] for frame in frames]
            self.profiles.append(dict(entry, key=library.profile_key(entry), frame_ids=identifiers,
                main_frame_ids=identifiers, child_frame_ids=[], status='captured', captured_fields=1,
                requested_fields=1, capture_complete=True,
                coverage_complete=False, coverage_note='Echter nativer Ausschnitt; kein vollständiger Aktionskatalog.'))
        self.index = {'version': 1, 'rom_sha256': library.ROM_SHA256, 'destination': str(self.destination),
                      'profiles': self.profiles, 'sources': [str(self.normal_subset), str(self.boss_subset)],
                      'coverage_complete': False, 'capture_fields': 1, 'run_complete': False}
        write(self.destination/'library.json', self.index)

    def test_merged_pngs_preserve_each_recorded_source_byte(self):
        target = self.destination/'native-template'
        frames = read(target/'enemies.json')['frames']
        expected = {frame['id']: (self.normal_subset if frame in self.ordinary+self.orphan else self.boss_subset)/frame['reference']
                    for frame in self.ordinary+self.orphan+self.boss}
        self.assertEqual({frame['id'] for frame in frames}, set(expected))
        for frame in frames:
            self.assertEqual(sha(target/frame['reference']), sha(expected[frame['id']]))
        again = library.merge_sources(self.destination, [self.normal_subset, self.boss_subset])
        self.assertEqual(again['added'], 0)

    def test_same_id_conflict_is_reported_without_overwriting_existing_png(self):
        frame = self.ordinary[0]
        conflict = self.folder/'conflicting-native'
        clone_frames(self.normal_subset, [frame], conflict)
        with Image.open(conflict/frame['reference']) as image:
            altered = image.convert('RGBA')
        altered.putpixel((0, 0), (255, 0, 255, 255))
        altered.save(conflict/frame['reference'])
        target = self.destination/'native-template'/frame['reference']
        before = sha(target)
        result = library.merge_sources(self.destination, [conflict])
        self.assertEqual(sha(target), before)
        self.assertTrue(any(item['id'] == frame['id'] for item in result['conflicts']))

    def test_profiles_filter_real_boss_alias_by_exact_ids(self):
        workspace = Workspace(self.folder/'workspace')
        workspace.load_library(self.destination)
        expected_ids = {identifier for row in self.profiles for identifier in row['frame_ids']}
        self.assertEqual(set(workspace.frames), expected_ids, 'Unmapped room props leaked into the library workspace')
        for row in self.profiles:
            for components in (False, True):
                selected = workspace.frames_for(row['key'], components=components)
                expected_images = {workspace.frames[identifier]['image'] for identifier in row['frame_ids']
                                   if workspace.frames[identifier]['component'] == components}
                self.assertEqual({frame['image'] for frame in selected}, expected_images)
                self.assertTrue(all(frame['id'] in row['frame_ids'] for frame in selected))
        selected_boss = workspace.frames_for('boss-8b-v00')
        selected_ordinary = workspace.frames_for('actor-09-v00')
        self.assertTrue(selected_boss and selected_ordinary)
        self.assertTrue(all(frame['actor_type'] == 9 for frame in selected_boss))
        self.assertTrue({f['id'] for f in selected_boss}.isdisjoint(f['id'] for f in selected_ordinary),
                        'Boss alias pulled unrelated ordinary actor 09 poses')
        self.assertEqual(workspace.frames_for('unknown-profile'), [])

    def test_merge_and_restart_keep_existing_artist_png(self):
        workspace = Workspace(self.folder/'workspace')
        workspace.load_library(self.destination)
        selected = workspace.frames_for('boss-8b-v00')[0]
        artwork = workspace.folder/'artwork'/selected['image']
        with Image.open(artwork) as image:
            edited = image.convert('RGBA')
        edited.putpixel((0, 0), (20, 220, 170, 255))
        edited.save(artwork)
        before = sha(artwork)
        native_before = {p.name: sha(p) for p in (workspace.folder/'references').iterdir()}
        self.assertEqual(workspace.load_library(self.destination), 0)
        self.assertEqual(sha(artwork), before)
        restarted = Workspace(workspace.folder)
        with patch.object(restarted, 'ingest', side_effect=AssertionError('Warm workspace must not rescan captures')):
            self.assertEqual(restarted.load_library(self.destination), 0)
        self.assertEqual(sha(artwork), before)
        self.assertEqual({p.name: sha(p) for p in (workspace.folder/'references').iterdir()}, native_before)
        self.assertTrue(restarted.frames_for('boss-8b-v00'))
        self.assertEqual(restarted.data['library_rom_sha256'], library.ROM_SHA256)

    def test_warm_native_library_cache_never_starts_an_emulator(self):
        raw = (ROOT/'Super Castlevania IV (USA).sfc').read_bytes()
        probe = NativeSession.__new__(NativeSession)
        probe.bytes = raw
        entries = probe.read_catalog()+boss_profiles(probe)
        existing = {row['key']: row for row in self.profiles}
        self.index['profiles'] = []
        for entry in entries:
            key = library.profile_key(entry)
            row = existing.get(key)
            if row is None:
                row = dict(entry, key=key, main_type=entry.get('main_type', entry['type']),
                           frame_ids=[], main_frame_ids=[], child_frame_ids=[], status='missing', captured_fields=1,
                           requested_fields=1, capture_complete=True,
                           coverage_complete=False, coverage_note='Test cache contains only selected recorded profiles.')
            self.index['profiles'].append(row)
        write(self.destination/'library.json', self.index)
        with patch.object(library, 'discover_sources', return_value=[self.normal_subset, self.boss_subset]), \
             patch.object(library.NativeSession, 'start', side_effect=AssertionError('Warm cache started native capture')) as start:
            result = library.build_library(self.destination, fields=1)
        start.assert_not_called()
        self.assertTrue(result['run_complete'])
        self.assertFalse(result['coverage_complete'])
        self.assertFalse(result['summary']['coverage_complete'])
        self.assertEqual({row['key'] for row in result['profiles'] if not row.get('preview_only')}, {library.profile_key(entry) for entry in entries})

    def test_cancelled_profile_keeps_real_field_count_and_is_not_a_warm_cache_hit(self):
        """Replay real recorded actor fields, with native boot deliberately stubbed.

        This is a cancellation/cache-state test, not evidence of a new game run.
        The source PNGs and snapshots themselves are existing native captures.
        """
        source_session = ROOT/'artwork-local/enemy-workshop/session-ie7cbyp8'
        recording = read(source_session/'native-actions.json')[0]['frames']
        source = source_session/'enemy_packs/native-template'
        raw = (ROOT/'Super Castlevania IV (USA).sfc').read_bytes()
        probe = NativeSession.__new__(NativeSession)
        probe.bytes = raw
        entry = next(e for e in probe.read_catalog() if e['type'] == 18 and e['variant'] == 0)
        counters = {'starts': 0, 'fields': 0}

        class RecordedSession(NativeSession):
            def __init__(self, rom=None, build=None, folder=None):
                self.folder = Path(folder)
                shutil.copytree(source, self.references)

            def read_catalog(self):
                return [copy.deepcopy(entry)]

            def start(self):
                counters['starts'] += 1
                return self

            def command(self, name, arg=''):
                # Context byte inspection is unrelated to cancellation; give
                # the builder private harmless placeholders instead of booting.
                if name in ('dump', 'lines'):
                    Path(arg).write_bytes(bytes(64))
                return True

            def read(self, address):
                return 0

            def spawn(self, entry, count=1):
                return copy.deepcopy(recording[0])

            def action(self, action):
                pass

            def step(self, frames=1):
                snapshot = copy.deepcopy(recording[counters['fields']%len(recording)])
                counters['fields'] += frames
                return snapshot

            def close(self):
                pass

        target = self.folder/'cancel-library'
        with patch.object(library, 'NativeSession', RecordedSession), \
             patch.object(library, 'discover_sources', return_value=[source]), \
             patch('enemy_catalog_profiles.boss_profiles', return_value=[]):
            result = library.build_library(target, fields=240, cancelled=lambda: counters['fields'] >= 1)
            row = result['profiles'][0]
            self.assertEqual(row['captured_fields'], 1, 'Cancelled one-field capture was inflated to the requested count')
            self.assertFalse(row['capture_complete'])
            self.assertEqual(row['status'], 'cancelled')
            self.assertFalse(result['run_complete'])
            library.build_library(target, fields=240, cancelled=lambda: counters['fields'] >= 2)
        self.assertEqual(counters['starts'], 2, 'Interrupted profile was incorrectly reused as a finished warm cache')
        self.assertEqual(counters['fields'], 2)

    def test_default_library_reports_profile_and_animation_limits_honestly(self):
        path = CONFIG['library']
        index = library.load_library(path)
        self.assertTrue(index.get('profiles'), 'The real prefilled library has no profile index yet')
        self.assertFalse(index.get('coverage_complete', True), 'Bounded captures must not claim all game animations complete')
        self.assertTrue(index.get('coverage_note'))
        self.assertEqual(index['rom_sha256'], library.ROM_SHA256)
        frames = {frame['id']: frame for frame in read(path/'native-template/enemies.json')['frames']}
        keys = [row['key'] for row in index['profiles']]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn('boss-8b-v00', keys)
        for row in index['profiles']:
            self.assertFalse(row.get('coverage_complete', True), row['key'])
            self.assertTrue(row.get('coverage_note'), row['key'])
            self.assertTrue(set(row.get('frame_ids', [])) <= frames.keys(), row['key'])
            self.assertEqual(set(row.get('frame_ids', [])),
                             set(row.get('main_frame_ids', [])) | set(row.get('child_frame_ids', [])) |
                             set(row.get('template_frame_ids', [])) | set(row.get('rom_frame_ids', [])), row['key'])
            if row['status'] == 'captured':
                self.assertTrue(row.get('main_frame_ids'), 'Only children visible must not mark the boss body captured')
            if row['key'] == 'boss-8b-v00' and row.get('main_frame_ids'):
                self.assertTrue(all(frames[identifier]['actor_type'] == 9 for identifier in row['main_frame_ids']))
        write(self.folder/'coverage-snapshot.json', {'profile_count': len(keys), 'frame_count': len(frames),
              'statuses': {status: sum(p['status'] == status for p in index['profiles']) for status in {p['status'] for p in index['profiles']}},
              'coverage_complete': False, 'run_complete': index.get('run_complete', False)})

    def test_real_prefilled_profile_pngs_keep_declared_source_bytes(self):
        path = CONFIG['library']
        index = library.load_library(path)
        identifiers = {identifier for row in index['profiles'] for identifier in row.get('frame_ids', [])}
        self.assertTrue(identifiers, 'No prefilled profile PNGs are available')
        origins = {}
        for directory in index.get('sources', []):
            source = Path(directory)
            manifest_path = source/'enemies.json'
            if not manifest_path.is_file():
                continue
            for frame in read(manifest_path).get('frames', []):
                if frame['id'] not in identifiers:
                    continue
                original = source/frame['reference']
                if original.is_file():
                    origins.setdefault(frame['id'], set()).add(sha(original))
        native = path/'native-template'
        frames = {frame['id']: frame for frame in read(native/'enemies.json')['frames']}
        for identifier in identifiers:
            image = native/frames[identifier]['reference']
            self.assertTrue(image.is_file(), identifier)
            if frames[identifier].get('source_kind')=='rom_pose':
                self.assertTrue(frames[identifier].get('graphics_context'))
                self.assertFalse(frames[identifier].get('native_motion_observed',True))
                continue
            self.assertIn(sha(image), origins.get(identifier, set()),
                          f'{identifier}: library PNG differs from every declared original source')
        write(self.folder/'source-provenance-summary.json', {'profile_png_ids_checked': len(identifiers),
              'declared_sources': len(index.get('sources', [])), 'byte_identity': True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, default=ROOT/'artwork-local/enemy-library')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    parent = ROOT/'artwork-local/enemy-workshop'
    if args.out:
        args.out.mkdir(parents=True, exist_ok=False)
        output = args.out.resolve()
    else:
        output = Path(tempfile.mkdtemp(prefix='library-check-', dir=parent)).resolve()
    CONFIG.update(out=output, library=args.library.resolve())
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LibraryTests))
    report = {'passed': result.wasSuccessful(), 'tests': result.testsRun, 'artifacts': str(output),
              'source_data': 'Actual captured catalog PNGs and native boss 8B actor-09 PNGs',
              'player_data_modified': False, 'new_emulator_capture': False,
              'failures': [{'test': str(test), 'details': details} for test, details in result.errors+result.failures]}
    write(output/'report.json', report)
    print(json.dumps({'passed': report['passed'], 'tests': report['tests'], 'artifacts': str(output)}))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
