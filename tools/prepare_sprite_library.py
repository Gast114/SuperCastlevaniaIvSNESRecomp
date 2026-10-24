"""Add proved ROM poses to the measured native sprite library, then reuse it."""
import argparse
import hashlib
import json
from pathlib import Path
from enemy_workshop_library import DEFAULT_LIBRARY,load_library,reconcile_library
from enemy_workshop_native import ROOT
from enemy_sprite_export import render_pose

INVENTORY=ROOT/'assets/enemy_sprite_inventory.json'
EXPORT_VERSION=1


def write(path,value):
    pending=path.with_suffix('.pending.json')
    pending.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    pending.replace(path)


def add_rom_poses(destination=DEFAULT_LIBRARY,rom=None,inventory=INVENTORY,ensure=False):
    destination=Path(destination);inventory=Path(inventory)
    index=load_library(destination)
    if not index.get('run_complete'):raise ValueError('Zuerst die native Sprite-Bibliothek vollständig vorbereiten.')
    digest=hashlib.sha256(inventory.read_bytes()).hexdigest()
    if ensure and index.get('rom_inventory_sha256')==digest and index.get('rom_export_version')==EXPORT_VERSION:
        return index
    data=json.loads(inventory.read_text(encoding='utf-8'))
    raw=Path(rom or ROOT/'Super Castlevania IV (USA).sfc').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=index['rom_sha256'] or data['rom_sha256']!=index['rom_sha256']:
        raise ValueError('ROM, Inventar und Sprite-Bibliothek müssen zusammenpassen.')
    native=destination/'native-template';manifest=json.loads((native/'enemies.json').read_text(encoding='utf-8'))
    frames={f['id']:f for f in manifest['frames']};actors={a['type']:a for a in data['actors']}
    def graphics_resource(actor):
        offset=0x8000+((0xa900+actor*3)&0x7fff)
        return raw[offset:offset+3]
    contexts={graphics_resource(p['type']):p for p in index['profiles'] if p['type']<128 and p.get('context')}
    report={'added_images':0,'exported_pose_assignments':0,'context_id_checks':0,'profiles':[],'unresolved':[]}
    for profile in index['profiles']:
        if profile.get('preview_only'):continue
        actor=actors.get(profile['type'],{});poses=actor.get('poses',[])
        if not poses:continue
        context=profile.get('context');context_key=profile['key'];borrowed=False
        if not context and profile['type']<128:
            owner=contexts.get(graphics_resource(profile['type']))
            if owner:context=owner['context'];context_key=owner['key'];borrowed=True
        if not context:
            report['unresolved'].append({'key':profile['key'],'poses':poses,'reason':'Originaler Grafikkontext fehlt'})
            continue
        video=Path(context['video']).read_bytes()
        check=render_pose(raw,context['actor_type'],context['current_pose'],video,context['obsel'],context['tile_add'],context['priority'])
        if check[0][0]['id']!=context['current_id']:
            raise ValueError('Originaler Grafikkontext stimmt nicht mit der nativen Aufnahme überein: '+context_key)
        report['context_id_checks']+=1
        # Boss programs also write other actor slots. Static code ownership
        # alone cannot assign every child pose to the main body's actor ID.
        observed_main=set(profile.get('main_poses',[]))
        if profile.get('boss'):
            unknown=sorted(set(poses)-observed_main)
            if unknown:report['unresolved'].append({'key':profile['key'],'poses':unknown,'reason':'Boss-Kindslot / Grafikwechsel noch nicht sicher zugeordnet'})
            poses=[p for p in poses if p in observed_main]
        exported=set(profile.get('rom_frame_ids',[]));success=[];failed=[]
        actual_type=context['actor_type'] if profile.get('boss') else profile['type']
        for pose in poses:
            try:images=render_pose(raw,actual_type,pose,video,context['obsel'],context['tile_add'],context['priority'])
            except ValueError as error:
                failed.append({'pose':pose,'reason':str(error)});continue
            for frame,image in images:
                identifier=frame['id'];exported.add(identifier)
                if identifier in frames:continue
                path=native/frame['reference']
                if path.exists():raise ValueError('Unzugeordnete bestehende Originaldatei wird nicht überschrieben: '+str(path))
                image.save(path)
                frames[identifier]=dict(frame,source_kind='rom_pose',source_profile=profile['key'],
                    graphics_context=context_key,graphics_resource_shared=borrowed,
                    native_motion_observed=False,pose_reference=0x040000|pose)
                report['added_images']+=1
            success.append(pose);report['exported_pose_assignments']+=1
        profile['rom_frame_ids']=sorted(exported)
        profile['frame_ids']=sorted(set(profile['frame_ids'])|exported)
        profile['template_frame_ids']=sorted(set(profile.get('template_frame_ids',[]))|exported)
        profile['rom_poses']=success
        profile['poses']=sorted(set(profile['poses'])|set(success))
        report['profiles'].append({'key':profile['key'],'poses':success,'failed':failed,'graphics_context':context_key})
    manifest['frames']=list(frames.values());write(native/'enemies.json',manifest)
    index['rom_inventory_sha256']=digest;index['rom_export_version']=EXPORT_VERSION
    index['rom_export_report']=report
    index=reconcile_library(destination,index)
    write(destination/'rom-export-report.json',report)
    return index


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path,default=DEFAULT_LIBRARY)
    parser.add_argument('--rom',type=Path);parser.add_argument('--ensure',action='store_true')
    args=parser.parse_args()
    data=add_rom_poses(args.destination,args.rom,ensure=args.ensure)
    print(json.dumps({'summary':data['summary'],'rom_poses':data.get('rom_export_report',{}).get('exported_pose_assignments',0)},ensure_ascii=False))


if __name__=='__main__':main()
