"""Native movement evidence for complete skeleton actions in a private session."""
import argparse
import json
import time
from pathlib import Path
from enemy_workshop_native import NativeSession,ROOT

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--rom',type=Path)
p.add_argument('--fixture',type=Path)
a=p.parse_args()
s=NativeSession(a.rom)
print(s.folder,flush=True)
report={'passed':False,'native_action_replay':True,'full_game_coverage':False,'actions':{},'catalog_entries':len(s.catalog)}
try:
    s.start(a.fixture)
    entry=next(e for e in s.catalog if e['type']==0x12 and e['room']==1)
    all_frames=[]
    for action,fields in [('Gehen',70),('Werfen',65),('Zerfallen',45)]:
        s.spawn(entry);s.action(action);seen={};trace=[]
        for n in range(fields):
            snapshot=s.step()
            trace.append(snapshot)
            for actor in snapshot['actors']:
                seen.setdefault(str(actor['type']),set()).add(actor['pose'])
        report['actions'][action]={k:sorted(v) for k,v in seen.items()}
        all_frames.append({'action':action,'frames':trace})
        print(action,report['actions'][action],flush=True)
    (s.folder/'native-actions.json').write_text(json.dumps(all_frames))
    throw=report['actions']['Werfen']
    assert {0x8af4,0x8b05}.issubset(report['actions']['Gehen'].get('18',[]))
    assert {0x8b1b,0x8b30,0x8b4d}.issubset(throw.get('18',[])),throw
    assert {0x900c,0x9011,0x9016}.issubset(throw.get('2',[])),'Bone rotations incomplete'
    death={0x80dc,0x80e1,0x80f2,0x8103,0x8108,0x8119,0x811e,0x812f,0x8134,0x8145}
    assert death.issubset(report['actions']['Zerfallen'].get('45',[])),'Native death effects incomplete'
    s.command('enemy','flush')
    manifest=json.loads((s.references/'enemies.json').read_text())
    captured={f['id'] for f in manifest['frames']}
    observed={identifier for action in all_frames for snapshot in action['frames'] for actor in snapshot['actors']
              for identifier in [actor['id']]+[p['id'] for p in actor['parts']]}
    assert observed<=captured,'Visible native pose/component PNGs missing'
    report['captured_images']=len(manifest['frames'])
    assert report['captured_images']>10
    report['passed']=True
    print('PASS native walking, all three throw phases, moving bone, death fragments and editable components',flush=True)
finally:
    s.close()
    (s.folder/'report.json').write_text(json.dumps(report,indent=2))
