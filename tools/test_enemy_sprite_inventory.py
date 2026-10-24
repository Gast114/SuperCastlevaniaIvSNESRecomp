"""Check retail pose ownership, bounded tables and metadata-only inventory."""
import json
from pathlib import Path
import unittest
import enemy_sprite_inventory as inv


class NativeSpriteInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom=(inv.ROOT/'Super Castlevania IV (USA).sfc').read_bytes()
        cls.data=inv.inventory(cls.rom,actors=[2,0x11,0x12,0x31,0x56,0x69,0x81,0x82,0x8d])
        cls.actors={r['type']:r for r in cls.data['actors']}

    def test_shared_skeleton_dispatch_does_not_mix_actor_designs(self):
        self.assertEqual(self.actors[0x11]['poses'],[0x8af4,0x8b05])
        self.assertEqual(self.actors[0x12]['poses'],[0x8af4,0x8b05,0x8b1b,0x8b30,0x8b4d])
        self.assertTrue(set(self.actors[0x31]['poses']).isdisjoint(self.actors[0x11]['poses']))
        self.assertTrue({0x919d,0x91ba}.issubset(self.actors[0x56]['poses']))

    def test_projectile_code_in_bank0c_and_all_three_rotations(self):
        bone=self.actors[2]
        self.assertEqual(bone['handler'],0x0cfddd)
        self.assertTrue({0x900c,0x9011,0x9016}.issubset(bone['poses']))
        for frame in bone['direct_poses']:
            if frame['pose'] in (0x900c,0x9011,0x9016):
                self.assertTrue(all(0x0c0000<=e['instruction']<0x0d0000 for e in frame['evidence']))

    def test_retail_animation_durations_and_loop_terminator(self):
        animation=inv.parse_animation(self.rom,0x01b30f)
        self.assertIsNotNone(animation)
        self.assertEqual([f['duration'] for f in animation['frames']],[10,10,12,10,10])
        self.assertEqual([f['pose'] for f in animation['frames']],
                         [0x93f0,0x9409,0x9426,0x93f0,0x93f0])
        self.assertTrue(animation['loop'])

    def test_invalid_table_does_not_become_an_animation(self):
        damaged=bytearray(self.rom)
        damaged[inv.offset(0x01b30f)+2:inv.offset(0x01b30f)+4]=b'\0\0'
        self.assertIsNone(inv.parse_animation(damaged,0x01b30f))
        with self.assertRaises(ValueError):inv.inventory(damaged,actors=[0x31])

    def test_every_pose_has_native_producer_evidence(self):
        for actor in self.data['actors']:
            self.assertEqual(set(actor['poses']),{f['pose'] for f in actor['direct_poses']})
            for frame in actor['direct_poses']:
                self.assertTrue(frame['evidence'])
                self.assertIsNotNone(inv.parse_metasprite(self.rom,frame['pose']))
                for evidence in frame['evidence']:self.assertGreaterEqual(evidence['instruction']&0xffff,0x8000)

    def test_special_bosses_are_not_claimed_as_complete_obj_bodies(self):
        special=self.data['special_rendering']
        self.assertEqual(special['81']['kind'],'BG/Mode7')
        self.assertFalse(special['81']['main_actor_metasprite'])
        self.assertFalse(special['82']['standalone_profile'])
        self.assertFalse(special['8D']['standalone_profile'])
        self.assertTrue(self.data['metadata_only'])
        self.assertNotIn('image_data',json.dumps(self.data))


if __name__=='__main__':unittest.main()
