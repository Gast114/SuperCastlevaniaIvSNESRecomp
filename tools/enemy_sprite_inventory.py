"""ROM-bound, code-referenced actor metasprite/animation metadata.

This does not manufacture PNGs or native motion. It follows retail actor
handler code and its bounded local state tables, then decodes only immediate
pose stores and pointers passed to the two verified animation routines.
Unknown indirect code/data remains explicitly uncovered.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'snesrecomp/recompiler'))
import snes65816 as cpu

ROM_SHA256='0ef6f4cce5a2273fa49fe1ce724e0048a8e39c91da6b00dbb693fe1ba909177d'
ANIMATION_ROUTINES={0x02b069:'looping',0x02d65f:'terminating'}
# Generic dispatch, room loading, rendering and system services are not
# actor-owned code. Their data must not be re-labelled as every enemy's art.
SYSTEM_CALLS={0x008000,0x008131,0x008189,0x0081b8,0x008584,0x00859e,
    0x0085e3,0x008771,0x008c59,0x008e40,0x008e56,0x0090e6,0x0090e9,
    0x00c9cb,0x00d3ec,0x00d3fa,0x00d4d7,0x00d6f0,0x00dc43,
    0x0280dd,0x0280e8,0x02810f,0x028405}


def offset(address):
    bank=address>>16;addr=address&0xffff
    if addr<0x8000 or bank>=0x20:raise ValueError('Adresse liegt nicht in der ROM.')
    return bank*0x8000+(addr&0x7fff)


def word(rom,address):
    at=offset(address)
    return int.from_bytes(rom[at:at+2],'little')


def parse_metasprite(rom,pose):
    """Verified bank04 OBJ format: count then signed xy/tile-attribute records."""
    if not 0x8000<=pose<0x10000:return None
    at=offset(0x040000|pose);count=rom[at]
    if not 1<=count<=32 or at+1+count*4>0x28000:return None
    parts=[]
    for index in range(count):
        row=rom[at+1+index*4:at+5+index*4]
        x=int.from_bytes(row[:1],'little',signed=True)
        y=int.from_bytes(row[1:2],'little',signed=True)
        attr=int.from_bytes(row[2:4],'little');size=16 if attr&0x2000 else 8
        parts.append(dict(index=index,x=x,y=y,size=size,tile_attr=attr))
    return dict(pose=pose,address=0x040000|pose,parts=parts,
        bounds=[min(p['x'] for p in parts),min(p['y'] for p in parts),
                max(p['x']+p['size'] for p in parts),max(p['y']+p['size'] for p in parts)])


def parse_animation(rom,address,routine=0x02b069,max_frames=256):
    """Decode an actual pointer passed to a known retail animation reader."""
    if routine not in ANIMATION_ROUTINES:return None
    frames=[]
    for index in range(max_frames):
        source=address+index*4
        if source&0xffff<0x8000 or source>>16!=address>>16:return None
        pose=word(rom,source)
        if pose==0xffff or (pose==0 and routine==0x02d65f):
            if not frames:return None
            return dict(address=address,routine=routine,loop=pose==0xffff,
                terminal=pose,frames=frames)
        duration=word(rom,source+2)
        if not 1<=duration<=0x7fff or parse_metasprite(rom,pose) is None:return None
        frames.append(dict(pose=pose,duration=duration,source=source))
    return None


def _state_table(rom,base,bank):
    """Bounded adjacent 16-bit state table ending at its earliest handler.

    Unlike scanning arbitrary words, this is called only after an actual
    indexed load feeds native JMP($0000). No distant guessed table end.
    """
    if base&0xffff<0x8000:return []
    minimum=0x10000;targets=[];start=base&0xffff
    for index in range(128):
        position=start+index*2
        if position>=minimum:
            return targets if position==minimum else []
        target=word(rom,(base&0xff0000)|position)
        if not start<target<0x10000:
            # Some tables are followed by a tiny default return stub before
            # the first listed handler, e.g. bone $0C:FDF0 → stub FDF8.
            gap=minimum-position
            if targets and 0<gap<=16:
                pc=position
                while pc<minimum:
                    ins=cpu.decode_insn(rom,offset((bank<<16)|pc),pc,bank,0,0)
                    if ins is None:break
                    pc+=ins.length
                    if ins.mnem in ('RTS','RTL') and pc==minimum:return targets
            # A second dispatcher/helper can sit between a short pointer run
            # and its first handler. Stop at the first non-forward pointer;
            # only states proved reachable by writes to $12 will be used.
            return targets if targets and 0<gap<=256 else []
        minimum=min(minimum,target)
        if minimum-start>256:return []
        targets.append((bank<<16)|target)
    return []


def _index_values(history,register):
    """Finite byte offsets explicitly bounded by native AND/shift code."""
    transfer='TAY' if register=='Y' else 'TAX'
    positions=[i for i,row in enumerate(history) if row[1]==transfer]
    if not positions:return None
    end=positions[-1];starts=[i for i,row in enumerate(history[:end]) if row[1]=='AND' and row[2]==cpu.IMM and row[3]<256]
    if not starts:return None
    begin=starts[-1];mask=history[begin][3]
    values={n for n in range(mask+1) if n&mask==n}
    if len(values)>64:return None
    for _,name,mode,operand in history[begin+1:end]:
        if name=='LSR':values={v>>1 for v in values}
        elif name=='ASL':values={(v<<1)&65535 for v in values}
        elif name=='INC' and mode==cpu.ACC:values={(v+1)&65535 for v in values}
        elif name in ('CLC','SEC','PHA','PHX','PHY'):pass
        else:return None
    # A comparison after TAY/TAX and before the indexed read can narrow the
    # byte offsets further on this fallthrough path.
    bound=None
    for _,name,mode,value in history[end+1:]:
        if name in ('JSR','JSL','LDY','INY','DEY','TXY','PLY'):return None
        if name=='CMP' and mode==cpu.IMM:bound=value
        elif name=='BCS' and bound is not None:values={v for v in values if v<bound}
    return sorted(values) if values and max(values)<=510 else None


def actor_inventory(rom,actor,max_instructions=6000):
    """Potential native poses reachable from one exact retail actor handler.

    Static reachability is not an observed action or a complete mapping of
    multipart children; every entry carries its producer instruction.
    """
    table=0x01a41c+actor*3 if actor<128 else 0x01a59c+(actor&0x7f)*3
    at=offset(table);handler=int.from_bytes(rom[at:at+3],'little')
    result=dict(type=actor,handler=handler,pose_bank=4,animations=[],direct_poses=[],
        poses=[],unresolved_dispatches=[],code_instruction_count=0,truncated=False,
        evidence='static native actor handler reachability; not observed execution')
    if handler&0xffff<0x8000 or handler>>16>0x1f:
        result['unresolved_dispatches'].append(dict(address=handler,reason='invalid handler'))
        return result
    queue=deque([(handler,0,0,[])]);seen=set();animations={};poses={};unresolved=set()
    edges={};state_dispatches={};state_writes={};dynamic_state_writes=set()
    while queue and len(seen)<max_instructions:
        pc,m,x,history=queue.popleft();a=None;scratch=None;table_load=None;comparison=None;data_bank=1
        history=list(history);indexed=None
        while len(seen)<max_instructions:
            key=(pc,m,x)
            if key in seen:break
            if pc&0xffff<0x8000 or pc>>16>0x1f:break
            seen.add(key)
            try:ins=cpu.decode_insn(rom,offset(pc),pc&0xffff,pc>>16,m,x)
            except (ValueError,IndexError):break
            if ins is None:break
            history.append((pc,ins.mnem,ins.mode,ins.operand));history=history[-18:]
            name,mode,value=ins.mnem,ins.mode,ins.operand
            after=(pc&0xff0000)|((pc+ins.length)&0xffff)
            edges.setdefault(pc,set()).add(after)
            if name in ('REP','SEP'):
                if value&0x20:m=0 if name=='REP' else 1
                if value&0x10:x=0 if name=='REP' else 1
            if name=='LDA':
                indexed=None
                a=value if mode==cpu.IMM else actor if mode in (cpu.DP_X,cpu.ABS_X) and value==0x10 else None
                comparison=a==0 if a is not None else None
                if mode in (cpu.LONG_X,cpu.ABS_X,cpu.ABS_Y) and value&0xffff>=0x8000:
                    table_load=value if mode==cpu.LONG_X else (data_bank<<16)|value
                    indices=_index_values(history[:-1],'Y' if mode==cpu.ABS_Y else 'X')
                    if indices:indexed=(table_load,indices,pc)
            elif name=='CMP':comparison=(a==value) if a is not None and mode==cpu.IMM else None
            elif name in ('AND','ORA','EOR','ADC','SBC','ASL','LSR','ROL','ROR','INC','DEC','PLA','TXA','TYA','XBA'):
                indexed=None
                if name=='AND' and a is not None and mode==cpu.IMM:a&=value
                elif name=='ORA' and a is not None and mode==cpu.IMM:a|=value
                elif name=='EOR' and a is not None and mode==cpu.IMM:a^=value
                else:a=None
                comparison=None
            if name=='STA' and value==0:
                if mode==cpu.DP:scratch=(data_bank<<16)|a if a is not None else None
                if mode in (cpu.DP_X,cpu.ABS_X) and a is not None and parse_metasprite(rom,a):
                    poses.setdefault(a,[]).append(dict(instruction=pc,kind='immediate native pose store'))
                if mode in (cpu.DP_X,cpu.ABS_X) and indexed:
                    base,indices,producer=indexed
                    for index in indices:
                        pose=word(rom,base+index)
                        if parse_metasprite(rom,pose):
                            poses.setdefault(pose,[]).append(dict(instruction=pc,load_instruction=producer,
                                table=base,index=index,kind='native pose table with code-bounded index'))
            if name=='STY' and value==0 and mode in (cpu.DP_X,cpu.ABS_X):
                for producer,op,opmode,operand in reversed(history[:-1]):
                    if op=='LDY' and opmode==cpu.IMM:
                        if parse_metasprite(rom,operand):poses.setdefault(operand,[]).append(
                            dict(instruction=pc,load_instruction=producer,kind='immediate native Y pose store'))
                        break
                    if op in ('LDY','TAY','TXY','PLY','INY','DEY','JSR','JSL'):break
            if mode in (cpu.DP_X,cpu.ABS_X) and value==0x12:
                if name=='STA':
                    if a is not None and a<128:state_writes[pc]=('set',a)
                    else:dynamic_state_writes.add(pc)
                elif name=='STZ':state_writes[pc]=('set',0)
                elif name=='INC':state_writes[pc]=('delta',1)
                elif name=='DEC':state_writes[pc]=('delta',-1)
            if name=='PLB' and len(history)>=2 and history[-2][1]=='PHA' and a is not None:data_bank=a&255
            if name in ('JSR','JSL'):
                target=value if name=='JSL' else (pc&0xff0000)|value
                if mode in (cpu.INDIR_X,cpu.INDIR_DPX):
                    unresolved.add(pc)
                elif target in ANIMATION_ROUTINES:
                    animation=parse_animation(rom,scratch,target) if scratch else None
                    if animation:
                        animation=dict(animation,evidence=[dict(instruction=pc,kind='native animation-reader call')])
                        animations[(scratch,target)]=animation
                        for frame in animation['frames']:
                            poses.setdefault(frame['pose'],[]).append(dict(instruction=pc,animation=scratch,kind='native animation table'))
                elif target not in SYSTEM_CALLS:queue.append((target,m,x,[]))
                if target not in SYSTEM_CALLS and target not in ANIMATION_ROUTINES:
                    edges[pc].add(target)
                a=None;comparison=None
            if name in ('JMP','JML'):
                edges[pc].clear()
                if mode==cpu.ABS:
                    destination=(pc&0xff0000)|value;queue.append((destination,m,x,history));edges[pc].add(destination)
                elif mode==cpu.LONG:queue.append((value,m,x,history));edges[pc].add(value)
                else:
                    recent=history[-6:]
                    fed_by_index=any(h[1]=='LDA' and h[2] in (cpu.LONG_X,cpu.ABS_X,cpu.ABS_Y) for h in recent)
                    targets=_state_table(rom,table_load,pc>>16) if table_load and fed_by_index else []
                    if targets:
                        queue.extend((t,m,x,[]) for t in targets)
                        if any(h[1]=='LDA' and h[2] in (cpu.DP_X,cpu.ABS_X) and h[3]==0x12 for h in history):
                            state_dispatches[pc]=targets
                        else:edges[pc].update(targets)
                    else:unresolved.add(pc)
                break
            if name in ('RTS','RTL','RTI','BRK','COP','STP'):
                edges[pc].clear();break
            if mode in (cpu.REL,cpu.REL16):
                target=(pc&0xff0000)|value
                if name in ('BRA','BRL'):
                    queue.append((target,m,x,history));edges[pc]={target};break
                take=comparison if name=='BEQ' else not comparison if name=='BNE' and comparison is not None else None
                if take is not False:queue.append((target,m,x,history));edges[pc].add(target)
                if take is True:edges[pc].discard(after);break
            pc=after
    result['code_instruction_count']=len(seen);result['truncated']=bool(queue)
    death_actor=rom[offset(0x01ae00+actor)] if actor<128 else None
    death_state=rom[offset(0x01ae80+actor)] if actor<128 else None
    states={0}
    if death_actor==actor and death_state is not None and death_state<128:states.add(death_state)
    state_bound=max((len(t) for t in state_dispatches.values()),default=128)
    state_limit=max(max_instructions*4,len(edges)*state_bound*2)
    reach=set();pending=deque((handler,s) for s in states);state_seen=set()
    while pending and len(state_seen)<state_limit:
        address,state=pending.popleft()
        if (address,state) in state_seen:continue
        state_seen.add((address,state));reach.add(address)
        if address in state_writes:
            kind,value=state_writes[address];new=value if kind=='set' else state+value
            if 0<=new<state_bound and new not in states:
                states.add(new);pending.append((handler,new))
        if address in state_dispatches:
            targets=state_dispatches[address]
            if state<len(targets):pending.append((targets[state],state))
        pending.extend((next_address,state) for next_address in edges.get(address,()))
    result['reachable_states']=sorted(states)
    result['state_analysis_truncated']=bool(pending)
    result['dynamic_state_writes']=[p for p in sorted(dynamic_state_writes) if p in reach]
    result['family_candidate_poses']=sorted(poses)
    poses={p:[e for e in evidence if e['instruction'] in reach] for p,evidence in poses.items()}
    poses={p:e for p,e in poses.items() if e}
    result['animations']=[a for a in animations.values() if any(e['instruction'] in reach for e in a['evidence'])]
    result['direct_poses']=[dict(pose=p,evidence=e) for p,e in sorted(poses.items())]
    result['poses']=sorted(poses)
    result['unresolved_dispatches']=[dict(address=p,reason='indirect target not statically bounded') for p in sorted(unresolved)]
    if actor<128:
        result['native_death_actor']=rom[offset(0x01ae00+actor)]
        result['native_death_state']=rom[offset(0x01ae80+actor)]
    return result


def inventory(rom,actors=None,max_instructions=6000):
    rom=Path(rom).read_bytes() if not isinstance(rom,(bytes,bytearray)) else bytes(rom)
    if len(rom)!=0x100000 or hashlib.sha256(rom).hexdigest()!=ROM_SHA256:
        raise ValueError('Inventar benötigt die ungeheaderte USA-ROM des Projekts.')
    cpu.set_rom_mapping('lorom')
    rows=[actor_inventory(rom,a,max_instructions) for a in (actors if actors is not None else range(1,142))]
    return dict(schema='sciv native actor sprite inventory v1',rom_sha256=ROM_SHA256,
        metadata_only=True,actors=rows,
        special_rendering={
            '81':dict(kind='BG/Mode7',initializer=0x05e6c7,main_actor_metasprite=False,
                evidence='Native initializer sets Mode7 matrix 1EA6/1EA8 and loads descriptor01:F349.'),
            '82':dict(kind='script-generated boss/scene actor',handler=0x02e250,
                standalone_profile=False),
            '8D':dict(kind='final scene',initializer=0x0295ca,handler=0x03bfe7,
                standalone_profile=False,required_camera_x=0)},
        limits=['Static reachability is not a runtime pose verification.',
            'Only directly referenced standard animation tables are decoded; unresolved indirect data remains uncovered.',
            'Palette/tile resources and multipart aliases still require the original native scene.',
            'No completeness claim for every action, transformed BG body or generated child actor.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',type=Path,default=ROOT/'Super Castlevania IV (USA).sfc')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--actors',help='Comma-separated hexadecimal IDs')
    parser.add_argument('--max-instructions',type=int,default=6000)
    args=parser.parse_args()
    actors=[int(a,16) for a in args.actors.split(',')] if args.actors else None
    data=inventory(args.rom,actors,args.max_instructions)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'{len(data["actors"])} actor handlers; {sum(len(a["poses"]) for a in data["actors"])} actor/pose references; '+str(args.output))


if __name__=='__main__':main()
