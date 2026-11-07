"""Real native boss effects must reach the live SPC/DSP, not just a private copy."""
import json
import os
from pathlib import Path
import struct
import tempfile
import wave
import numpy as np
from enemy_workshop_native import ROOT,play
from level_assets import Assets,ensure_room
from level_parts import builtin_parts,repeat_part
from level_project import Project,paint
from level_playtest import Playtest


def output(session,path):
    session.command('audio_dump',path);data=path.read_bytes()
    magic,count,write,read=struct.unpack_from('<4I',data)
    assert magic==0x41345643 and count==8192 and len(data)==148+count*4
    ring=np.frombuffer(data,dtype='<i2',offset=148).reshape(count,2)
    pcm=ring[(np.arange(2048,dtype=np.int64)+write-2048)%count].copy()
    with wave.open(str(path.with_suffix('.wav')),'wb') as wav:
        wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(32040);wav.writeframes(pcm.tobytes())
    return dict(ack=data[16],pcm=pcm,voice_registers=data[20:148].hex(),write=write,read=read)


def check():
    # Keep callbacks enabled even on a workstation without a connected output.
    # This verifies the native output data/handshake, not a subjective hearing test.
    os.environ.setdefault('SDL_AUDIODRIVER','dummy')
    folder=Path(tempfile.mkdtemp(prefix='boss-audio-',dir=ROOT/'artwork-local/level-editor/tests'))
    print(folder,flush=True);report=dict(passed=False,audio_driver=os.environ['SDL_AUDIODRIVER'],checks=[])
    asset=Assets(ensure_room(2));floor=repeat_part(next(p for p in builtin_parts({2:asset}) if p['id']=='platform-a03'),16)
    def project(hp=333):
        p=Project();r=p.data['rooms'][0];r['spawn']=[50,165]
        for x in range(0,r['width'],floor['width']):paint(r,'front',x,24,floor['tiles'],floor['collision'],floor['width'])
        r['actors']=[dict(id='boss',type=137,variant=0,x=150,y=160,flags=32768,boss_mode='free',stats=dict(hp=hp,contact_damage=7))]
        return p
    def status(s):return json.loads(s.command('level_status'))
    def passed(message):report['checks'].append(message);print('PASS:',message,flush=True)
    try:
        pictures={}
        for hit in (False,True):
            g=Playtest(project().data,folder/('contact' if hit else 'control'),fast=False)
            try:
                assert not g.audio_unavailable
                s=g.session;before=status(s)['boss_sound_forwarded']
                s.write({0xbc:0 if hit else 32767,0x13f4:16,0x54a:150 if hit else 50,0x54e:165})
                play.advance(s.lua,4);v=status(s)
                assert s.read(0x13f4)==(9 if hit else 16)
                if hit:assert v['boss_sound_forwarded']>before and v['boss_sound_last']==0x95,v
                play.advance(s.lua,8)
                sample=output(s,folder/('contact.bin' if hit else 'control.bin'));pictures[hit]=sample
                print('contact',hit,'ack',sample['ack'],'forwarded',status(s)['boss_sound_forwarded'],flush=True)
                if hit:assert sample['ack']==0x95,sample['ack']
            finally:g.close()
        difference=pictures[True]['pcm'].astype(float)-pictures[False]['pcm'].astype(float)
        report['contact_pcm_difference_rms']=float(np.sqrt(np.mean(difference*difference)))
        assert report['contact_pcm_difference_rms']>100,report
        passed('Real contact damage forwards original effect $95, the live SPC acknowledges it, and actual DSP output differs from the no-contact control')

        g=Playtest(project().data,folder/'whip',fast=False)
        try:
            s=g.session
            # Enter the same active combat phase as a player who walks into
            # this boss, rather than demanding a hit response during its
            # native protected opening state.
            s.write({0xbc:0,0x13f4:16,0x54a:150,0x54e:165});play.advance(s.lua,4)
            before=status(s)['boss_sound_forwarded']
            for _ in range(24):
                a=status(s)['free_actors'][0];s.write({0xbc:32767,0x13f4:16,0x54a:max(24,a['x']-24),0x54e:165})
                play.advance(s.lua,4,('Y',));play.advance(s.lua,4)
                if status(s)['free_actors'][0]['hp']<333:break
            v=status(s);assert v['free_actors'][0]['hp']<333
            assert v['boss_sound_forwarded']>before and v['boss_sound_last']==0x76,v
            acknowledgements=[]
            for frame in range(12):
                sample=output(s,folder/f'whip-{frame}.bin');acknowledgements.append(sample['ack'])
                if sample['ack']==0x76:break
                play.advance(s.lua,1)
            assert 0x76 in acknowledgements,acknowledgements
            assert np.max(np.abs(sample['pcm'].astype(np.int32)))>100
            passed('A real native whip hit reduces boss HP and original impact effect $76 reaches the live SPC and non-silent DSP output')
        finally:g.close()
        report['passed']=True
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:(folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':check()
