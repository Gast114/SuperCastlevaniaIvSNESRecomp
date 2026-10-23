"""Observe retail boss-controller variants in private native sessions.

This is investigation evidence, not a claim every boss profile is complete.
No player configuration, saves or source artwork is modified.
"""
import argparse
import json
from enemy_workshop_native import NativeSession, play


def raw_actors(session):
    text=session.lua.eval('local t={} for a=0x580,0xebf,0x40 do '
        'local id=mainmemory.read_u16_le(a+0x10) if id~=0 then '
        't[#t+1]=string.format("%d,%d,%d,%d,%d,%d",a,id,'
        'mainmemory.read_u16_le(a),mainmemory.read_u16_le(a+0x12),'
        'mainmemory.read_u16_le(a+0xa),mainmemory.read_u16_le(a+0xe)) '
        'end end return table.concat(t,";")')['values'][0]
    return [dict(zip(('slot','type','pose','state','x','y'),map(int,row.split(','))))
            for row in text.split(';') if row]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variants',default='0,1,2,3,4,5,6,7,8,9,10,11,12')
    parser.add_argument('--follow',action='store_true',help='Keep actual native boss and hero inside the comparison camera')
    parser.add_argument('--profiles',action='store_true',help='Exercise integrated workshop boss profiles and capture actual C++ matches')
    parser.add_argument('--frames',type=int,default=320)
    args=parser.parse_args()
    # Existing native actor-$2A records give exact contexts for these variants.
    rooms={0:4,1:7,2:9,3:20,4:34,5:53,6:45,7:55,8:57,9:41,10:58,11:59,12:62}
    positions={0:(0x780,0x40),1:(0x7e0,0x78),2:(0xe80,0x80),3:(0x380,0x60),
        4:(0x180,0x60),5:(0x280,0x60),6:(0x8c0,0x75),7:(0x180,0x60),
        8:(0x180,0x60),9:(0x2b0,0x80),10:(0x280,0x60),11:(0x280,0x60),12:(0x80,0xa0)}
    session=NativeSession();report=[]
    try:
        session.start()
        for variant in map(int,args.variants.split(',')):
            x,y=positions[variant]
            entry=dict(type=0x2a,variant=variant,room=rooms[variant],x=x,y=y,flags=0x8000)
            if args.profiles:
                entry=next((e for e in session.catalog if e.get('boss') and e['controller_variant']&0x7f==variant),None)
                if entry is None:
                    report.append(dict(controller_variant=variant,unsupported=True,
                        reason='Kein abgeschlossenes separates Bossprofil.'))
                    print(variant,'not supported by isolated profile',flush=True)
                    continue
            result=dict(entry,samples=[])
            try:
                session.spawn(entry)
                # The retail loader itself loads boss graphics via $01:B9D6.
                # Skip only the music/countdown wait; original state 2 executes
                # the native boss initializer selected by the variant table.
                if not args.profiles:session.write({0x592:2,0x5a4:0,0x1a12:0,0x5a:0,0x6a:0})
                matched=[]
                for n in range(max(1,args.frames//4)):
                    if args.profiles:
                        observation=session.step(4)
                        matched.extend(a for a in observation['actors'] if a['type']==entry.get('main_type',entry['type']))
                        result['samples'].append(dict(frame=n*4,phase=session.read(0x70),boss=session.read(0xb8),actors=raw_actors(session)))
                        continue
                    actual=next((a for a in raw_actors(session) if a['type']>=128),None) if args.follow else None
                    fx=actual['x'] if actual else x
                    fy=(actual['y'] if actual['y']<32768 else actual['y']-65536) if actual else 176
                    cx=max(0,fx-128);cy=max(0,fy-112) if args.follow else 0
                    session.write({0x54a:max(32,fx-64),0x54e:max(64,fy),0x1c:cx,0x1e:cy,
                                   0x1280:cx,0x12c0:cx,0x1298:cy,0x12d8:cy})
                    play.advance(session.lua,4)
                    result['samples'].append(dict(frame=n*4,phase=session.read(0x70),boss=session.read(0xb8),actors=raw_actors(session)))
                session.command('screenshot',session.folder/f'boss-{variant:02d}.png')
                session.command('enemy_snapshot',session.folder/f'boss-{variant:02d}.json')
                result['observed_types']=sorted({a['type'] for row in result['samples'] for a in row['actors']})
                result['observed_poses']=sorted({a['pose'] for row in result['samples'] for a in row['actors'] if a['type']>=128})
                if args.profiles:
                    result['matched_poses']=sorted({a['pose'] for a in matched})
                    result['matched_main_slots']=sorted({a['slot'] for a in matched})
                    result['matched_ids']=sorted({a['id'] for a in matched})
            except Exception as error:result['error']=str(error)
            report.append(result)
            (session.folder/'boss-audit.json').write_text(json.dumps(report,indent=2))
            print(variant,result.get('observed_types'),result.get('matched_poses',result.get('observed_poses')),result.get('error',''),flush=True)
        print(session.folder,flush=True)
    finally:session.close()


if __name__=='__main__':main()
