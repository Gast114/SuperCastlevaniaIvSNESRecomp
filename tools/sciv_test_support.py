"""Shared helpers for the ROM-required regression tests in tools/.

Every test runs the game in its own throwaway folder (the host anchors its
working directory to the executable), so the player's config, saves and
character packs are never touched. Generated data stays under the chosen
build directory.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXE_NAME = 'SuperCastlevaniaIvSNESRecomp.exe'
BASE_CONFIG = {
    'General': {'Autosave': '0', 'SkipLauncher': '1'},
    'Graphics': {'NewRenderer': '1', 'OutputMethod': 'OpenGL', 'VSync': '0'},
    'Sound': {'EnableAudio': '0'},
}


def add_build_arg(parser):
    """--build-dir: a single-config (Ninja) build dir or a multi-config one
    containing Release/. Default: $SCIV_BUILD_DIR, build/Release, then build."""
    parser.add_argument('--build-dir', type=Path, default=None)


def build_dir(args):
    candidates = [args.build_dir] if args.build_dir else []
    if os.environ.get('SCIV_BUILD_DIR'):
        candidates.append(Path(os.environ['SCIV_BUILD_DIR']))
    candidates += [ROOT / 'build/Release', ROOT / 'build']
    for candidate in candidates:
        candidate = candidate if candidate.is_absolute() else ROOT / candidate
        if (candidate / EXE_NAME).exists():
            return candidate.resolve()
        if (candidate / 'Release' / EXE_NAME).exists():
            return (candidate / 'Release').resolve()
    raise SystemExit(f'No {EXE_NAME} found; pass --build-dir')


def work_dir(build, prefix):
    work = Path(tempfile.mkdtemp(prefix=prefix, dir=build))
    print(work, flush=True)
    return work


def prepare(folder, build, config=None):
    """Copy the executable and its staged data into an isolated folder."""
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy2(build / EXE_NAME, folder / EXE_NAME)
    for name in ('assets', 'mods', 'shaders'):
        if (build / name).is_dir():
            shutil.copytree(build / name, folder / name, dirs_exist_ok=True)
    sections = {s: dict(v) for s, v in BASE_CONFIG.items()}
    for section, values in (config or {}).items():
        sections.setdefault(section, {}).update(values)
    (folder / 'config.ini').write_text(''.join(
        f'[{s}]\n' + ''.join(f'{k}={v}\n' for k, v in values.items())
        for s, values in sections.items()))
    return folder / EXE_NAME


def clean_env(**values):
    env = {k: v for k, v in os.environ.items() if not k.startswith('SNESRECOMP_')}
    env.update({k: str(v) for k, v in values.items()})
    return env


def hidden_window():
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    return startup


def run(folder, script, rom, env, timeout=180, log_name='game.log'):
    """Run the copied executable in `folder` with an input script; raises on failure."""
    with (folder / log_name).open('w') as log:
        subprocess.run([str(folder / EXE_NAME), '--script', str(ROOT / 'scripts' / script),
                        str(Path(rom).resolve())], cwd=folder, env=env,
                       startupinfo=hidden_window(), stdout=log, stderr=log,
                       timeout=timeout, check=True)
    return (folder / log_name).read_text(errors='replace')


def capture_template(build, rom, work, script='character_workshop_smoke.input',
                     frames=1600, config=None):
    """Collect Simon's body poses from the player's own ROM into an isolated
    characters/simon-template, the same way playing does. Returns its path."""
    folder = work / 'template-capture'
    prepare(folder, build, config)
    run(folder, script, rom, clean_env(SNESRECOMP_RUN_FRAMES=frames))
    template = folder / 'characters/simon-template'
    assert (template / 'character.json').exists(), 'No poses captured'
    return template


def recolored_copy(template, destination, color=(0, 255, 255, 255)):
    """A test pack whose artwork is unmistakably not Simon's."""
    from PIL import Image
    shutil.copytree(template, destination)
    sheet = Image.open(destination / 'body.png').convert('RGBA')
    sheet.paste(color, mask=sheet.getchannel('A'))
    sheet.save(destination / 'body.png')
    return destination
