"""Download pinned public reference-conditioning and local matting weights.

Only public model downloads; no images, keys, or user files are uploaded.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.request

os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    from huggingface_hub import snapshot_download
    root = args.out
    root.mkdir(parents=True, exist_ok=True)
    revision = '018e402774aeeddd60609b4ecdb7e298259dc729'
    ip = root / 'ip-adapter'
    snapshot_download('h94/IP-Adapter', revision=revision, token=False,
        allow_patterns=['models/image_encoder/config.json', 'models/image_encoder/model.safetensors',
                        'sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors', 'README.md'],
        local_dir=str(ip), max_workers=2)
    (ip / 'download-source.json').write_text(json.dumps({
        'repo': 'h94/IP-Adapter', 'revision': revision, 'uploaded': False}, indent=2), encoding='utf-8')
    path = root / 'isnet-anime.onnx'
    url = 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-anime.onnx'
    if not path.exists():
        temporary = path.with_suffix('.part')
        urllib.request.urlretrieve(url, temporary)
        temporary.replace(path)
    if hashlib.md5(path.read_bytes()).hexdigest() != '6f184e756bb3bd901c8849220a83e38e':
        raise ValueError('Matting model does not match upstream rembg checksum')
    (root / 'matting-source.json').write_text(json.dumps({
        'url': url, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'upstream_md5_verified': True, 'uploaded': False}, indent=2), encoding='utf-8')
    print('Reference and matting models ready:', root, flush=True)


if __name__ == '__main__':
    main()
