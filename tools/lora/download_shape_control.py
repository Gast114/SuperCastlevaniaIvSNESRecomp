"""Download a pinned public SDXL edge controller. No local images are uploaded."""
import argparse
import json
import os
from pathlib import Path

os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    from huggingface_hub import snapshot_download
    repo = 'xinsir/controlnet-canny-sdxl-1.0'
    revision = '1271357eda52d54b857c650cacb5b51144643ccb'
    snapshot_download(repo, revision=revision, token=False,
        allow_patterns=['config.json', 'diffusion_pytorch_model.safetensors', 'README.md'],
        local_dir=str(args.out), max_workers=2)
    (args.out / 'download-source.json').write_text(json.dumps({
        'repo': repo, 'revision': revision, 'uploaded': False}, indent=2), encoding='utf-8')
    print(args.out.resolve(), flush=True)


if __name__ == '__main__':
    main()
