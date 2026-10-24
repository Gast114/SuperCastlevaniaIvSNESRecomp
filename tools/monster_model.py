"""Monster codes, verified action ownership and original combat parameters."""
from monster_balance import original_stats

SKELETONS={0x11,0x12,0x31,0x56,0x69}
WALK={0x11:{0x8af4,0x8b05},0x12:{0x8af4,0x8b05},0x31:{0x93be,0x93d7},
      0x56:{0x919d,0x91ba},0x69:{0x9470,0x9481}}
ATTACK={0x12:{0x8b1b,0x8b30,0x8b4d},0x31:{0x93f0,0x9409,0x9426},
        0x56:{0x91d8,0x9201}}
BONES={0x900c,0x9011,0x9016}
GROUPS=('Gehen / Bewegen','Springen','Angriff','Sterben','Noch zuordnen')


def code(actor):return f'M-{actor:04X}'


def byte(rom,bank,address):return rom[bank*0x8000+(address&0x7fff)]
def word(rom,bank,address):return byte(rom,bank,address)|byte(rom,bank,address+1)<<8


def definitions(catalog,rom):
    """One selectable monster per native type; projectiles stay with owners."""
    result={}
    for entry in catalog:
        t=entry['type']
        if entry.get('preview_only'):continue
        combat=t<128 and word(rom,1,0xac00+t*2)>0 and word(rom,1,0xad00+t*2)&0x40
        if t in (0x6c,0x73,0x77):continue  # Invisible helpers; $77 handler is a bare RTL.
        if not (entry.get('boss') or entry.get('category')=='enemy' and word(rom,1,0xac00+t*2)>0 or combat and entry.get('category') in ('unclassified','object')):continue
        row=result.setdefault(t,dict(type=t,code=code(t),variants=[],boss=entry.get('boss',False)))
        row['variants'].append(entry)
    return [result[t] for t in sorted(result)]


def actions(entry):
    t=entry['type']
    return {'Natürlich':True,'Gehen':t in SKELETONS,'Springen':t in (0x12,0x31,0x56),
            'Angriff':t in (0x12,0x31,0x56),'Sterben':not entry.get('boss')}


def ai_notes(entry):
    t=entry['type']
    if t in SKELETONS:
        text='Die Original-KI wählt Bewegung und Blickrichtung relativ zum Spielerziel. Timer und Bodenkollisionen steuern Richtungswechsel.'
        if t in (0x12,0x31,0x56):text+=' Diese Variante startet mit zwei möglichen Ausweichsprüngen.'
        if t==0x12:text+=' Der Angriff besteht aus Ausholen, Abwurf und Ausklang; dabei erzeugt die KI ein echtes Geschoss (Typ 0002).'
        if t in (0x11,0x69):text+=' Diese Variante verursacht Kontaktschaden und hat keine eigene Wurfaktion.'
        return text
    if entry.get('boss'):return 'Originaler Bossablauf mit eigenem Szenenskript. Eine frei steuerbare neutrale Bossarena und die Bedeutungen aller Zustände sind noch nicht zugeordnet.'
    return 'Die Original-KI läuft in der Testszene. Die genaue Bedeutung ihrer Zustände und getrennte Sprung-/Angriffsauslöser sind für diesen Code noch nicht geprüft. „Natürlich“ zeigt den echten Ablauf.'


def combat_stats(rom,entry,live=None):
    t=entry['type'];live=live or {}
    room=live.get('source_room',entry.get('room',0))
    profiles={name:original_stats(rom,entry,name,room) for name in ('normal','new_game_plus')}
    normal=profiles['normal']
    return dict(code=code(t),base_hp=normal['base_hp'],current_hp=live.get('hp'),contact_damage=normal['contact_damage'],
                profiles=profiles,live_quest=live.get('quest'),live_difficulty=live.get('difficulty'),
                hitbox_width=live.get('half_width',0)*2,hitbox_height=live.get('half_height',0)*2,
                state=live.get('state'),x=live.get('x'),y=live.get('y'),speed_x=live.get('speed_x'),speed_y=live.get('speed_y'),
                hp_unit='interne Schadenseinheiten',damage_unit='Lebenspunkte des Spielers',
                hp_evidence='00:D74E..D75C / Actor+06',contact_evidence='00:DD0A..DD12 / 01:AF00' if t<128 else '00:DE29..DE33 / 01:B201')


def frame_groups(entry,workspace,extra_ids=()):
    """Group body, attack projectiles and death effects under one monster."""
    from enemy_workshop_library import profile_key
    profile=next((p for p in workspace.data['library_profiles'] if p['key']==profile_key(entry)),None)
    ids=set(profile.get('frame_ids',[])) if profile else set(workspace.frames)
    ids.update(extra_ids);t=entry['type'];main=entry.get('main_type',t)
    output={name:[] for name in GROUPS}
    recorded=workspace.data.get('monster_actions',{}).get(profile_key(entry),{})
    for frame in workspace.frames.values():
        if frame['id'] not in ids:continue
        actor=frame['actor_type'];pose=frame['pose'];group=None
        if frame['id'] in recorded.get('Sterben',[]):output['Sterben'].append(frame)
        if actor==45:group='Sterben'
        elif t in SKELETONS:
            if actor==main and pose in WALK[t]:group='Gehen / Bewegen'
            elif actor==main and pose in ATTACK.get(t,set()):group='Angriff'
            elif actor==2 and t==0x12 and pose in BONES:group='Angriff'
            else:continue
        elif actor==main:group='Noch zuordnen'
        elif actor in entry.get('child_types',[]):group='Angriff'
        if group and frame not in output[group]:output[group].append(frame)
    if t in (0x12,0x31,0x56):output['Springen']=list(output['Gehen / Bewegen'])
    return output


def visible_frames(groups,components=False,graphics_variants=False):
    """Default to one PNG per native pose/part; keep resource variants optional."""
    output={}
    for group,frames in groups.items():
        rows={}
        for frame in frames:
            if frame['component']!=components:continue
            part=frame['id'].rsplit('__teil-',1)[1] if components else None
            key=frame['image'] if graphics_variants else (frame['actor_type'],frame['pose'],part)
            rows.setdefault(key,frame)
        output[group]=list(rows.values())
    return output
