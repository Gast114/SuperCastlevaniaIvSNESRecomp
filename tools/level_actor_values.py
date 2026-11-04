"""Project-owned instance values; no writes to the retail ROM or workshop."""
from monster_balance import original_stats

LIMITS={'hp':(0,32767),'contact_damage':(0,255),'half_width':(0,255),'half_height':(0,255)}

def validate_values(actor):
    values=actor.get('stats',{})
    if not isinstance(values,dict):raise ValueError('Werte müssen ein Objekt sein.')
    for key,value in values.items():
        if key not in LIMITS or type(value) is not int or not LIMITS[key][0]<=value<=LIMITS[key][1]:
            raise ValueError('Ungültiger Objektwert: '+str(key))
    if not isinstance(actor.get('name',''),str) or len(actor.get('name',''))>100:raise ValueError('Name: höchstens 100 Zeichen.')
    if actor.get('boss_start','direct') not in ('direct','sequence'):raise ValueError('Ungültiger Bossstart.')
    if actor.get('boss_end','continue') not in ('continue','exit'):raise ValueError('Ungültiges Bossende.')

def values_for(rom,actor,room,quest=0):
    t=actor['type'];entry=dict(actor,boss=t>=128)
    result=original_stats(rom,entry,'new_game_plus' if quest else 'normal',room)
    hit=int.from_bytes(rom[0x8000+((0xab00+t*2)&32767):][:2],'little') if t<128 else 0
    result.update(half_width=hit&255,half_height=hit>>8)
    if t>=128:
        if t==0x8b:result['contact_damage']=None  # This controller's body is auxiliary actor $09.
        from level_bosses import REVISION,STATE_BYTES
        from enemy_workshop_native import ROOT
        import struct
        path=ROOT/f'artwork-local/level-editor/bosses/{t:02x}-r{REVISION}.bin'
        if path.is_file():
            data=path.read_bytes();slot=struct.unpack_from('<5H',data)[3];at=10+STATE_BYTES+2+2+slot-0x580
            if not quest:result['hp']=struct.unpack_from('<H',data,at+6)[0]
            result.update(half_width=struct.unpack_from('<H',data,at+0x28)[0],half_height=struct.unpack_from('<H',data,at+0x2a)[0])
    if t==14:result.update(hp=0,contact_damage=0,half_width=8,half_height=8)
    result.update(actor.get('stats',{}));return result
