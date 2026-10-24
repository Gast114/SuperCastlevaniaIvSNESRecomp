"""Independent tests for 256px whole/part workshop artwork and native fallback."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

def main():
    parent=ROOT/'artwork-local/enemy-workshop-review';parent.mkdir(exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='large-render-',dir=parent))
    exe=work/'probe.exe'
    subprocess.run([shutil.which('clang++'),'-std=c++17',str(ROOT/'tools/enemy_workshop_render_probe.cpp'),str(ROOT/'src/enemy_pack.cpp'),
                    '-I',str(ROOT/'src'),'-I',str(ROOT/'snesrecomp/runner/src'),'-I',str(ROOT/'recomp-ui/src'),'-o',str(exe)],check=True,capture_output=True)
    first=subprocess.run([str(exe)],cwd=work,check=True,capture_output=True,text=True).stdout
    refs=work/'enemy_packs/native-template';data=json.loads((refs/'enemies.json').read_text())
    assert len(data['frames'])==3 and all(f['display_size']==[256,256] for f in data['frames'])
    whole=next(f for f in data['frames'] if '__teil-' not in f['id'])
    piece=next(f for f in data['frames'] if f['id'].endswith('__teil-0'))
    for name,frames in [('large',[whole]),('part',[piece]),('combined',[whole,piece])]:
        dest=work/'enemy_packs'/name;dest.mkdir();mapped=[]
        for frame in frames:
            with Image.open(refs/frame['reference']) as image:image.resize((1032,1032),Image.Resampling.NEAREST).save(dest/frame['reference'])
            mapped.append(dict(frame,image=frame['reference']))
        (dest/'enemies.json').write_text(json.dumps({'version':1,'frames':mapped}))
    checks=subprocess.run([str(exe),'verify'],cwd=work,check=True,capture_output=True,text=True).stdout
    edge_dir=work/'edge-cases';edge_dir.mkdir()
    checks+=subprocess.run([str(exe),'edges'],cwd=edge_dir,check=True,capture_output=True,text=True).stdout
    (work/'report.json').write_text(json.dumps({'passed':True,'real_game_coverage':False,'checks':(first+checks).splitlines()},indent=2)+'\n')
    print(work);print(first+checks)

if __name__=='__main__':main()
