"""Audit ordinary workshop candidates against visible native-engine sprites.

This is a diagnostic, not an assertion that resource-table actors are enemies.
Every profile runs in a copied private game folder. Failed/hung profiles restart
that private process; actual player saves, settings, artwork and ROM are read-only.
"""
import argparse
import collections
import json
from pathlib import Path
import tempfile
import time
import shutil
from PIL import Image,ImageDraw
import sciv_play as play
from enemy_workshop_native import NativeSession,ROOT

# The regular playback helper permits long campaign scripts. A candidate which
# gets stuck in an AI/controller must not block this bounded catalog audit.
_wait=play.wait_idle
play.wait_idle=lambda lua,timeout=8:_wait(lua,min(timeout,8))

def gallery(work,results):
    visible=[r for r in results if r.get('image')]
    for page in range((len(visible)+23)//24):
        sheet=Image.new('RGB',(1200,960),(25,29,34));draw=ImageDraw.Draw(sheet)
        for index,row in enumerate(visible[page*24:(page+1)*24]):
            image=Image.open(work/row['image']).convert('RGBA');image.thumbnail((184,184),Image.Resampling.NEAREST)
            x=(index%6)*200;y=(index//6)*240
            sheet.paste(image,(x+(200-image.width)//2,y+30),image)
            draw.text((x+7,y+6),f'{row["type"]:02X} / v{row["variant"]} / R{row["room"]:02X}',fill='white')
            draw.text((x+7,y+218),f'{row["matched_fields"]} fields; {row["poses"][:3]}',fill='#b7c3cf')
        sheet.save(work/f'gallery-{page+1}.png')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fields',type=int,default=48)
    parser.add_argument('--limit',type=int)
    parser.add_argument('--types',help='Optional comma-separated native hexadecimal actor types')
    parser.add_argument('--fixture',type=Path,default=ROOT/'artwork-local/enemy-hd-2026-10-23/a02-enemy-probe/saves/save9.sav')
    args=parser.parse_args()
    parent=ROOT/'artwork-local/enemy-catalog-audit';parent.mkdir(exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='audit-',dir=parent));results=[];session=None;counter=0
    def new_session():
        nonlocal counter
        counter+=1;s=NativeSession(folder=work/f'game-{counter:02d}')
        s.start(args.fixture);s.command('enemy','capture off');s.command('hd','off');s.command('layers','16')
        return s
    def save():
        counts=collections.Counter(r['result'] for r in results)
        report={'scope':'ordinary/provisional actors below 0x80; bosses excluded','not_all_verified_actors_are_enemies':True,
                'fields_per_profile':args.fields,'summary':dict(counts),'results':results}
        (work/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(work,flush=True)
    try:
        session=new_session();catalog=[dict(e) for e in session.catalog if e['type']<0x80 and e['type']!=0x2a]
        if args.types:
            selected={int(n,16) for n in args.types.split(',')};catalog=[e for e in catalog if e['type'] in selected]
        if args.limit:catalog=catalog[:args.limit]
        (work/'catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        for index,entry in enumerate(catalog):
            row=dict(entry,result='missing',matched_fields=0,poses=[],observed_types=[],observation_count=0,classification='unclassified',proven_enemy_identity=False)
            began=time.monotonic();poses=set();other_types=set();best=None;trace=[]
            try:
                current=session.spawn(entry)
                # Capture one exact actor-composed image after loading settles.
                # A rectangular screenshot crop can contain Simon/other OBJs;
                # it is useful context but must not identify the actor's art.
                session.command('enemy','capture on');current=session.step(1)
                session.command('enemy','capture off');session.command('enemy','flush')
                for field in range(0,max(1,args.fields),4):
                    if field:current=session.step(min(4,args.fields-field))
                    actors=[a for a in current['actors'] if a['type']==entry['type']]
                    other_types.update(a['type'] for a in current['actors'])
                    trace.append({'field':field,'actors':current['actors']})
                    if actors:
                        row['matched_fields']+=1;row['observation_count']+=len(actors)
                        poses.update(a['pose'] for a in actors)
                        if best is None:
                            actor=actors[0];tag=f'{entry["type"]:02x}-v{entry["variant"]:02x}-r{entry["room"]:02x}'
                            shot=work/(tag+'-obj.png');session.command('screenshot',shot)
                            image=Image.open(shot).convert('RGBA');size=actor.get('size',96);anchor=actor.get('anchor',size//2)
                            # Native pixels, clipped by the actual output field.
                            box=(actor['x']-anchor,actor['y']-anchor,actor['x']-anchor+size,actor['y']-anchor+size)
                            crop=image.crop(box);crop.save(work/(tag+'-crop.png'))
                            reference=session.references/(actor['id']+'.png')
                            if reference.exists():
                                shutil.copy2(reference,work/(tag+'-actor.png'));row['image']=tag+'-actor.png';row['image_kind']='exact_actor_composition'
                            else:
                                row['image']=tag+'-crop.png';row['image_kind']='context_crop_not_identity'
                            row['screenshot']=tag+'-obj.png';best=actor
                if row['matched_fields']:row['result']='visible_native_actor'
                if best:row['first_verified_actor']=best
            except BaseException as exc:
                row['result']='error';row['error']=f'{type(exc).__name__}: {exc}'
                try:session.close()
                except BaseException:pass
                session=None
            row['poses']=[f'{n:04X}' for n in sorted(poses)];row['observed_types']=sorted(other_types);row['seconds']=round(time.monotonic()-began,2)
            row['samples']=len(trace);results.append(row)
            (work/f'{entry["type"]:02x}-v{entry["variant"]:02x}-trace.json').write_text(json.dumps(trace)+'\n')
            save()
            print(f'{index+1}/{len(catalog)} {entry["type"]:02X} v{entry["variant"]}: {row["result"]}, {row["matched_fields"]}/{len(trace)} samples, poses {row["poses"]}',flush=True)
            if session is None and index+1<len(catalog):session=new_session()
        gallery(work,results)
    finally:
        save()
        if session:
            try:session.close()
            except BaseException:pass
    print(work/'report.json',flush=True)

if __name__=='__main__':main()
