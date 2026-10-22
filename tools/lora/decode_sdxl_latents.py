"""Decode saved SDXL latents locally with only the VAE resident on the GPU.

Separating this step avoids holding UNet, ControlNet and CPU offload copies
alongside the fp32 VAE on a machine with shared graphics memory.
"""
import argparse
import json
import os
from pathlib import Path
import time

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--device', default='cuda', choices=('cpu', 'cuda', 'auto'))
    args = parser.parse_args()
    output_dir = args.out or args.source
    sources = sorted(args.source.glob('*-latents.safetensors'))
    if not sources:
        raise ValueError('No saved latents')
    for source in sources:
        target = output_dir / (source.name.removesuffix('-latents.safetensors') + '.png')
        if target.exists():
            raise FileExistsError(target)
    output_dir.mkdir(parents=True, exist_ok=True)
    progress = {'status': 'loading', 'pid': os.getpid(), 'images': [], 'uploaded': False}
    def report():
        (output_dir / 'decode.json').write_text(json.dumps(progress, indent=2), encoding='utf-8')
    report()
    import torch
    from diffusers import AutoencoderKL
    from diffusers.image_processor import VaeImageProcessor
    from diffusers.models.attention_processor import AttnProcessor
    from safetensors.torch import load_file
    from compute import configure
    device, details = configure(torch, args.device, 0)
    progress.update(details)
    vae = AutoencoderKL.from_pretrained(str(args.model.resolve()), subfolder='vae',
        variant='fp16', torch_dtype=torch.float32, local_files_only=True).to(device)
    vae.set_attn_processor(AttnProcessor())
    vae.enable_tiling()
    vae.tile_sample_min_size = 512
    vae.tile_latent_min_size = 64
    processor = VaeImageProcessor(vae_scale_factor=2 ** (len(vae.config.block_out_channels) - 1))
    records = []
    with torch.inference_mode():
        for source in sources:
            output = output_dir / (source.name.removesuffix('-latents.safetensors') + '.png')
            if output.exists():
                raise FileExistsError(output)
            tick = time.monotonic()
            progress.update(status='decoding', image=output.name)
            report()
            latent = load_file(source)['latents'].to(device=device, dtype=torch.float32)
            if vae.config.latents_mean is not None and vae.config.latents_std is not None:
                mean = torch.tensor(vae.config.latents_mean, device=device).view(1, 4, 1, 1)
                std = torch.tensor(vae.config.latents_std, device=device).view(1, 4, 1, 1)
                latent = latent * std / vae.config.scaling_factor + mean
            else:
                latent = latent / vae.config.scaling_factor
            decoded = vae.decode(latent, return_dict=False)[0]
            processor.postprocess(decoded, output_type='pil')[0].save(output)
            records.append({'image': output.name, 'latent': source.name,
                            'seconds': time.monotonic() - tick})
            print('Decoded:', output.name, records[-1]['seconds'], flush=True)
            progress['images'] = records
            report()
            del latent, decoded
    progress.update(status='complete',
        vae_dtype='float32', vae_attention='gpu_matrix', images=records,
        peak_gpu_allocated_bytes=torch.cuda.max_memory_allocated(device)
            if device.type == 'cuda' else None, tile_sample_size=512)
    report()


if __name__ == '__main__':
    main()
