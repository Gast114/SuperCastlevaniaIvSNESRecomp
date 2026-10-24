"""Persistent original-sprite library for the separate native enemy workshop.

The cache contains observed original PNGs and motion records, never artist HD
files. A bounded native capture is explicitly not a full ROM animation census.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
from enemy_workshop_native import NativeSession,ROOT
from enemy_catalog_profiles import BOSS_SETUP_REVISION,BOSS_TYPES

DEFAULT_LIBRARY=ROOT/'artwork-local/enemy-library'
ROM_SHA256='0ef6f4cce5a2273fa49fe1ce724e0048a8e39c91da6b00dbb693fe1ba909177d'

def _read(path,default=None):
    try:return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError):return {} if default is None else default

def _write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');temporary.replace(path)

def profile_key(entry):
    if entry.get('key'):return entry['key']
    return ('boss' if entry.get('boss') else 'actor')+f'-{entry["type"]:02x}-v{entry.get("variant",0):02x}'

def load_library(path=DEFAULT_LIBRARY):
    path=Path(path);return _read(path/'library.json' if path.is_dir() or path.suffix!='.json' else path)


def boss_cache_current(index):
    rows={p['type']:p for p in index.get('profiles',[]) if p.get('boss')}
    return BOSS_TYPES<=rows.keys() and all(rows[t].get('native_setup_revision',0)>=BOSS_SETUP_REVISION for t in BOSS_TYPES)


def refresh_profile(row,entry,destination):
    """Invalidate obsolete native boss captures without changing any PNG.

    Old mappings and recordings stay available in history; they must not be
    reused as current boss templates after a graphics-loader correction.
    """
    if row is None:return None
    revision=entry.get('native_setup_revision',0)
    if row.get('native_setup_revision',0)<revision:
        history=Path(destination)/'history';history.mkdir(exist_ok=True)
        archived=dict(row)
        archived['recordings']=[]
        for record in row.get('recordings',[]):
            source=Path(record)
            if not source.is_file():continue
            digest=hashlib.sha256(source.read_bytes()).hexdigest()[:16]
            target=history/(row['key']+'-'+digest+'.json')
            if not target.exists():shutil.copy2(source,target)
            archived['recordings'].append(str(target))
        previous=list(row.get('legacy_captures',[]));archived.pop('legacy_captures',None)
        previous.append(archived)
        row=dict(entry,key=row['key'],main_type=entry.get('main_type',entry['type']),
                 frame_ids=[],main_frame_ids=[],child_frame_ids=[],poses=[],recordings=[],
                 legacy_captures=previous,status='not_captured',captured_fields=0,coverage_complete=False)
    else:
        # Catalog metadata may improve without requiring another native run.
        row.update(entry)
    return row

def discover_sources():
    sources=[]
    for name in ('enemy-workshop','enemy-workshop-2026-10-24','enemy-catalog-audit','enemy-workshop-review','enemy-hd-2026-10-23'):
        root=ROOT/'artwork-local'/name
        if root.exists():
            for path in root.rglob('enemies.json'):
                if path.parent.name!='native-template':continue
                # Standalone synthetic renderer tests also write native-template
                # folders. Only a copied real-game profile has this ROM binding.
                binding=path.parent.parent.parent/'rom.cfg'
                if binding.is_file():sources.append(path.parent)
    return sorted(set(sources),key=str)

def merge_sources(destination,sources,progress=None):
    """Merge immutable original captures, preserving every existing image byte.

    Differently coloured captures can share a palette-independent native pose
    key. Keep the first reference and record the conflict instead of replacing
    an existing original or touching artist artwork.
    """
    destination=Path(destination).resolve();target=destination/'native-template';target.mkdir(parents=True,exist_ok=True)
    old=_read(target/'enemies.json',{'version':1,'frames':[]});frames={f['id']:f for f in old.get('frames',[])}
    conflicts=[];used=[];added=0
    for value in sources:
        source=Path(value).resolve()
        if source==target:continue
        data=_read(source/'enemies.json')
        if data.get('version')!=1:continue
        used.append(str(source))
        for frame in data.get('frames',[]):
            identifier=frame.get('id');name=frame.get('reference','')
            if not identifier or not name or Path(name).name!=name:continue
            file=source/name
            if not file.is_file():continue
            current=frames.get(identifier);output=target/(current['reference'] if current else name)
            if output.exists():
                if hashlib.sha256(output.read_bytes()).digest()!=hashlib.sha256(file.read_bytes()).digest():
                    conflicts.append({'id':identifier,'source':str(file),'kept':str(output)})
                if current is None:frames[identifier]=dict(frame)
                continue
            shutil.copy2(file,output);frames[identifier]=dict(frame,reference=output.name);added+=1
        if progress:progress({'stage':'merge','source':str(source),'frames':len(frames),'added':added})
    _write(target/'enemies.json',{'version':1,'name':'Originale Gegnerbibliothek','frames':list(frames.values())})
    return {'frames':list(frames.values()),'added':added,'conflicts':conflicts,'sources':used}

def _families(entry):
    main=entry.get('main_type',entry['type']);children=set(entry.get('child_types',[]))
    if entry['type'] in (17,18):children.update((2,45))
    children.discard(main);return main,children

def _actor_role(entry,actor):
    main,children=_families(entry)
    if actor['type']==main:
        if not entry.get('boss') or actor['slot']==entry.get('main_slot',actor['slot']):return 'main'
        return 'child'
    return 'child' if actor['type'] in children else None

def _index_summary(index):
    profiles=index['profiles'];frames=_read(Path(index['destination'])/'native-template/enemies.json').get('frames',[])
    assigned={identifier for p in profiles for identifier in p['frame_ids']}
    index['summary']={'catalog_profiles':sum(not p.get('preview_only') for p in profiles),'profile_count':len(profiles),'profiles_with_images':sum(bool(p['frame_ids']) for p in profiles),
                      'captured_profiles':sum(p['status']=='captured' for p in profiles),
                      'missing_profiles':sum(p['status']=='missing' for p in profiles),
                      'error_profiles':sum(p['status']=='error' for p in profiles),
                      'original_images':len(frames),'whole_images':sum('__teil-' not in f['id'] for f in frames),
                      'component_images':sum('__teil-' in f['id'] for f in frames),'unassigned_images':sum(f['id'] not in assigned for f in frames),'coverage_complete':False}

def reconcile_library(destination,index=None):
    """Assign observed frame IDs strictly from each profile's own motion trace.

    Older type-family templates remain a labelled fallback only when that
    profile has no observed main body. Boss aliases never borrow other type09
    actors' screenshots merely because their native type happens to match.
    """
    destination=Path(destination).resolve();index=load_library(destination) if index is None else index
    available={f['id'] for f in _read(destination/'native-template/enemies.json').get('frames',[])}
    index['profiles']=[p for p in index.get('profiles',[]) if not p.get('preview_only')]
    for row in index.get('profiles',[]):
        main,children=_families(row);m=set();c=set();mp=set();cp={}
        for record in row.get('recordings',[]):
            data=_read(record)
            for action in data.get('actions',[]):
                for snap in action.get('frames',[]):
                    for actor in snap.get('actors',[]):
                        role=_actor_role(row,actor)
                        if role=='main':bucket=m;mp.add(actor['pose'])
                        elif role=='child':bucket=c;cp.setdefault(str(actor['type']),set()).add(actor['pose'])
                        else:continue
                        bucket.add(actor['id']);bucket.update(p['id'] for p in actor.get('parts',[]))
        row['observed_main_frame_ids']=sorted(m&available);row['observed_child_frame_ids']=sorted(c&available)
        row['missing_captured_frame_ids']=sorted((m|c)-available)
        row['main_poses']=sorted(mp);row['child_poses']={t:sorted(v) for t,v in cp.items()}
        row['motion_frame_ids']=sorted((m|c)&available)
        templates=(set(row.get('frame_ids',[]))|set(row.get('template_frame_ids',[])))&available
        row['template_frame_ids']=sorted(templates-(m|c))
        row['frame_ids']=sorted(templates|((m|c)&available))
        if m&available:
            row['main_frame_ids']=sorted(set(row.get('main_frame_ids',[]))|(m&available));row['child_frame_ids']=sorted(set(row.get('child_frame_ids',[]))|(c&available))
            row['poses']=sorted(set(row.get('poses',[]))|mp|{p for v in cp.values() for p in v})
            row['frame_assignment']='exact native snapshots from this profile'
        else:
            row['frame_assignment']='type-family templates only; no matched main body in this profile capture'
    assigned={identifier for row in index['profiles'] for identifier in row['frame_ids']}
    extra={}
    for frame in _read(destination/'native-template/enemies.json').get('frames',[]):
        if frame['id'] not in assigned:extra.setdefault(frame['actor_type'],[]).append(frame)
    for actor,frames in sorted(extra.items()):
        ids=sorted(f['id'] for f in frames)
        index['profiles'].append({'key':f'sprites-{actor:02x}','type':actor,'variant':0,'name':f'Weitere Sprites {actor:02X}',
            'category':'unclassified','boss':False,'preview_only':True,'frame_ids':ids,'template_frame_ids':ids,
            'motion_frame_ids':[],'main_frame_ids':[],'child_frame_ids':[],'poses':sorted({f['pose'] for f in frames}),
            'status':'original_templates','coverage_complete':False,
            'coverage_note':'Originalaufnahme; eigener Spawnkontext noch nicht zugeordnet'})
    _index_summary(index);_write(destination/'library.json',index);return index

def build_library(destination=DEFAULT_LIBRARY,rom=None,build=None,fields=240,progress=None,cancelled=None):
    destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=True);fields=max(1,int(fields))
    existing=load_library(destination)
    if existing and existing.get('rom_sha256')!=ROM_SHA256:raise ValueError('Spritebibliothek gehört zu einer anderen ROM.')
    if rom is not None and hashlib.sha256(Path(rom).read_bytes()).hexdigest()!=ROM_SHA256:
        raise ValueError('Original-USA-ROM passt nicht zur Spritebibliothek.')
    cached=_read(destination/'native-template/enemies.json')
    intact=bool(cached.get('frames')) and all((destination/'native-template'/f['reference']).is_file() for f in cached['frames'])
    if existing.get('run_complete') and existing.get('capture_fields',0)>=fields and intact and boss_cache_current(existing):
        if progress:progress({'stage':'cached','profiles':len(existing.get('profiles',[]))})
        return existing
    merged=merge_sources(destination,discover_sources(),progress)
    old={p['key']:p for p in existing.get('profiles',[])};session=None;sequence=0
    index={'version':1,'rom_sha256':ROM_SHA256,'destination':str(destination),'profiles':[],
           'sources':sorted(set(existing.get('sources',[])+merged['sources'])),
           'capture_fields':fields,'coverage_complete':False,'run_complete':False,
           'coverage_note':'Vorab erfasste native Abläufe und Original-PNGs. Noch kein vollständiger Nachweis aller ROM-Posen und Zustände.',
           'image_conflicts':existing.get('image_conflicts',[])+merged['conflicts']}
    runs=destination/'sessions';runs.mkdir(exist_ok=True)
    def notify(value):
        if progress:progress(value)
    def save():
        _index_summary(index);_write(destination/'library.json',index)
    def start():
        nonlocal sequence
        sequence+=1
        folder=Path(tempfile.mkdtemp(prefix='capture-',dir=runs))
        s=NativeSession(rom=rom,build=build,folder=folder);s.start();s.command('enemy','capture off');return s
    def collect(s):
        s.command('enemy','flush');source=s.references
        merge=merge_sources(destination,[source]);index['sources']=sorted(set(index['sources']+merge['sources']))
        index['image_conflicts'].extend(merge['conflicts'])
        return len(_read(source/'enemies.json').get('frames',[]))
    try:
        # Construct the catalog without booting an emulator on a warm cache.
        rom_path=Path(rom or ROOT/'Super Castlevania IV (USA).sfc');raw=rom_path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=ROM_SHA256:raise ValueError('Original-USA-ROM passt nicht zur Spritebibliothek.')
        probe=NativeSession.__new__(NativeSession);probe.bytes=raw
        from enemy_catalog_profiles import boss_profiles
        catalog=probe.read_catalog()+boss_profiles(probe)
        known=merged['frames']
        for entry in catalog:
            key=profile_key(entry);main,children=_families(entry)
            row=refresh_profile(old.get(key),entry,destination)
            if row is None:
                # Shared normal actor keys are reusable; a boss alias must be
                # assigned from that boss's observed recording, not all type09.
                seed=[f['id'] for f in known if f.get('actor_type')==main] if not entry.get('boss') else []
                row=dict(entry,key=key,main_type=main,child_types=sorted(children),frame_ids=seed,main_frame_ids=seed,
                         child_frame_ids=[],poses=sorted({f['pose'] for f in known if f['id'] in seed}),
                         status='seeded' if seed else 'not_captured',captured_fields=0,recordings=[],coverage_complete=False,
                         coverage_note=entry.get('coverage_note','Noch kein vollständiger Aktionskatalog; bisherige tatsächliche Aufnahmen.'))
            index['profiles'].append(row)
        save()
        for number,(entry,row) in enumerate(zip(catalog,index['profiles'])):
            if cancelled and cancelled():index['cancelled']=True;break
            if row.get('capture_complete') and row.get('requested_fields',0)>=fields and row.get('status') in ('captured','missing','seeded'):
                notify({'stage':'cached','profile':row['key'],'index':number+1,'total':len(catalog)});continue
            notify({'stage':'capture','profile':row['key'],'name':row['name'],'index':number+1,'total':len(catalog)})
            observed_main=set(row.get('main_frame_ids',[]));observed_child=set(row.get('child_frame_ids',[]));poses=set(row.get('poses',[]));recordings=[]
            main,children=_families(entry);captured_fields=0;actual_main=set();context_saved=False;interrupted=False
            try:
                if session is None:session=start()
                # Reserve enough space for new poses/parts before the native
                # capture set reaches its per-process 4096-reference bound.
                if len(_read(session.references/'enemies.json').get('frames',[]))>2600:
                    collect(session);session.close();session=start()
                session.command('enemy','capture off');session.spawn(entry);session.command('enemy','capture on')
                actions=[('Natürlich',fields)]
                if entry['type'] in (17,18):actions=[('Gehen',max(64,(fields+2)//3)),('Werfen',max(96,(fields+2)//3)),('Zerfallen',max(64,(fields+2)//3))]
                for action,length in actions:
                    if action not in ('Natürlich','Gehen'):
                        session.command('enemy','capture off');session.spawn(entry);session.command('enemy','capture on')
                    if action!='Natürlich':session.action(action)
                    frames=[]
                    for field in range(length):
                        if cancelled and cancelled():interrupted=True;break
                        snap=session.step(1);captured_fields+=1
                        actors=snap.get('actors',[])
                        for actor in actors:
                            role=_actor_role(entry,actor)
                            bucket=observed_main if role=='main' else observed_child if role=='child' else None
                            if bucket is None:continue
                            bucket.add(actor['id']);bucket.update(p['id'] for p in actor.get('parts',[]));poses.add(actor['pose'])
                            if role=='main':
                                actual_main.add(actor['id'])
                                if not context_saved:
                                    contexts=destination/'contexts';contexts.mkdir(exist_ok=True)
                                    video=contexts/(row['key']+'-video.bin');lines=contexts/(row['key']+'-lines.bin')
                                    session.command('dump',video);session.command('lines',lines)
                                    slot=actor['slot'];linebytes=lines.read_bytes()
                                    row['context']={'video':str(video),'lines':str(lines),'obsel':linebytes[34] if len(linebytes)>34 else None,
                                                    'priority':session.read(slot+2),'tile_add':session.read(slot+0x26),
                                                    'actor_type':main,'slot':slot,'current_pose':actor['pose'],'current_id':actor['id'],
                                                    'same_native_field':True}
                                    context_saved=True
                        frames.append(snap)
                    recordings.append({'action':action,'frames':frames})
                    if interrupted:break
                session.command('enemy','capture off');collect(session)
                file=destination/'recordings'/(row['key']+'.json');_write(file,{'profile':row['key'],'actions':recordings})
                available={f['id'] for f in _read(destination/'native-template/enemies.json').get('frames',[])}
                row.update(main_frame_ids=sorted(observed_main&available),child_frame_ids=sorted(observed_child&available),
                           frame_ids=sorted((observed_main|observed_child)&available),poses=sorted(poses),
                           status='cancelled' if interrupted else 'captured' if actual_main else 'seeded' if observed_main&available else 'missing',
                           captured_fields=captured_fields,requested_fields=fields,capture_complete=not interrupted,
                           movement_observed=bool(actual_main),observed_main_ids=sorted(actual_main),
                           recordings=[str(file)],coverage_complete=False,
                           coverage_note=entry.get('coverage_note','Kurzer nativer Ablauf aufgenommen; weitere Angriffe, Treffer und Todeszustände können fehlen.'))
                row.pop('error',None)
            except Exception as exc:
                row.update(status='error',error=f'{type(exc).__name__}: {exc}',captured_fields=captured_fields)
                if session:
                    try:collect(session)
                    except Exception:pass
                    try:session.close()
                    except Exception:pass
                    session=None
            save();notify({'stage':'profile_done','profile':row['key'],'status':row['status'],'images':len(row['frame_ids']),'index':number+1,'total':len(catalog)})
        index['run_complete']=not index.get('cancelled',False) and all(r.get('capture_complete') and r.get('requested_fields',0)>=fields and r['status'] in ('captured','missing','seeded') for r in index['profiles'])
        index=reconcile_library(destination,index)
        save();return index
    finally:
        if session:
            try:collect(session)
            except Exception:pass
            session.close()
        save()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--ensure',action='store_true')
    parser.add_argument('--destination',type=Path,default=DEFAULT_LIBRARY);parser.add_argument('--fields',type=int,default=240)
    parser.add_argument('--rom',type=Path);parser.add_argument('--build',type=Path);args=parser.parse_args()
    result=build_library(args.destination,args.rom,args.build,args.fields,progress=lambda p:print(json.dumps(p,ensure_ascii=False),flush=True))
    print(json.dumps(result['summary'],ensure_ascii=False))

if __name__=='__main__':main()
