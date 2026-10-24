"""Compare static original-pose export with the real C++ reference capture."""
import json
from pathlib import Path
import tempfile
from PIL import Image
from enemy_workshop_native import NativeSession,ROOT
from enemy_sprite_export import render_pose


def main():
    folder=Path(tempfile.mkdtemp(prefix='pose-export-',dir=ROOT/'artwork-local/enemy-workshop'))
    session=NativeSession(folder=folder/'game');results=[]
    try:
        session.start()
        for actor_type in (7,18,0x85):
            session.command('enemy','capture off')
            entry=next(e for e in session.catalog if e['type']==actor_type and not e['variant'])
            snapshot=session.spawn(entry)
            if actor_type==18:session.action('Werfen')
            session.step(24)
            # Capture this exact field's palette, rather than comparing a
            # later boss palette against an earlier fading-room reference.
            session.command('enemy','capture on')
            for _ in range(24):
                snapshot=session.step(1)
                actor=next((a for a in snapshot['actors'] if a['type']==actor_type),None)
                if actor:break
            assert actor is not None,f'No original actor {actor_type:02X}'
            video=folder/f'{actor_type:02x}-video.bin';lines=folder/f'{actor_type:02x}-lines.bin'
            session.command('dump',video);session.command('lines',lines);session.command('enemy','flush')
            exported=render_pose(session.bytes,actor_type,actor['pose'],video.read_bytes(),lines.read_bytes()[34],
                                 session.read(actor['slot']+0x26),session.read(actor['slot']+2))
            assert exported[0][0]['id']==actor['id'],(exported[0][0]['id'],actor['id'])
            assert {frame['id'] for frame,_ in exported}=={actor['id'],*[p['id'] for p in actor['parts']]}
            for frame,image in exported:
                with Image.open(session.references/frame['reference']) as native:
                    assert image.size==native.size
                    assert image.tobytes()==native.convert('RGBA').tobytes(),f'Original pixels differ: {frame["id"]}'
            results.append({'type':actor_type,'pose':actor['pose'],'images':len(exported),'ids_and_rgba_equal':True})
    finally:session.close()
    (folder/'report.json').write_text(json.dumps({'passed':True,'native_comparison':results},indent=2))
    print(folder)
    print('PASS: native actor IDs, whole-pose pixels and every original part match the independent C++ capture')


if __name__=='__main__':main()
