"""Exercise exact OAM matching on stairs without modifying user artwork."""
import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
import shutil
from PIL import Image

import sciv_test_support as sciv

p=argparse.ArgumentParser()
p.add_argument('--rom', required=True)
p.add_argument('--script',default='character_stairs_smoke.input')
p.add_argument('--frames',type=int,default=1850)
p.add_argument('--screenshot',type=int,default=1400)
sciv.add_build_arg(p)
args=p.parse_args()
build=sciv.build_dir(args)
work=sciv.work_dir(build,'stairs-check-')
# Collect the poses from the same scripted route, so the recoloured pack
# covers every pose the replay shows.
template=sciv.capture_template(build,args.rom,work,args.script,args.frames,
                               {'Graphics':{'Widescreen':1}})
starter=sciv.recolored_copy(template,work/'starter-character')

def run(name):
    folder=work/name
    sciv.prepare(folder,build,{'Graphics':{'Widescreen':1}})
    shutil.copytree(template,folder/'characters/simon-template')
    shutil.copytree(starter if name=='edited' else template,folder/'characters/test-pack')
    (folder/'characters/selected.txt').write_text('' if name=='baseline' else 'test-pack')
    sciv.run(folder,args.script,args.rom,sciv.clean_env(
        SNESRECOMP_RUN_FRAMES=args.frames,SNESRECOMP_CHARACTER_TRACE=1,
        SNESRECOMP_CHARACTER_DIAG=1,SNESRECOMP_SCREENSHOT_FRAME=args.screenshot,
        SNESRECOMP_SCREENSHOT=folder/'game.ppm',SNESRECOMP_PRESENT_LOG=folder/'frames.csv'),timeout=160)
    Image.open(folder/'game.ppm').save(folder/'game.png')
    rows=[line for line in (folder/'game.log').read_text().splitlines() if line.startswith('[character_frame]')]
    print(name, 'frames',len(rows),'unmatched',sum('matched=0' in x for x in rows),
          'replaced',sum('replaced=1' in x for x in rows),flush=True)

with ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(run,['baseline','native','edited']))

def checksums(name):
    with (work/name/'frames.csv').open() as f:
        return [(r['frame'],r['crc32']) for r in csv.DictReader(f)]

baseline=checksums('baseline')
assert len(baseline)==args.frames, 'Incomplete capture'
assert baseline==checksums('native'), 'Full-frame rendering changed native artwork'
movement=[line for line in (work/'edited/game.log').read_text().splitlines()
          if line.startswith('[character_frame]') and int(line.split()[1])>=1100]
assert len(movement)==args.frames-1099, 'Incomplete movement trace'
assert all('replaced=1' in line for line in movement), 'Replacement dropped out during movement'
if args.script=='character_top_edge_smoke.input':
    clipped=[line for line in (work/'edited/game.log').read_text().splitlines()
             if line.startswith('[character_frame]') and 'clipped=1' in line]
    assert clipped and all('replaced=1' in line for line in clipped), 'Top-edge replacement not covered'
    assert any('id=a32c-' in line for line in clipped), 'Airborne attack did not cross the top edge'
    print(f'PASS: {len(clipped)} edge-clipped frames replaced',flush=True)
print(f'PASS: {len(baseline)} native frames identical; {len(movement)} movement frames replaced without dropouts',flush=True)
