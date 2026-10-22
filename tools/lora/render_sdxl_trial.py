"""Render local pose-controlled character LoRA examples, offline.

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
    parser.add_argument('--skip-pose', action='append', default=[],
                        help='Skip a completed calibration phase instead of generating it twice')
    parser.add_argument('--lora-scale', type=float, default=.85)
    parser.add_argument('--control-scale', type=float, default=.8)
    parser.add_argument('--control-end', type=float, default=.85)
    parser.add_argument('--steps', type=int, default=28)
    parser.add_argument('--latents-only', action='store_true',
                        help='Decode separately after releasing the large generation models')
    parser.add_argument('--offload', choices=('auto', 'none', 'model', 'group'), default='auto')
    parser.add_argument('--max-poses', type=int, default=3)
    parser.add_argument('--reference-image', type=Path)
    parser.add_argument('--ip-adapter', type=Path)
    parser.add_argument('--ip-scale', type=float, default=.6)
    parser.add_argument('--ip-mode', choices=('all', 'style'), default='all',
                        help='Style mode avoids copying the reference body posture')
    args = parser.parse_args()
    if not 1 <= args.steps <= 100 or not 0 < args.control_end <= 1:
        raise ValueError('Invalid inference settings')
    if not 1 <= args.max_poses <= 24 or bool(args.reference_image) != bool(args.ip_adapter):
        raise ValueError('Expected a bounded pose count and both reference image and IP-Adapter together')
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
    if args.reference_image:
        pipe.load_ip_adapter(str(args.ip_adapter.resolve()), subfolder='sdxl_models',
            weight_name='ip-adapter-plus_sdxl_vit-h.safetensors',
            image_encoder_folder='models/image_encoder', local_files_only=True)
        ip_scale = ({'up': {'block_0': [0., args.ip_scale, 0.]}}
                    if args.ip_mode == 'style' else args.ip_scale)
        pipe.set_ip_adapter_scale(ip_scale)
        progress.update(reference_image=str(args.reference_image.resolve()),
            reference_sha256=hashlib.sha256(args.reference_image.read_bytes()).hexdigest(),
            ip_adapter_scale=ip_scale, ip_adapter_mode=args.ip_mode)
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
    width, height = pose_data.get('canvas', [512, 512])
    poses = [pose for pose in pose_data['poses']
             if (not args.pose or pose['name'] == args.pose) and pose['name'] not in args.skip_pose]
    if not poses:
        raise ValueError('Unknown pose: ' + str(args.pose))
    conditioning = {}
    if args.reference_image:
        progress.update(status='encoding_reference')
        report()
        with torch.no_grad():
            conditioning['ip_adapter_image_embeds'] = pipe.prepare_ip_adapter_image_embeds(
                ip_adapter_image=Image.open(args.reference_image).convert('RGB'),
                ip_adapter_image_embeds=None, device=device, num_images_per_prompt=1,
                do_classifier_free_guidance=True)
        # Embeddings are reused for all poses; the large encoder is no longer
        # needed on the GPU while UNet and ControlNet generate the frames.
        pipe.image_encoder.to('cpu')
        if device.type == 'cuda':
            torch.cuda.empty_cache()
    frames = []
    if args.latents_only:
        pipe.vae.to('cpu')
        if device.type == 'cuda':
            torch.cuda.empty_cache()
    for pose in poses[:args.max_poses]:
        progress.update(status='rendering', pose=pose['name'], step=0)
        report()
        prompt = ('scivsimonv1, full body detailed painted game character, walking right in profile, '
                  'tall athletic man, shoulder-length brown hair, black and gold armor, '
                  'short battle skirt, matching smooth greaves, fitted boots, gray background. '
                  + pose['description'])
        negative = ('3d render, sculpture, plastic, photograph, blurry, text, logo, scenery, '
                    'pixel art, low resolution, soft focus, thick outlines, '
                    'extra limbs, duplicate body, cropped head, cropped feet, chibi, giant boots, '
                    'hair below shoulders, very long hair, knee pads, protruding knee guards, asymmetrical knee armor')

        def on_step(pipeline, index, timestep, kwargs):
            if device.type == 'cuda':
                # HIP launches asynchronously; otherwise progress can say
                # "35/36" while most GPU work is still queued.
                torch.cuda.synchronize(device)
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
                width=width, height=height, num_inference_steps=args.steps, guidance_scale=5.,
                controlnet_conditioning_scale=args.control_scale, control_guidance_end=args.control_end,
                generator=torch.Generator('cpu').manual_seed(20261021),
                output_type='latent' if args.latents_only else 'pil',
                callback_on_step_end=on_step, **conditioning).images[0]
        except Exception as exc:
            progress.update(status='failed', error=str(exc), traceback=traceback.format_exc())
            report()
            raise
        filename = pose['name'] + '.png'
        if not args.latents_only:
            image.save(args.out / filename)
        frames.append({'image': filename, 'prompt': prompt, 'negative_prompt': negative,
                       'rgb_pending': args.latents_only,
                       'seconds': time.monotonic() - tick})
        progress['images'] = frames
        report()
    progress.update(status='latents_complete' if args.latents_only else 'complete', images=frames,
        lora_sha256=hashlib.sha256((args.lora / 'pytorch_lora_weights.safetensors').read_bytes()).hexdigest(),
        guide_origin=pose_data.get('origin'),
        note='RGB review only; native placement and alpha cleanup pending.')
    if device.type == 'cuda':
        progress['peak_gpu_allocated_bytes'] = torch.cuda.max_memory_allocated(device)
    report()


if __name__ == '__main__':
    main()
