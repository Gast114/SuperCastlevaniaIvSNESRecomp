"""Original boss-controller profiles, separate from ordinary actor placement.

The verified USA ROM dispatches $80..$8D through $01:A59C. $18..$29
are not boss IDs. Controller $2A is internal scene setup, never artist art.
Profiles below enter retail controller states; motion and child creation
remain entirely in the original engine. Room context is provisional unless
the exact controller record exists in $05 placement data.
"""

# variant, actor, native initializer, initial x/y, room, placement proved
_BOSSES=(
    (0x80,0x80,0x942b,0x0780,0x0040,7,True),
    (1,0x81,0x9447,0x07e0,0x0078,23,True),
    (2,0x83,0x947b,0x0e80,0x0080,9,True),
    (3,0x84,0x9497,0x0380,0x0060,20,True),
    (4,0x85,0x94b8,0x0180,0x0060,34,True),
    (5,0x86,0x94ec,0x0280,0x0060,53,True),
    (6,0x87,0x9514,0x08c0,0x0075,45,True),
    (7,0x88,0x9530,0x0180,0x0060,64,True),
    (8,0x89,0x954c,0x0180,0x0060,63,True),
    (9,0x8a,0x9568,0x02b0,0x0080,41,True),
    (10,0x8b,0x9584,0x0280,0x0060,65,True),
    (11,0x8c,0x95ae,0x0280,0x0060,59,True),
)
BOSS_SETUP_REVISION=2
BOSS_TYPES=frozenset(row[1] for row in _BOSSES)


def boss_profiles(session):
    """Return measured IDs, retaining context and visibility limits honestly."""
    profiles=[]
    for variant,actor,initializer,x,y,room,placed in _BOSSES:
        if session.word(2,0x9413+(variant&0x7f)*2)!=initializer:
            raise ValueError('Boss-Initialisierung passt nicht zur Original-ROM.')
        original_room=7 if actor==0x80 else room
        pointer=session.word(0,0xd81b+original_room*2);record=None
        for index in range(1024):
            address=pointer+index*6
            offset=5*0x8000+(address&0x7fff)
            raw=session.bytes[offset:offset+6]
            if raw[:2]==b'\xff\xff':break
            # Boss scene controllers also occur with x low bits=2. That
            # family is intentionally excluded from ordinary-actor parsing.
            if len(raw)==6 and raw[4]==0x2a and raw[5]==variant:
                record=address;break
        if record is None:
            raise ValueError('Originaler Bossraum-Controller fehlt in der ROM.')
        profiles.append(dict(type=actor,variant=0,boss=True,
            controller_variant=variant,
            original_controller_variant=variant,original_room=original_room,
            initializer=0x020000|initializer,
            room=room,x=x,y=y,flags=0x8000,record=record,
            context_provisional=not placed,
            name=f'Boss {actor:02X} · Originalszene',
            coverage_note=('Originaler Bossraum 7 mit nativem Szenencontroller.'
                if actor==0x80 else 'Mode7-Körper nativ sichtbar; seine HD-Texturzuordnung ist noch offen. OBJ-Teile können bearbeitet werden.'
                if actor==0x81 else 'Sichtbarer Körper als Actor 09 belegt; weitere Angriffs-/Todeszustände noch unvollständig.'
                if actor==0x8b else 'Sichtbare native OBJ-Posen belegt; kein vollständiger Angriff-/Todeskatalog.'),
            main_slot=0xd80 if actor in (0x83,0x88,0x8b,0x8c) else 0x580,
            main_type=9 if actor==0x8b else actor,
            # 81 needs BG/Mode7; 8B's visible body is native actor 09.
            preview_verified=True,
            # With ordinary streaming stopped, $01..$0D are the boss-specific
            # auxiliary actor family dispatched by $B8. $0E is Simon's weapon.
            child_types=list(range(1,0x0e)),native_setup_revision=BOSS_SETUP_REVISION))
    return profiles


def native_camera(session,x,y=0):
    """Write both the render camera and the original engine camera state."""
    session.write({0x1c:x,0x1280:x,0x12c0:x,
                   0x1e:y,0x1298:y,0x12d8:y})


def hold_boss_stage(session,entry):
    """Keep the private workshop camera/hero in this original boss arena.

    Call immediately before every native step batch, like the ordinary
    workshop's hero-position controls. This does not alter any boss field.
    """
    if getattr(session,'neutral_scene',False):
        session.prepare_arena();return
    # Boss motion must not teleport its target or drag the arena camera along.
    # The original AI uses world positions and its own collision/scene data.
    origin=max(0,entry['x']-128)
    native_camera(session,origin,0)
    session.write({0x54a:origin+(64 if getattr(session,'direction',-1)<0 else 192),0x54e:176,
                   0x13f4:16,0xbc:0x7fff,0x552:0,0x558:0,0x55a:0,0x55c:0,0x55e:0,
                   0x70:5,0x86:entry['room']})


def spawn_boss(session,entry,neutral=False):
    """Start a retail boss through its own asset-loading controller.

    Uses an isolated NativeSession. Executes the original graphics loader and
    controller transition, then native AI. It does not invent boss poses.
    Type82 is a script-generated actor and 8D has a separate final-scene
    initializer; neither is a complete standalone profile yet.
    """
    import sciv_play as play
    if neutral:session.enter_neutral(entry)
    else:
        session.command('loadfile',session.base)
        session.write({0x86:entry['room'],0x70:3,0x88:session.quest})
        for _ in range(900):
            play.advance(session.lua,1)
            if session.read(0x70)==5 and session.read(0x3c)==0:break
        else:raise RuntimeError('Der Boss-Grafikraum wurde nicht vollständig geladen.')
        pointer=session.word(0,0xd81b+entry['room']*2)
        for _ in range(1024):
            if session.word(5,pointer)==0xffff:break
            pointer+=6
        else:raise RuntimeError('Bossraum hat keinen gültigen Spawn-Abschluss.')
        session.write({0x94:pointer,0x96:pointer})
        session.lua.eval('for a=0x580,0xebf do mainmemory.write_u8(a,0) end')
        session.entry=entry;session.target=entry.get('main_slot',0x580);session.elapsed=0
    # Allow the room's palette/VRAM work to settle before running state0 once.
    session.step(24)
    session.write({0x590:0x2a,0x594:entry['controller_variant'],0x58a:entry['x'],0x58e:entry['y'],0x592:0})
    for _ in range(900):
        snapshot=session.step(1)
        if session.read(0x3c)==0 and session.read(0x590)==0x2a and session.read(0x592)==1:
            # $1A12 belongs to the graphics loader's DP block $1A00. It is
            # NOT an audio wait: clearing it truncates pending VRAM transfers.
            # Shorten only the actor countdown, then let state1 wait naturally.
            session.write({0x5a4:0})
        if session.read(entry.get('main_slot',0x580)+0x10)==entry.get('main_type',entry['type']):break
    else:raise RuntimeError('Der originale Bosscontroller hat den Hauptkörper nicht gestartet.')
    # Some original introductions spend over a hundred fields with pose zero.
    # Keep the UI loading until the group actually draws, without forcing AI.
    for _ in range(240):
        snapshot=session.step(1)
        if snapshot['actors']:break
    else:
        if entry['type']!=0x81:raise RuntimeError('Der Boss hat noch keinen sichtbaren nativen Körper oder Teil gezeichnet.')
    if entry['type']==0x81:
        for _ in range(900):
            snapshot=session.step(1)
            if session.read(0x1e84)&7==7:
                snapshot=session.step(2);break
        else:raise RuntimeError('Der native Mode7-Körper wurde nicht vollständig initialisiert.')
    return snapshot
