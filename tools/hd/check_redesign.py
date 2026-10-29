"""Check PNG dimensions/alpha against source geometry; never certify design or stone count."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image


def check(source, result):
    with Image.open(source) as im:
        expected_size=im.size
        expected=np.array(im.convert('RGBA'))
    with Image.open(result) as im:
        size=im.size;mode=im.mode;fmt=im.format
        actual=np.array(im.convert('RGBA'))
    dimensions=size==expected_size
    alpha_equal=dimensions and np.array_equal(expected[:,:,3],actual[:,:,3])
    changed_alpha=int(np.count_nonzero(expected[:,:,3]!=actual[:,:,3])) if dimensions else None
    checks=dict(png=fmt=='PNG',rgba=mode=='RGBA',dimensions=dimensions,alpha_exact=bool(alpha_equal))
    return dict(technical_pass=all(checks.values()),checks=checks,expected_size=expected_size,
        actual_size=size,mode=mode,changed_alpha_pixels=changed_alpha,
        source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        result_sha256=hashlib.sha256(Path(result).read_bytes()).hexdigest(),
        geometry_stone_count_style_and_seams='NOT VERIFIED: separate visual/structural review required',
        overall_approved=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--result',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    report=check(a.source,a.result)
    a.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Technical file checks: '+('PASS' if report['technical_pass'] else 'FAIL'))
    print(json.dumps(report['checks']))
    print('Style, stone positions/count and architectural seams still need review.')
    print('Report: '+str(a.report))
    raise SystemExit(0 if report['technical_pass'] else 1)
