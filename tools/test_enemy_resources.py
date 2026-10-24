"""Check ROM-direct graphics against independent, previously captured VRAM."""
import json
import hashlib
import io
from contextlib import redirect_stdout
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from enemy_resources import decompress,ordinary_plan,resource,write_bundle
from enemy_resources import RESOURCE_VERSION,ROM_SHA256
from enemy_workshop_native import ROOT


class Resources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom=(ROOT/'Super Castlevania IV (USA).sfc').read_bytes()
        cls.index=json.loads((ROOT/'artwork-local/enemy-library/library.json').read_text())

    def test_direct_rom_decode_matches_original_native_vram(self):
        for actor in (7,17,18,49,86,105,127):
            with self.subTest(actor=actor):
                profile=next(p for p in self.index['profiles'] if p['type']==actor and not p.get('variant'))
                context=profile['context'];video=Path(context['video']).read_bytes()
                pointer,pages=resource(self.rom,actor);data=decompress(self.rom,pointer)
                start=(0x6000+context['tile_add']*16)*2;length=min(len(data),pages*1024)
                self.assertEqual(data[:length],video[start:start+length])

    def test_shared_variants_reserve_the_native_declared_prefix(self):
        plans=[ordinary_plan(self.rom,dict(type=t)) for t in (17,18,86)]
        self.assertEqual([p['pages'] for p in plans],[2,3,4])
        self.assertEqual(plans[0]['blocks'][0]['data'],plans[1]['blocks'][0]['data'][:2048])
        self.assertEqual(plans[1]['blocks'][0]['data'],plans[2]['blocks'][0]['data'][:3072])
        family=ordinary_plan(self.rom,dict(type=18,child_types=[17,86,2,45]))
        self.assertEqual(len(family['blocks']),1);self.assertEqual(family['pages'],4)
        self.assertEqual({family['tile_add'][t] for t in (17,18,86)},{0xa0})
        self.assertNotIn(2,family['tile_add'])  # fixed common-effect graphics

    def test_multiple_resource_reservations_do_not_overlap(self):
        plan=ordinary_plan(self.rom,dict(type=7,child_types=[18,49]))
        occupied=set()
        for block in plan['blocks']:
            addresses=set(range(block['vram_word'],block['vram_word']+len(block['data'])//2))
            self.assertFalse(occupied&addresses);occupied.update(addresses)
        self.assertGreaterEqual(min(occupied),0x6a00);self.assertLess(max(occupied),0x8000)
        self.assertEqual(len(plan['blocks']),3)
        shifted=ordinary_plan(self.rom,dict(type=7),first_slot=8)
        self.assertEqual(shifted['tile_add'][7],0x1a0)
        with self.assertRaises(ValueError):ordinary_plan(self.rom,dict(type=18),first_slot=10)

    def test_bad_rom_streams_are_bounded(self):
        with self.assertRaises(ValueError):decompress(self.rom,0x1000)
        with self.assertRaises(ValueError):decompress(self.rom,resource(self.rom,18)[0],limit=8)
        bad=bytearray(self.rom);bad[0:3]=b'\x03\x00\x01'
        with self.assertRaises(ValueError):decompress(bad,0x008000)

    def test_bundle_contains_graphics_and_palette_only(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'resource.bin';colors=bytes(range(256))*2
            write_bundle(path,colors,ordinary_plan(self.rom,dict(type=7)))
            data=path.read_bytes();self.assertEqual(data[:8],b'CV4OBJ1\0')
            self.assertEqual(struct.unpack_from('<HHHH',data,8),(0,1,0x6a00,1024))
            self.assertEqual(data[-256:],colors[256:]);self.assertEqual(len(data),16+1024+256)
            write_bundle(path,colors,full_palette=True)
            self.assertEqual(path.read_bytes(),b'CV4OBJ1\0'+struct.pack('<HH',1,0)+colors)

    def test_prepared_boss_palette_never_boots_a_source_level(self):
        from prepare_monster_resources import prepare
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'resources').mkdir();key='boss-81-v00'
            data=bytes(range(256))*2;path=root/'resources'/f'{key}-palette.bin';path.write_bytes(data)
            (root/'library.json').write_text(json.dumps(dict(rom_sha256=ROM_SHA256,profiles=[dict(key=key,type=129,boss=True)])))
            (root/'resources/palettes.json').write_text(json.dumps(dict(version=RESOURCE_VERSION,rom_sha256=ROM_SHA256,
                profiles=[dict(key=key,sha256=hashlib.sha256(data).hexdigest(),source='recorded original palette')])))
            with patch('prepare_monster_resources.NativeSession.start',side_effect=AssertionError('Source scene booted')) as start,redirect_stdout(io.StringIO()):
                rows=prepare(root)
            start.assert_not_called();self.assertEqual(len(rows),1);self.assertEqual(path.read_bytes(),data)


if __name__=='__main__':unittest.main(verbosity=2)
