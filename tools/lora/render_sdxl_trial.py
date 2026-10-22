"""Render up to three local pose-controlled character LoRA examples, offline.

Creates RGB review pictures, not a transparent or installed game character pack.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import traceback

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--controlnet', type=Path, required=True)
    parser.add_argument('--lora', type=Path, required=True)
    parser.add_argument('--guides', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--threads', type=int, default=0)
    parser.add_argument('--device', choices=('auto', 'cpu', 'cuda'), default='auto')
    parser.add_argument('--pose', help='Render only this named pose from poses.json')
    parser.add_argument('--lora-scale', type=float, default=.85)
    parser.add_argument('--control-scale', type=float, default=.8)
    parser.add_argument('--control-end', type=float, default=.85)
    parser.add_argument('--steps', type=int, default=28)
    parser.add_argument('--offload', choices=('auto', 'none', 'model', 'group'), default='auto')
    args = parser.parse_args()
    if not 1 <= args.steps <= 100 or not 0 < args.control_end <= 1:
        raise ValueError('Invalid inference settings')
    if args.out.exists():
        raise FileExistsError('Use a new review output folder')
    args.out.mkdir(parents=True)
    progress = {'status': 'loading', 'pid': os.getpid(), 'uploaded': False}

    def report():
        temp = args.out / 'progress.tmp'
        temp.write_text(json.dumps(progress, indent=2), encoding='utf-8')
        temp.replace(args.out / 'progress.json')

    report()
    import torch
    from diffusers import ControlNetModel, DPMSolverMultistepScheduler, StableDiffusionXLControlNetPipeline
    from PIL import Image
    from safetensors.torch import save_file
    from compute import configure
    device, compute = configure(torch, args.device, args.threads)
    progress.update(compute, inference_steps=args.steps, lora_scale=args.lora_scale,
                    control_scale=args.control_scale, control_end=args.control_end)
    report()
    control = ControlNetModel.from_pretrained(str(args.controlnet.resolve()),
                                            torch_dtype=torch.bfloat16, local_files_only=True)
    pipe = StableDiffusionXLControlNetPipeline.from_pretrained(str(args.model.resolve()),
        controlnet=control, torch_dtype=torch.bfloat16, variant='fp16', local_files_only=True)
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    pipe.load_lora_weights(str(args.lora.resolve()), adapter_name='simon',
                           weight_name='pytorch_lora_weights.safetensors',
                           use_safetensors=True, local_files_only=True)
    pipe.fuse_lora(lora_scale=args.lora_scale)
    offload = args.offload
    if offload == 'auto':
        offload = 'group' if device.type == 'cuda' and compute['accelerator_memory'] < 12 * 1024**3 else 'none'
    if device.type == 'cuda':
        if offload == 'model':
            pipe.enable_model_cpu_offload(device=device)
        elif offload == 'group':
            pipe.enable_group_offload(onload_device=device, offload_type='block_level',
                                     num_blocks_per_group=1)
        else:
            pipe.to(device)
        pipe.vae.enable_tiling()
        if torch.version.hip:
            # The fp32 VAE attention hit hipErrorProfilerNotInitialized with
            # experimental RDNA 3.5 SDPA. Keep optimized BF16 UNet/ControlNet
            # attention, and use ordinary GPU matrix attention only in the VAE.
            from diffusers.models.attention_processor import AttnProcessor
            pipe.vae.set_attn_processor(AttnProcessor())
            progress['vae_attention'] = 'gpu_matrix'
    elif offload != 'none':
        raise ValueError('GPU offloading requires --device cuda')
    progress['offload'] = offload
    pose_data = json.loads((args.guides / 'poses.json').read_text(encoding='utf-8'))
    poses = [pose for pose in pose_data['poses'] if not args.pose or pose['name'] == args.pose]
    if not poses:
        raise ValueError('Unknown pose: ' + str(args.pose))
    frames = []
    for pose in poses[:3]:
        progress.update(status='rendering', pose=pose['name'], step=0)
        report()
        prompt = ('scivsimonv1, painted 2D game character, full body, three-quarter side view facing right, '
                  'muscular male warrior with long brown hair, charcoal black armor with gold edges and rivets, '
                  'short segmented battle skirt, armored bracers and tall armored boots, '
                  + pose['description'] + ', plain solid gray background, detailed painted illustration')
        negative = ('3d render, sculpture, plastic, photograph, blurry, text, logo, scenery, '
                    'extra limbs, duplicate body, cropped head, cropped feet')

        def on_step(pipeline, index, timestep, kwargs):
            progress['step'] = index + 1
            if index + 1 == args.steps:
                save_file({'latents': kwargs['latents'].detach().cpu().contiguous()},
                          args.out / (pose['name'] + '-latents.safetensors'))
            report()
            return kwargs

        tick = time.monotonic()
        try:
            image = pipe(prompt=prompt, negative_prompt=negative,
                image=Image.open(args.guides / (pose['name'] + '.png')).convert('RGB'),
                width=512, height=512, num_inference_steps=args.steps, guidance_scale=5.,
                controlnet_conditioning_scale=args.control_scale, control_guidance_end=args.control_end,
                generator=torch.Generator('cpu').manual_seed(20261021),
                callback_on_step_end=on_step).images[0]
        except Exception as exc:
            progress.update(status='failed', error=str(exc), traceback=traceback.format_exc())
            report()
            raise
        filename = pose['name'] + '.png'
        image.save(args.out / filename)
        frames.append({'image': filename, 'prompt': prompt, 'negative_prompt': negative,
                       'seconds': time.monotonic() - tick})
    progress.update(status='complete', images=frames,
        lora_sha256=hashlib.sha256((args.lora / 'pytorch_lora_weights.safetensors').read_bytes()).hexdigest(),
        note='RGB review only. Pose points approximate; native mapping and alpha cleanup pending.')
    if device.type == 'cuda':
        progress['peak_gpu_allocated_bytes'] = torch.cuda.max_memory_allocated(device)
    report()


if __name__ == '__main__':
    main()
