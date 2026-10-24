"""Verified quest/room balance and future override precedence; no images."""
import copy
from pathlib import Path
import unittest
from monster_balance import original_stats,resolve_mode


class BalanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.rom=(Path(__file__).resolve().parents[1]/'Super Castlevania IV (USA).sfc').read_bytes()
    def test_first_room_normal_and_second_quest(self):
        e={'type':18,'room':1}
        normal=original_stats(self.rom,e);hard=original_stats(self.rom,e,'new_game_plus')
        self.assertEqual((normal['hp'],hard['hp']),(48,64))
        self.assertEqual((normal['contact_damage'],hard['contact_damage']),(3,3))
    def test_late_room_bonus_and_cap(self):
        e={'type':0x6b,'room':45}
        self.assertEqual(original_stats(self.rom,e)['hp'],64)
        self.assertEqual(original_stats(self.rom,e,'new_game_plus')['hp'],80)
        self.assertEqual(original_stats(self.rom,{'type':0x46,'room':45},'new_game_plus')['hp'],32767)
    def test_unknown_boss_hp_is_not_invented(self):
        e={'type':0x8b,'boss':True,'main_type':9,'room':65}
        for p in ('normal','new_game_plus'):
            self.assertIsNone(original_stats(self.rom,e,p)['hp'])
            self.assertIsNone(original_stats(self.rom,e,p)['contact_damage'])
    def test_future_mode_keeps_originals_and_applies_only_target_code(self):
        e={'type':18,'room':1}
        mode={'version':1,'name':'Mein Modus','base_profile':'new_game_plus','overrides':{'M-0012':{'hp':80,'contact_damage':4}}}
        saved=copy.deepcopy(mode);result=resolve_mode(self.rom,e,mode)
        self.assertEqual(result['original']['hp'],64)
        self.assertEqual(result['effective']['hp'],80)
        self.assertEqual(result['effective']['contact_damage'],4)
        self.assertEqual(mode,saved)
        other=resolve_mode(self.rom,{'type':17,'room':1},mode)
        self.assertEqual(other['effective'],other['original'])
        self.assertFalse(other['overridden_fields'])
        result['effective']['evidence']['hp']='test'
        self.assertNotEqual(result['original']['evidence']['hp'],'test')
    def test_bad_modes_fail_without_silent_coercion(self):
        e={'type':18,'room':1};template={'version':1,'base_profile':'normal','overrides':{}}
        bad=[[],{},dict(template,version=True),dict(template,base_profile=[]),dict(template,extra=1)]
        for key,value in (('hp',32768),('hp',True),('hp',1.5),('contact_damage',-1),('speed',3)):
            bad.append(dict(template,overrides={'M-0012':{key:value}}))
        bad.extend(dict(template,overrides={key:{'hp':80}}) for key in ('M-00ff','M-0000','M-1000','other'))
        for mode in bad:
            with self.subTest(mode=mode),self.assertRaises(ValueError):resolve_mode(self.rom,e,mode)
        with self.assertRaises(ValueError):original_stats(self.rom,e,room=68)


if __name__=='__main__':unittest.main()
