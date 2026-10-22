"""Check real GPU forward/backward kernels, not just device detection.

No model download, training dataset, generated image, or cloud call.
"""
import argparse
import json
from pathlib import Path
import time
import traceback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = {'passed': False}
    try:
        import torch
        result.update(torch=torch.__version__, hip=torch.version.hip,
                      available=torch.cuda.is_available(), device_count=torch.cuda.device_count())
        if not result['available']:
            raise RuntimeError('No GPU available in this Python runtime')
        properties = torch.cuda.get_device_properties(0)
        result.update(name=properties.name, total_memory=properties.total_memory,
                      architecture=getattr(properties, 'gcnArchName', None),
                      bf16=torch.cuda.is_bf16_supported())
        tick = time.perf_counter()
        x = torch.randn(1, 4, 64, 64, device='cuda', dtype=torch.bfloat16, requires_grad=True)
        layer = torch.nn.Conv2d(4, 8, 3, padding=1).to(device='cuda', dtype=torch.bfloat16)
        layer(x).float().square().mean().backward()
        q = torch.randn(1, 4, 32, 32, device='cuda', dtype=torch.bfloat16, requires_grad=True)
        torch.nn.functional.scaled_dot_product_attention(q, q, q).float().square().mean().backward()
        torch.cuda.synchronize()
        passed = bool(torch.isfinite(x.grad).all() and torch.isfinite(q.grad).all()
                      and x.grad.abs().max() > 0 and q.grad.abs().max() > 0)
        result.update(passed=passed, seconds=time.perf_counter() - tick)
    except Exception as exc:
        result.update(error=str(exc), traceback=traceback.format_exc())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2), flush=True)
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
