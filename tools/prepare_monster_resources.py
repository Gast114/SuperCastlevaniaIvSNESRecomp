"""Prepare portable palettes once; normal graphics load directly from ROM.

Existing measured contexts need no emulator. Profiles without a measured
palette use a one-time original-context extraction, never the live spawn path.
"""
import argparse
import hashlib
import json
from pathlib import Path
from enemy_resources import RESOURCE_VERSION,ROM_SHA256
from enemy_workshop_library import DEFAULT_LIBRARY,load_library,profile_key
from enemy_workshop_native import NativeSession


def prepare(library=DEFAULT_LIBRARY):
    library=Path(library);index=load_library(library);folder=library/'resources';folder.mkdir(exist_ok=True)
    if index.get('rom_sha256')!=ROM_SHA256:raise ValueError('Originalfarben gehören zu einer anderen ROM.')
    manifest=folder/'palettes.json'
    previous=json.loads(manifest.read_text()) if manifest.is_file() else {}
    rows={p['key']:p for p in previous.get('profiles',[])} if previous.get('version')==RESOURCE_VERSION and previous.get('rom_sha256')==ROM_SHA256 else {}
    result=[];session=None
    try:
        for profile in index['profiles']:
            if profile.get('preview_only'):continue
            key=profile_key(profile);path=folder/f'{key}-palette.bin';context=profile.get('context')
            if context:
                data=Path(context['video']).read_bytes()[0x10000:0x10200];source=context['video']
            elif key in rows and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==rows[key]['sha256']:
                result.append(rows[key]);continue
            elif not profile.get('boss'):
                continue  # No playable/renderable context proved for this helper.
            else:
                print(f'Einmalig Originalfarben vorbereiten: {key}',flush=True)
                if session is None:session=NativeSession();session.start();session.command('enemy','capture off')
                entry=next(e for e in session.catalog if profile_key(e)==key)
                session.spawn(entry);session.step(2)
                video=folder/f'{key}-palette-source.bin';session.command('dump',video)
                data=video.read_bytes()[0x10000:0x10200];source=str(video)
            if len(data)!=512:raise ValueError('Unvollständige Originalpalette: '+key)
            if not path.exists() or path.read_bytes()!=data:path.write_bytes(data)
            result.append(dict(key=key,sha256=hashlib.sha256(data).hexdigest(),source=source))
        manifest.write_text(json.dumps(dict(version=RESOURCE_VERSION,rom_sha256=ROM_SHA256,profiles=result),indent=2))
    finally:
        if session:session.close()
    print(f'{len(result)} Farbressourcen vorbereitet; keine Herkunftslevel beim Spawnen nötig.',flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--library',type=Path,default=DEFAULT_LIBRARY)
    parser.add_argument('--ensure',action='store_true');args=parser.parse_args();prepare(args.library)
