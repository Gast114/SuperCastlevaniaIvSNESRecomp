"""Original timing remains available; boosted busy scenes retain one logic update/field."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import sciv_test_support as sciv


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','stress','death','quiet'):p.add_argument('--'+name,type=Path,required=True)
    sciv.add_build_arg(p);a=p.parse_args();build=sciv.build_dir(a);work=sciv.work_dir(build,'cpu-performance-')
    reports={};folders={}
    for label,fixture,mode,death in [('original',a.stress,0,0),('fastrom',a.stress,1,0),('boost',a.stress,2,0),
        ('death-original',a.death,0,120),('death-boost',a.death,2,120),('quiet-original',a.quiet,0,0),('quiet-boost',a.quiet,2,0)]:
        cmd=[sys.executable,str(sciv.ROOT/'tools/profile_sciv_fps.py'),'--rom',str(a.rom.resolve()),
            '--build-dir',str(build),'--fixture',str(fixture.resolve()),'--frames','240','--unthrottled','--cpu-timing',str(mode)]
        if death:cmd+=['--medusa-death-at',str(death)]
        result=subprocess.run(cmd,capture_output=True,text=True,check=True)
        (work/(label+'.log')).write_text(result.stdout+result.stderr)
        folder=Path(result.stdout.splitlines()[0]);folders[label]=folder
        report=json.loads((folder/'report.json').read_text());reports[label]=report
        assert report['performance']['cpu_timing']==mode
        assert report['performance']['rom_cost']==(8 if mode==0 else 6 if mode==1 else 4)
        assert report['performance']['wram_cost']==(4 if mode==2 else 8)
        assert report['performance']['mmio_cost']==6
        assert json.loads((folder/'performance_settings.json').read_text())['cpu_timing']==mode
        print(label,report['logic_updates'],report['comparable_gameplay_intervals'],flush=True)
    assert reports['original']['logic_repeats']>0
    assert reports['death-original']['logic_repeats']>0
    for label in ('boost','death-boost'):
        assert reports[label]['logic_repeats']==0,(label,'lost logic updates')
        assert reports[label]['logic_updates']==reports[label]['comparable_gameplay_intervals']
    assert reports['death-boost']['max_medusa_fragments']>0
    assert reports['quiet-original']['state']==reports['quiet-boost']['state'],'boost changed quiet-scene simulation'
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(folders['quiet-original']/'native.png')==sha(folders['quiet-boost']/'native.png'),'quiet scene native pixels changed'
    (work/'report.json').write_text(json.dumps({'passed':True,'runs':{k:str(v) for k,v in folders.items()},
        'updates':{k:[v['logic_updates'],v['comparable_gameplay_intervals']] for k,v in reports.items()}},indent=2))
    print('PASS: retail/FastROM/boost bus scope and persistence; busy/death stalls removed; quiet gameplay and native pixels identical')


if __name__=='__main__':main()
