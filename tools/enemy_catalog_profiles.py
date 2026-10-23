"""Original boss-controller profiles, separate from ordinary actor placement.

The verified USA ROM dispatches $80..$8D through $01:A59C. $18..$29
are not boss IDs. Controller $2A is internal scene setup, never artist art.
Profiles below enter retail controller states; motion and child creation
remain entirely in the original engine. Room context is provisional unless
the exact controller record exists in $05 placement data.
"""

# variant, actor, native initializer, initial x/y, room, placement proved
_BOSSES=(
    (0x80,0x80,0x942b,0x0780,0x0040,4,False),
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
            controller_variant=variant&0x7f if actor==0x80 else variant,
            original_controller_variant=variant,original_room=original_room,
            initializer=0x020000|initializer,
            room=room,x=x,y=y,flags=0x8000,record=record,
            context_provisional=not placed,
            name=f'Boss {actor:02X} · '+('BG/Mode7-Kontext offen' if actor==0x81 else
                'experimenteller Kontext'),
            coverage_note=('Experimenteller Testkontext Raum 4; vollständige OBJ-Zuordnung im Originalraum 7 noch offen.'
                if actor==0x80 else 'Körper wird über BG/Mode7 und eigene Skripte dargestellt; OBJ-PNGs allein reichen nicht.'
                if actor==0x81 else 'Sichtbarer Körper als Actor 09 belegt; weitere Angriffs-/Todeszustände noch unvollständig.'
                if actor==0x8b else 'Sichtbare native OBJ-Posen belegt; kein vollständiger Angriff-/Todeskatalog.'),
            main_slot=0xd80 if actor in (0x83,0x88,0x8b,0x8c) else 0x580,
            main_type=9 if actor==0x8b else actor,
            # 81 needs BG/Mode7; 8B's visible body is native actor 09.
            preview_verified=actor!=0x81,
            child_types={0x80:[3,4],0x83:[1,2,6],0x84:[3,5],
                0x85:[1],0x86:[1,4],0x87:[],0x88:[],0x89:[1,3,5,7],
                0x8a:[1,2,7],0x8b:[1,4,8,9],0x8c:[1,3]}.get(actor,[])))
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
    slot=entry.get('main_slot',0xd80 if entry['type'] in (0x83,0x88,0x8c) else 0x580)
    if session.read(slot+0x10)==entry.get('main_type',entry['type']):
        x=session.read(slot+0xa);y=session.read(slot+0xe)
        if y>=32768:y-=65536
        session.target=slot
    else:x,y=entry['x'],entry['y']
    native_camera(session,max(0,x-128),max(0,y-112))
    session.write({0x54a:max(32,x+getattr(session,'direction',-1)*64),0x54e:max(64,y)})


def spawn_boss(session,entry):
    """Start a retail boss through its own asset-loading controller.

    Uses an isolated NativeSession. Skips the music wait only, then executes
    original controller state 2 and native AI. It does not invent boss poses.
    Type82 is a script-generated actor and 8D has a separate final-scene
    initializer; neither is a complete standalone profile yet.
    """
    import sciv_play as play
    seed=dict(entry,type=0x2a,variant=entry['controller_variant'],boss=False)
    session.spawn(seed)
    x,y=entry['x'],entry['y']
    hold_boss_stage(session,entry)
    session.write({0x54a:max(32,x-96),0x54e:176})
    pointer=session.word(0,0xd81b+entry['room']*2)
    for _ in range(1024):
        if session.word(5,pointer)==0xffff:break
        pointer+=6
    else:raise RuntimeError('Bossraum hat keinen gültigen Spawn-Abschluss.')
    # Original state0 has cleared actor slots and loaded the boss graphics
    # descriptor from $01:B9D6 in session.spawn; never write guessed VRAM.
    session.write({0x592:2,0x5a4:0,0x1a12:0,0x5a:0,0x6a:0,
                   0x94:pointer,0x96:pointer})
    native_camera(session,max(0,x-160),0)
    play.advance(session.lua,4)
    session.entry=entry;session.target=entry.get('main_slot',0x580);session.elapsed=0
    snapshot=session.snapshot()
    if entry.get('preview_verified'):
        for _ in range(32):
            if any(a['type']==entry.get('main_type',entry['type']) for a in snapshot['actors']):break
            snapshot=session.step(1)
    return snapshot
