"""Local SDXL character LoRA with cached conditioning and resumable checkpoints.

Uses public Diffusers/PEFT APIs following the SDXL LoRA training objective:
https://huggingface.co/docs/diffusers/training/lora
No network, tracker, cloud training, model publication, or game installation.
"""
import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import random
import time
import traceback

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'


def atomic_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--steps', type=int, default=600)
    parser.add_argument('--rank', type=int, default=16)
    parser.add_argument('--lr', type=float, default=8e-5)
    parser.add_argument('--threads', type=int, default=0, help='0 uses all logical CPU processors')
    parser.add_argument('--device', choices=('auto', 'cpu', 'cuda'), default='auto',
                        help='cuda also means an AMD GPU in the ROCm runtime')
    parser.add_argument('--checkpoint-every', type=int, default=100)
    parser.add_argument('--seed', type=int, default=20261021)
    parser.add_argument('--dtype', choices=('bf16', 'fp32'), default='bf16')
    parser.add_argument('--resume', type=Path)
    args = parser.parse_args()
    if not 1 <= args.steps <= 3000 or not 1 <= args.rank <= 64 or args.checkpoint_every < 1:
        raise ValueError('Invalid bounded training settings')
    if args.out.exists() and not args.resume:
        raise FileExistsError('Use a new output folder, or explicitly resume a checkpoint')
    args.out.mkdir(parents=True, exist_ok=bool(args.resume))
    started = time.time()
    progress = {'status': 'loading_runtime', 'pid': os.getpid(), 'step': 0,
                'total_steps': args.steps, 'device': args.device, 'dtype': args.dtype,
                'started_unix': started, 'uploaded': False}
    status = args.out / 'progress.json'
    atomic_json(status, progress)
    try:
        import numpy as np
        import torch
        import torch.nn.functional as functional
        from diffusers import AutoencoderKL, DDPMScheduler, StableDiffusionXLPipeline, UNet2DConditionModel
        from diffusers.utils import convert_state_dict_to_diffusers
        from peft import LoraConfig, get_peft_model_state_dict, set_peft_model_state_dict
        from PIL import Image
        from safetensors.torch import load_file, save_file
        from transformers import CLIPTextModel, CLIPTextModelWithProjection, CLIPTokenizer

        from compute import configure
        device, compute = configure(torch, args.device, args.threads)
        progress.update(compute)
        torch.manual_seed(args.seed)
        rng = random.Random(args.seed)
        dtype = torch.bfloat16 if args.dtype == 'bf16' else torch.float32
        if os.name == 'nt':
            # Keep this active job awake without changing a Windows power plan.
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
        dataset = json.loads((args.dataset / 'dataset.json').read_text(encoding='utf-8'))
        rows = [row for row in dataset['images'] if row['split'] == 'train']
        if dataset['canvas'] != [512, 512] or not rows:
            raise ValueError('Expected prepared 512px training examples')
        model = str(args.model.resolve())
        run = {'base_model': 'stabilityai/stable-diffusion-xl-base-1.0',
               'model_directory': model, 'dataset_sha256': dataset['archive_sha256'],
               'trigger_word': dataset['trigger_word'], 'steps': args.steps, 'rank': args.rank,
               'learning_rate': args.lr, 'seed': args.seed, 'dtype': args.dtype,
               'threads': compute['threads'], 'train_images': len(rows), 'resolution': 512,
               'text_encoders_trained': False, 'device': str(device), 'uploaded': False,
               'torch': torch.__version__, 'cpu_capability': torch.backends.cpu.get_cpu_capability()}
        atomic_json(args.out / 'run.json', run)
        cache = args.out / 'conditioning.safetensors'
        if cache.exists():
            tensors = load_file(cache)
        else:
            progress['status'] = 'caching_text'
            atomic_json(status, progress)
            tokenizers = [CLIPTokenizer.from_pretrained(model, subfolder=name, local_files_only=True)
                          for name in ('tokenizer', 'tokenizer_2')]
            encoders = [cls.from_pretrained(model, subfolder=name, variant='fp16',
                                           torch_dtype=dtype, local_files_only=True)
                        for cls, name in ((CLIPTextModel, 'text_encoder'),
                                          (CLIPTextModelWithProjection, 'text_encoder_2'))]
            tensors = {}
            for encoder in encoders:
                encoder.requires_grad_(False).eval()
            with torch.no_grad():
                for i, row in enumerate(rows):
                    hidden = []
                    for tokenizer, encoder in zip(tokenizers, encoders):
                        ids = tokenizer(row['caption'], padding='max_length', truncation=True,
                                        max_length=tokenizer.model_max_length, return_tensors='pt').input_ids
                        encoded = encoder(ids, output_hidden_states=True)
                        hidden.append(encoded.hidden_states[-2])
                    tensors[f'prompt_{i}'] = torch.cat(hidden, dim=-1).contiguous()
                    tensors[f'pooled_{i}'] = encoded.text_embeds.contiguous()
            del encoded, hidden, encoders, tokenizers, encoder
            gc.collect()
            progress['status'] = 'caching_latents'
            atomic_json(status, progress)
            vae = AutoencoderKL.from_pretrained(model, subfolder='vae', variant='fp16',
                                                torch_dtype=torch.float32, local_files_only=True)
            vae.requires_grad_(False).eval()
            with torch.no_grad():
                for i, row in enumerate(rows):
                    path = args.dataset / 'train' / (row['name'] + '.png')
                    if hashlib.sha256(path.read_bytes()).hexdigest() != row['prepared_sha256']:
                        raise ValueError('Dataset image changed after preparation: ' + str(path))
                    with Image.open(path) as im:
                        pixels = torch.from_numpy(np.array(im.convert('RGB'), dtype=np.float32))
                    pixels = pixels.permute(2, 0, 1).unsqueeze(0) / 127.5 - 1
                    posterior = vae.encode(pixels).latent_dist
                    # Keep the posterior distribution; sample fresh latents per
                    # update rather than freezing one random encoding forever.
                    tensors[f'mean_{i}'] = posterior.mean.contiguous()
                    tensors[f'std_{i}'] = posterior.std.contiguous()
                tensors['vae_scale'] = torch.tensor([vae.config.scaling_factor])
            save_file(tensors, cache, metadata={'dataset_sha256': dataset['archive_sha256']})
            del vae, pixels, posterior
            gc.collect()
        progress['status'] = 'loading_unet'
        atomic_json(status, progress)
        unet = UNet2DConditionModel.from_pretrained(model, subfolder='unet', variant='fp16',
                                                   torch_dtype=dtype, local_files_only=True)
        unet.requires_grad_(False)
        unet.add_adapter(LoraConfig(r=args.rank, lora_alpha=args.rank, init_lora_weights='gaussian',
                                    target_modules=['to_k', 'to_q', 'to_v', 'to_out.0']))
        for parameter in unet.parameters():
            if parameter.requires_grad:
                parameter.data = parameter.data.float()
        unet.to(device)
        tensors = {key: value.to(device) for key, value in tensors.items()}
        run.update(compute)
        unet.enable_gradient_checkpointing()
        unet.train()
        trainable = [p for p in unet.parameters() if p.requires_grad]
        run['trainable_parameters'] = sum(p.numel() for p in trainable)
        atomic_json(args.out / 'run.json', run)
        optimizer = torch.optim.AdamW(trainable, lr=args.lr, betas=(.9, .999), weight_decay=.01)
        scheduler = DDPMScheduler.from_pretrained(model, subfolder='scheduler', local_files_only=True)
        scheduler.alphas_cumprod = scheduler.alphas_cumprod.to(device)
        time_ids = torch.tensor([[512, 512, 0, 0, 512, 512]], dtype=dtype, device=device)
        initial_step = 0
        order = []
        position = 0
        if args.resume:
            saved = json.loads((args.resume / 'state.json').read_text(encoding='utf-8'))
            for key in ('dataset_sha256', 'rank', 'dtype', 'seed'):
                if saved['run'][key] != run[key]:
                    raise ValueError('Resume mismatch: ' + key)
            state_dict = load_file(args.resume / 'adapter-training.safetensors')
            set_peft_model_state_dict(unet, state_dict)
            state = torch.load(args.resume / 'optimizer.pt', map_location='cpu', weights_only=True)
            optimizer.load_state_dict(state['optimizer'])
            torch.set_rng_state(state['torch_rng'])
            if device.type == 'cuda' and state.get('cuda_rng') is not None:
                torch.cuda.set_rng_state_all(state['cuda_rng'])
            rng.setstate(state['python_rng'])
            initial_step = saved['step']
            order, position = state['order'], state['position']
            del state, state_dict

        def checkpoint(step, folder):
            folder.mkdir(parents=True, exist_ok=False)
            weights = {k: v.detach().cpu().contiguous() for k, v in get_peft_model_state_dict(unet).items()}
            save_file(weights, folder / 'adapter-training.safetensors')
            StableDiffusionXLPipeline.save_lora_weights(str(folder),
                unet_lora_layers=convert_state_dict_to_diffusers(weights), safe_serialization=True)
            torch.save({'optimizer': optimizer.state_dict(), 'torch_rng': torch.get_rng_state(),
                        'cuda_rng': torch.cuda.get_rng_state_all() if device.type == 'cuda' else None,
                        'python_rng': rng.getstate(), 'order': order, 'position': position},
                       folder / 'optimizer.pt')
            atomic_json(folder / 'state.json', {'step': step, 'run': run})

        durations = []
        progress.update(status='training', step=initial_step)
        atomic_json(status, progress)
        with (args.out / 'loss.jsonl').open('a', encoding='utf-8') as log:
            for step in range(initial_step, args.steps):
                if (args.out / 'STOP').exists():
                    checkpoint(step, args.out / f'stopped-{step:04d}')
                    progress.update(status='stopped', step=step)
                    atomic_json(status, progress)
                    return
                tick = time.monotonic()
                if position >= len(order):
                    order = list(range(len(rows)))
                    rng.shuffle(order)
                    position = 0
                i = order[position]
                position += 1
                mean, std = tensors[f'mean_{i}'], tensors[f'std_{i}']
                latents = ((mean + std * torch.randn_like(mean)) * tensors['vae_scale']).to(dtype)
                noise = torch.randn_like(latents)
                timestep = torch.randint(0, scheduler.config.num_train_timesteps, (1,), dtype=torch.long, device=device)
                noisy = scheduler.add_noise(latents, noise, timestep)
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast(device.type, dtype=torch.bfloat16, enabled=args.dtype == 'bf16'):
                    predicted = unet(noisy, timestep, encoder_hidden_states=tensors[f'prompt_{i}'].to(dtype),
                                     added_cond_kwargs={'text_embeds': tensors[f'pooled_{i}'].to(dtype),
                                                        'time_ids': time_ids}).sample
                target = noise if scheduler.config.prediction_type == 'epsilon' else scheduler.get_velocity(latents, noise, timestep)
                alpha = scheduler.alphas_cumprod[timestep].float()
                snr = alpha / (1 - alpha)
                weight = torch.minimum(snr, torch.full_like(snr, 5)) / (snr if scheduler.config.prediction_type == 'epsilon' else snr + 1)
                loss = functional.mse_loss(predicted.float(), target.float()) * weight.mean()
                if not torch.isfinite(loss):
                    raise RuntimeError('Non-finite training loss')
                loss.backward()
                gradient_norm = torch.nn.utils.clip_grad_norm_(trainable, 1.)
                if not torch.isfinite(gradient_norm) or (step == initial_step and gradient_norm.item() == 0):
                    raise RuntimeError('Invalid or zero adapter gradients')
                warmup = min(1., (step + 1) / 30)
                decay = .15 + .85 * (1 + math.cos(math.pi * step / args.steps)) / 2
                for group in optimizer.param_groups:
                    group['lr'] = args.lr * warmup * decay
                optimizer.step()
                if device.type == 'cuda':
                    torch.cuda.synchronize(device)
                duration = time.monotonic() - tick
                durations.append(duration)
                value = {'step': step + 1, 'loss': loss.item(), 'gradient_norm': gradient_norm.item(),
                         'seconds': duration, 'image': rows[i]['name'], 'learning_rate': optimizer.param_groups[0]['lr']}
                log.write(json.dumps(value) + '\n')
                log.flush()
                progress.update(status='training', **value, elapsed_seconds=time.time() - started,
                                estimated_remaining_seconds=sum(durations[-10:]) / len(durations[-10:]) * (args.steps - step - 1))
                atomic_json(status, progress)
                print(json.dumps(value), flush=True)
                if (step + 1) % args.checkpoint_every == 0 and step + 1 < args.steps:
                    checkpoint(step + 1, args.out / f'checkpoint-{step+1:04d}')
        checkpoint(args.steps, args.out / 'final')
        progress.update(status='training_complete', completed_unix=time.time())
        if device.type == 'cuda':
            progress['peak_gpu_allocated_bytes'] = torch.cuda.max_memory_allocated(device)
        atomic_json(status, progress)
    except BaseException as exc:
        progress.update(status='failed', error=str(exc), traceback=traceback.format_exc())
        atomic_json(status, progress)
        raise
    finally:
        if os.name == 'nt':
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == '__main__':
    main()
