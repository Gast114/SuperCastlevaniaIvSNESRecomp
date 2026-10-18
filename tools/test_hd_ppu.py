"""ROM-free HD tile provenance regression, built against the real PPU."""
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
cc = shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')
if not cc:
    raise SystemExit('C11 compiler required')
with tempfile.TemporaryDirectory(prefix='ppu-hd-') as tmp:
    exe = Path(tmp) / 'test.exe'
    subprocess.run([cc, '-std=c11', '-O2', '-DSNESRECOMP_REVERSE_DEBUG=0',
                    '-Irunner/src', '-Irunner/src/snes',
                    'tests/ppu/ppu_hd_tiles_test.c', 'runner/src/snes/ppu.c',
                    'runner/src/snes/ppu_legacy.c', '-lm', '-o', str(exe)],
                   cwd=ROOT / 'snesrecomp', check=True)
    subprocess.run([str(exe)], check=True)
