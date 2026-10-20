"""sciv_play --fast must never change the player's normal launch folder."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys

import sciv_test_support as sciv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, required=True)
    sciv.add_build_arg(parser)
    args = parser.parse_args()
    build = sciv.build_dir(args)
    player = sciv.ROOT / 'build-play/game'
    script = sciv.ROOT / 'tools/sciv_play.py'

    def protected():
        files = [player / name for name in ('config.ini', 'keybinds.ini', 'hd_settings.json')]
        for name in ('saves', 'debug_markers'):
            files.extend((player / name).rglob('*'))
        return {str(p.relative_to(player)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in files if p.is_file()}

    before = protected()
    folders = []
    for fast in (True, False):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        cmd = [sys.executable, str(script), 'start', '--build-dir', str(build),
               '--rom', str(args.rom.resolve()), '--port', str(port), '--widescreen']
        if fast:
            cmd.append('--fast')
        running = False
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            running = True
            folder = Path(json.loads(result.stdout)['folder'])
            folders.append(folder)
            assert folder != player and folder.parent == player.parent / 'sessions'
            config = (folder / 'config.ini').read_text()
            assert ('DisableFrameDelay=1' in config) == fast, config
        finally:
            if running:
                subprocess.run([sys.executable, str(script), 'stop'], check=True, capture_output=True)
        assert protected() == before, 'test session changed player configuration, saves or markers'
    assert folders[0] != folders[1], 'test sessions reused a folder'
    print('PASS: fast/normal sessions use unique folders; player settings, saves and debug captures unchanged')


if __name__ == '__main__':
    main()
