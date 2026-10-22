"""Shared CPU/ROCm device selection for local training and rendering."""
import os


def configure(torch, requested, threads):
    count = os.cpu_count() or 1
    threads = threads or count
    if not 1 <= threads <= count:
        raise ValueError(f'Expected 1..{count} CPU threads, or 0 for automatic')
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(2)
    available = torch.cuda.is_available()
    if requested == 'cuda' and not available:
        raise RuntimeError('GPU unavailable. Use the ROCm Python environment, or --device cpu.')
    device = torch.device('cuda' if requested == 'cuda' or (requested == 'auto' and available) else 'cpu')
    details = {'device': str(device), 'threads': threads, 'torch': torch.__version__,
               'hip': torch.version.hip, 'cpu_logical_processors': count}
    if device.type == 'cuda':
        properties = torch.cuda.get_device_properties(device)
        details.update(accelerator=properties.name, accelerator_memory=properties.total_memory)
        if torch.version.hip and getattr(properties, 'gcnArchName', '').startswith('gfx1150'):
            # PyTorch currently gates the optimized RDNA 3.5 attention kernels.
            # A caller can explicitly disable this with the environment value 0.
            os.environ.setdefault('TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL', '1')
            details['experimental_attention'] = os.environ['TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL'] == '1'
    return device, details
