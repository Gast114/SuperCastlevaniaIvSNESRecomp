"""Actual neutral native spawns, with source-level loading explicitly forbidden."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
from PIL import Image
from enemy_workshop_native import NativeSession,ROOT
from monster_model import definitions
from enemy_resources import ordinary_plan,palette,write_bundle


def check(types=None,fields=96,boss_fields=240):
    folder=Path(tempfile.mkdtemp(prefix='neutral-check-',dir=ROOT/'artwork-local/enemy-workshop'))
    session=NativeSession(folder=folder/'game');session.arena_enabled=True
    report=dict(images_opened=False,source_level_loads=0,profiles=[],failures=[])
    try:
        session.start();native_write=session.write;native_command=session.command
        def forbid_original(*args,**kwargs):raise AssertionError('Neutral spawn called original-room loader')
        session._spawn_original=forbid_original
        def write(values):
            if 0x86 in values and values[0x86]!=0:raise AssertionError('Source room selected')
            if 0x70 in values and values[0x70]!=5:raise AssertionError('Native level load requested')
            return native_write(values)
        def command(name,arg=''):
            if name in ('load','reset'):raise AssertionError('Unexpected reset/source save load')
            if name=='loadfile' and Path(arg).resolve()!=session.base.resolve():raise AssertionError('Source-room snapshot restored')
            return native_command(name,arg)
        session.write=write;session.command=command
        # A malformed later block must not apply the preceding valid block.
        before=folder/'before.bin';after=folder/'after.bin';session.command('dump',before)
        bad=folder/'bad-resource.bin'
        bad.write_bytes(b'CV4OBJ1\0'+struct.pack('<HHHHH',0,2,0x6a00,2,0x1234)+struct.pack('<HH',0x100,2)+b'\0'*258)
        try:session.command('enemy_resources',bad)
        except RuntimeError:pass
        session.command('dump',after)
        assert before.read_bytes()==after.read_bytes(),'Rejected bundle changed PPU memory'
        report['atomic_rejection']=True
        entry=next(e for e in session.catalog if e['type']==18 and e['variant']==0)
        plan=ordinary_plan(session.bytes,entry);colors=palette(session.resource_library,entry)
        valid=write_bundle(folder/'valid-resource.bin',colors,plan)
        session.command('enemy_resources',valid);session.command('dump',after)
        original=before.read_bytes();installed=after.read_bytes();expected=bytearray(original)
        for block in plan['blocks']:
            start=block['vram_word']*2;expected[start:start+len(block['data'])]=block['data']
        expected[0x10100:0x10200]=colors[256:]
        assert bytes(expected)==installed,'Import modified data outside declared OBJ/palette spans'
        shadow=session.read(0x48)
        checksum=int(session.lua.eval(f'local s=0 for i=0,255 do s=s+mainmemory.read_u8({shadow+256}+i)*(i+1) end return s')['values'][0])
        assert checksum==sum(v*(i+1) for i,v in enumerate(colors[256:])), 'Native palette shadow not updated'
        report['graphics_only_import']=True
        monsters=definitions(session.catalog,session.bytes)
        for monster in monsters:
            if types and monster['type'] not in types:continue
            entry=monster['variants'][0];samples=[];length=boss_fields if entry.get('boss') else fields
            try:
                snapshot=session.spawn(entry)
                for n in range(0,length,4):
                    if n:snapshot=session.step(4)
                    surface=0;surface_hash=None
                    if snapshot.get('boss_surface'):
                        raw=base64.b64decode(snapshot['boss_surface']);surface_hash=hashlib.sha256(raw).hexdigest()
                        with Image.open(io.BytesIO(raw)) as image:surface=sum(image.getchannel('A').histogram()[1:])
                    globals_=list(map(int,session.lua.eval('return mainmemory.read_u16_le(0x70),mainmemory.read_u16_le(0x86),mainmemory.read_u16_le(0x13f4)')['values']))
                    samples.append(dict(field=n,live=snapshot['live_stats'],actors=snapshot['actors'],globals=globals_,
                                        surface_opaque=surface,surface_hash=surface_hash))
                main=entry.get('main_type',entry['type'])
                visible=sum(any(a['type']==main for a in s['actors']) or s['surface_opaque']>0 for s in samples)
                result=dict(code=monster['code'],boss=monster['boss'],visible_samples=visible,total_samples=len(samples),
                            poses=len({a['id'] for s in samples for a in s['actors']}),
                            states=sorted({s['live'].get('state') for s in samples}),
                            rooms=sorted({s['globals'][1] for s in samples}),phases=sorted({s['globals'][0] for s in samples}),
                            mode7_frames=len({s['surface_hash'] for s in samples if s['surface_opaque']}),failures=[])
                if not visible:result['failures'].append('No exact native main-body match')
                if result['rooms']!=[0] or result['phases']!=[5]:result['failures'].append('Unexpected neutral-room transition')
                if any(s['globals'][2]!=16 for s in samples):result['failures'].append('Target lost health')
                if any(not s['live'].get('neutral') for s in samples):result['failures'].append('Native neutral path not used')
                if entry['type']==0x81 and not result['mode7_frames']:result['failures'].append('Missing Mode7 body')
                (folder/f'{entry["type"]:02x}.json').write_text(json.dumps(dict(entry=entry,samples=samples),indent=2))
            except Exception as exc:result=dict(code=monster['code'],boss=monster['boss'],failures=[f'{type(exc).__name__}: {exc}'])
            report['profiles'].append(result);report['failures'].extend(f'{monster["code"]}: {f}' for f in result['failures'])
            (folder/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(result),flush=True)
    finally:session.close()
    report['passed']=not report['failures'];(folder/'report.json').write_text(json.dumps(report,indent=2))
    print(folder,flush=True);return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--types')
    parser.add_argument('--fields',type=int,default=96);parser.add_argument('--boss-fields',type=int,default=240);args=parser.parse_args()
    result=check([int(t,16) for t in args.types.split(',')] if args.types else None,args.fields,args.boss_fields)
    raise SystemExit(0 if result['passed'] else 1)
