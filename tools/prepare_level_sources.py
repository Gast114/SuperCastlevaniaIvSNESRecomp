"""Prepare the complete cross-level graphics library without image viewers."""
import argparse
import json
from pathlib import Path
import time
from level_assets import Assets,ensure_source,CACHE
from level_tiles import SOURCE_COUNT,source_name


def prepare():
    rows=[];start=time.monotonic()
    for n in range(SOURCE_COUNT):
        try:
            asset=Assets(ensure_source(n));row=dict(source=n,name=source_name(n),ready=True,mode=asset.meta['ppu']['bgmode']&7,blocks=asset.block_count)
        except Exception as exc:row=dict(source=n,name=source_name(n),ready=False,error=str(exc))
        rows.append(row);print(json.dumps(row,ensure_ascii=True),flush=True)
        CACHE.mkdir(parents=True,exist_ok=True);(CACHE/'sources.json').write_text(json.dumps(dict(version=1,elapsed_seconds=time.monotonic()-start,sources=rows),indent=2),encoding='utf-8')
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--ensure',action='store_true');parser.parse_args()
    raise SystemExit(0 if all(r['ready'] for r in prepare()) else 1)
