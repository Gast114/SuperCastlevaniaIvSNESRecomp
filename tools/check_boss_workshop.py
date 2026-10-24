"""Record boss stability/visibility from native RAM and OAM, without screenshots."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import tempfile
from PIL import Image
from enemy_workshop_native import NativeSession,ROOT


def raw_actors(session):
    chunks=session.lua.eval('local chunks={} for first=0x580,0xebf,0x200 do local t={} for a=first,math.min(first+0x1c0,0xebf),0x40 do '
        'local id=mainmemory.read_u16_le(a+0x10) if id~=0 then '
        't[#t+1]=string.format("%d,%d,%d,%d,%d,%d,%d",a,id,'
        'mainmemory.read_u16_le(a),mainmemory.read_u16_le(a+0x12),'
        'mainmemory.read_u16_le(a+0xa),mainmemory.read_u16_le(a+0xe),'
        'mainmemory.read_u16_le(a+6)) end end chunks[#chunks+1]=table.concat(t,";") end return table.unpack(chunks)')['values']
    return [dict(zip(('slot','type','pose','state','x','y','hp'),map(int,row.split(',')))) for value in chunks for row in value.split(';') if row]


def summarize(entry,samples,fields):
    main_type=entry.get('main_type',entry['type'])
    mains=[a for sample in samples for a in sample['raw'] if a['type']==main_type and a['slot']==entry['main_slot']]
    visible=sum(any(a['type']==main_type for a in sample['observed']) or sample['surface_opaque']>0 for sample in samples)
    result=dict(type=entry['type'],visible_samples=visible,total_samples=len(samples),
        group_visible_samples=sum(bool(s['observed']) or s['surface_opaque']>0 for s in samples),
        raw_states=sorted({a['state'] for a in mains}),poses=len({a['id'] for sample in samples for a in sample['observed']}),
        x_range=[min(a['x'] for a in mains),max(a['x'] for a in mains)] if mains else None,
        y_range=[min(a['y'] for a in mains),max(a['y'] for a in mains)] if mains else None,
        phases=sorted({s['globals'][0] for s in samples}),rooms=sorted({s['globals'][1] for s in samples}),
        surface_frames=len({s['surface_hash'] for s in samples if s['surface_opaque']}))
    failures=[]
    if result['phases']!=[5] or result['rooms']!=[entry['room']]:failures.append('Unexpected room transition')
    if not mains:failures.append('Native main slot never present')
    if not visible:failures.append('Native boss body never observed')
    if fields>=120 and result['poses']<2:failures.append('Native animation did not change pose')
    if any(s['globals'][5]!=16 for s in samples):failures.append('Protected target lost health')
    if entry['type']==0x81 and fields>=120 and result['surface_frames']<2:failures.append('Mode7 body missing or static')
    result['failures']=failures
    return result


def check(fields=360,types=None,output=None):
    folder=Path(output or tempfile.mkdtemp(prefix='boss-check-',dir=ROOT/'artwork-local/enemy-workshop'))
    session=NativeSession(folder=folder/'game');session.arena_enabled=True
    report={'images_opened':False,'profiles':[],'fields_per_profile':fields,'failures':[]}
    try:
        session.start()
        for entry in [e for e in session.catalog if e.get('boss') and (not types or e['type'] in types)]:
            samples=[];snapshot=session.spawn(entry)
            for field in range(0,fields,4):
                snapshot=session.step(4);raw=raw_actors(session)
                globals_=list(map(int,session.lua.eval('return mainmemory.read_u16_le(0x70),mainmemory.read_u16_le(0x86),'
                    'mainmemory.read_u16_le(0x1c),mainmemory.read_u16_le(0x1e),mainmemory.read_u16_le(0x13f2),'
                    'mainmemory.read_u16_le(0x13f4),mainmemory.read_u16_le(0xb8)')['values']))
                surface_hash=None;opaque=0
                if snapshot.get('boss_surface'):
                    pixels=base64.b64decode(snapshot['boss_surface']);surface_hash=hashlib.sha256(pixels).hexdigest()
                    with Image.open(io.BytesIO(pixels)) as image:opaque=sum(image.getchannel('A').histogram()[1:])
                samples.append(dict(field=field+4,globals=globals_,raw=raw,observed=snapshot['actors'],surface_hash=surface_hash,surface_opaque=opaque))
            result=summarize(entry,samples,fields)
            failures=result['failures']
            report['failures'].extend(f'{entry["type"]:02X}: {f}' for f in failures)
            (folder/f'{entry["type"]:02x}.json').write_text(json.dumps(dict(profile=entry,samples=samples),indent=2))
            report['profiles'].append(result);(folder/'report.json').write_text(json.dumps(report,indent=2))
            print(json.dumps(result),flush=True)
    finally:session.close()
    report['passed']=not report['failures'];(folder/'report.json').write_text(json.dumps(report,indent=2))
    print(folder,flush=True);return report


def verify_existing(folder):
    report={'images_opened':False,'profiles':[],'failures':[],'recorded_evidence':True}
    for file in sorted(Path(folder).glob('??.json')):
        data=json.loads(file.read_text());samples=data['samples'];entry=data['profile']
        result=summarize(entry,samples,max(s['field'] for s in samples))
        report['profiles'].append(result)
        report['failures'].extend(f'{entry["type"]:02X}: {f}' for f in result['failures'])
    if not report['profiles']:raise ValueError('No native boss recordings found')
    report['passed']=not report['failures']
    (Path(folder)/'verified-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2));return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fields',type=int,default=360)
    parser.add_argument('--verify-existing',type=Path);parser.add_argument('--types');parser.add_argument('--output',type=Path);args=parser.parse_args()
    result=verify_existing(args.verify_existing) if args.verify_existing else check(args.fields,[int(t,16) for t in args.types.split(',')] if args.types else None,args.output)
    raise SystemExit(0 if result['passed'] else 1)
