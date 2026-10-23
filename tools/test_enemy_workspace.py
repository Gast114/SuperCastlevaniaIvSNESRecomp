"""Check enlarged redesign templates and direct, unchanged PNG import."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageDraw
import enemy_hd


class EnemyWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='sciv-enemy-workspace-')
        self.root=Path(self.temp.name)
        self.source=self.root/'captured';self.source.mkdir()
        frames=[]
        for step in range(2):
            image=Image.new('RGBA',(96,96))
            ImageDraw.Draw(image).rectangle((36+step,27,55,72),fill=(190,180,140,255))
            image.save(self.source/f'step-{step}.png')
            for actor in (17,18):
                frames.append({'id':f'type-{actor}-pose-{step}','actor_type':actor,
                               'pose':35572+step,'reference':f'step-{step}.png',
                               'display_size':[96,96],'anchor':[48,48]})
        (self.source/'enemies.json').write_text(json.dumps({'version':1,'frames':frames}))

    def tearDown(self):
        self.temp.cleanup()

    def test_ready_templates_do_not_count_as_redesigns(self):
        project=self.root/'ready'
        self.assertEqual(enemy_hd.prepare(self.source,project,387),4)
        self.assertEqual(len(list((project/'artwork').glob('*.png'))),2)
        for path in (project/'artwork').glob('*.png'):
            with Image.open(path) as image:
                self.assertEqual(image.size,(387,387));self.assertEqual(image.mode,'RGBA')
        self.assertTrue((project/'VORLAGEN.html').is_file())
        with self.assertRaisesRegex(ValueError,'No changed artwork'):
            enemy_hd.pack(project,self.root/'untouched')
        self.assertFalse((self.root/'untouched').exists())

    def test_one_redesign_maps_both_planes_and_keeps_exact_png(self):
        project=self.root/'ready';enemy_hd.prepare(self.source,project,387)
        image_path=project/'artwork/Skelett_Schritt_01.png'
        with Image.open(image_path) as image:
            image.putpixel((160,160),(70,90,110,255));image.save(image_path)
        checksum=hashlib.sha256(image_path.read_bytes()).hexdigest()
        output=self.root/'pack'
        self.assertEqual(enemy_hd.pack(project,output),2)
        manifest=json.loads((output/'enemies.json').read_text())
        self.assertEqual({f['actor_type'] for f in manifest['frames']},{17,18})
        self.assertTrue(all(f['display_size']==[96,96] and f['anchor']==[48,48] for f in manifest['frames']))
        self.assertEqual(hashlib.sha256((output/image_path.name).read_bytes()).hexdigest(),checksum)
        self.assertEqual(len(list(output.glob('*.png'))),1)


if __name__=='__main__':
    unittest.main()
