"""Original balance profiles and a separate, validated layer for future modes.

This module resolves data only. Custom values are never written to the game.
The native quest/room formula is verified against the project's USA ROM.
"""
import copy

PROFILES={'normal':0,'new_game_plus':1}
OVERRIDE_LIMITS={'hp':(0,0x7fff),'contact_damage':(0,255)}


def byte(rom,bank,address):return rom[bank*0x8000+(address&0x7fff)]
def word(rom,bank,address):return byte(rom,bank,address)|byte(rom,bank,address+1)<<8


def original_stats(rom,entry,profile='normal',room=None):
    if not isinstance(profile,str) or profile not in PROFILES:raise ValueError('Unbekanntes Originalprofil: '+str(profile))
    t=entry['type'];room=entry.get('room',0) if room is None else room
    if type(room) is not int or not 0<=room<68:raise ValueError('Grafikraum muss zwischen 0 und 67 liegen.')
    base=word(rom,1,0xac00+t*2) if t<128 else None
    room_bonus=byte(rom,1,0xa88f+room)
    quest_bonus=16*PROFILES[profile]
    contact=byte(rom,1,0xaf00+t) if t<128 else byte(rom,1,0xb201+(t&0x7f))
    if entry.get('boss') and entry.get('main_type',t)!=t:contact=None
    return dict(hp=min(0x7fff,base+room_bonus+quest_bonus) if base is not None else None,
                contact_damage=contact,base_hp=base,room=room,room_bonus=room_bonus,
                quest_bonus=quest_bonus,profile=profile,quest=PROFILES[profile],
                evidence={'hp':'00:D3FA..D40E + 00:D74E..D75C',
                          'contact_damage':'00:DD0A..DD21 / 01:AF00' if t<128 else '00:DE29..DE33 / 01:B201'})


def resolve_mode(rom,entry,mode=None,room=None):
    """Original -> chosen base profile -> per-code overrides, without mutation.

    Future editor/runtime integration can consume the same versioned shape:
    {version:1, base_profile:'new_game_plus', overrides:{'M-0012':{hp:80}}}.
    hp replaces the resolved spawn value, including room/quest bonuses.
    Unknown keys and invalid values fail visibly rather than changing balance.
    """
    if mode is None:mode={'version':1,'base_profile':'normal','overrides':{}}
    if not isinstance(mode,dict):raise ValueError('Spielmodus muss ein Objekt sein.')
    if type(mode.get('version')) is not int or mode['version']!=1:raise ValueError('Unbekannte Spielmodus-Version.')
    if set(mode)-{'version','base_profile','overrides','name'}:raise ValueError('Unbekanntes Spielmodus-Feld.')
    overrides=mode.get('overrides',{})
    if not isinstance(overrides,dict):raise ValueError('Wertüberschreibungen müssen nach Monster-Code geordnet sein.')
    for identifier,values in overrides.items():
        if not isinstance(identifier,str) or len(identifier)!=6 or not identifier.startswith('M-'):
            raise ValueError('Ungültiger Monster-Code.')
        try:actor=int(identifier[2:],16)
        except ValueError:raise ValueError('Ungültiger Monster-Code.') from None
        if identifier!=f'M-{actor:04X}' or not 0<actor<=0x8d:raise ValueError('Ungültiger Monster-Code.')
        if not isinstance(values,dict):raise ValueError('Monster-Werte müssen ein Objekt sein.')
        for key,value in values.items():
            if key not in OVERRIDE_LIMITS:raise ValueError('Noch nicht unterstützter Moduswert: '+key)
            low,high=OVERRIDE_LIMITS[key]
            if type(value) is not int or not low<=value<=high:raise ValueError(f'{key} muss zwischen {low} und {high} liegen.')
    original=original_stats(rom,entry,mode.get('base_profile','normal'),room)
    effective=copy.deepcopy(original);changed=overrides.get(f'M-{entry["type"]:04X}',{})
    effective.update(changed)
    return dict(original=original,effective=effective,overridden_fields=sorted(changed))
