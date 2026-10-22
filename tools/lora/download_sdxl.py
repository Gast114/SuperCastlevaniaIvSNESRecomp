"""Download a pinned public SDXL snapshot; never uploads local files or uses a token."""
import argparse
import json
import os
from pathlib import Path

os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'

from huggingface_hub import snapshot_download


REPO = 'stabilityai/stable-diffusion-xl-base-1.0'
REVISION = '462165984030d82259a11f4367a4eed129e94a7b'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--controlnet-out', type=Path)
    args = parser.parse_args()
    # Explicit component whitelist: no ONNX copies, refiner, pickle or duplicate
    # full-precision checkpoints. Safetensors only for model weights.
    files = ['model_index.json', 'scheduler/scheduler_config.json',
             'README.md', 'LICENSE.md']
    for name in ('text_encoder', 'text_encoder_2'):
        files += [name + '/config.json', name + '/model.fp16.safetensors']
    for name in ('tokenizer', 'tokenizer_2'):
        files += [name + '/' + item for item in
                  ('merges.txt', 'vocab.json', 'tokenizer_config.json', 'special_tokens_map.json')]
    for name in ('unet', 'vae'):
        files += [name + '/config.json', name + '/diffusion_pytorch_model.fp16.safetensors']
    result = snapshot_download(REPO, revision=REVISION, allow_patterns=files,
                               local_dir=str(args.out), token=False, max_workers=2)
    record = {'repo': REPO, 'revision': REVISION, 'directory': str(Path(result).resolve()),
              'uploaded': False, 'personal_authentication_used': False}
    (args.out / 'download-source.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(record), flush=True)
    if args.controlnet_out:
        control_repo = 'xinsir/controlnet-openpose-sdxl-1.0'
        control_revision = '23f966cd5cfdd3f7729c903e243d87152162d2b7'
        snapshot_download(control_repo, revision=control_revision,
                          allow_patterns=['config.json', 'diffusion_pytorch_model.safetensors', 'README.md'],
                          local_dir=str(args.controlnet_out), token=False, max_workers=1)
        (args.controlnet_out / 'download-source.json').write_text(json.dumps({
            'repo': control_repo, 'revision': control_revision, 'uploaded': False}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
