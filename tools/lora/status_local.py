"""Show the local pilot status, request a saved stop, or resume its checkpoint."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def read(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--stop', action='store_true')
    action.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    work = args.work.resolve()
    training = work / 'training-local'
    job = read(work / 'job.json')
    state = read(training / 'progress.json')
    if args.stop:
        if job.get('status') != 'training' or state.get('status') in ('failed', 'stopped', 'training_complete'):
            raise SystemExit('Zurzeit laeuft kein Training, das dieser Knopf anhalten kann.')
        (training / 'STOP').write_text('Save after current update and stop.\n', encoding='ascii')
        print('Anhalten angefordert. Nach dem aktuellen Lernschritt wird gespeichert und angehalten.')
        return
    if args.resume:
        import psutil
        lock = work / '.running.lock'
        if lock.exists():
            try:
                process = psutil.Process(int(lock.read_text(encoding='ascii')))
                if any('run_local_pilot.py' in item for item in process.cmdline()):
                    raise SystemExit('Der Auftrag laeuft bereits. Bitte nicht doppelt starten.')
            except psutil.NoSuchProcess:
                pass
            lock.unlink()
        if (training / 'final/pytorch_lora_weights.safetensors').exists():
            raise SystemExit('Das Training ist bereits fertig. Bei einem Fehler der Bildausgabe die Logs weitergeben.')
        checkpoints = [(read(p)['step'], p.parent) for p in training.glob('*/state.json')]
        if not checkpoints:
            raise SystemExit('Noch kein gespeicherter Zwischenstand vorhanden.')
        step, checkpoint = max(checkpoints)
        run = read(training / 'run.json')
        root = Path(__file__).resolve().parents[2]
        with (work / 'resume-launch.log').open('ab') as log:
            process = subprocess.Popen([sys.executable, '-u', str(root / 'tools/lora/run_local_pilot.py'),
                '--work', str(work), '--resume', str(checkpoint), '--steps', str(run['steps']),
                '--threads', str(run['threads'])], cwd=root, stdout=log, stderr=log,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if os.name == 'nt':
            psutil.Process(process.pid).nice(psutil.NORMAL_PRIORITY_CLASS)
        print('Fortsetzen ab Lernschritt', step, 'gestartet.')
        return
    status = job.get('status', 'unknown')
    names = {'download':'Modelle werden heruntergeladen', 'starting':'Start wird vorbereitet',
             'training':'Lernen laeuft', 'rendering':'Die drei Probe-Bilder werden berechnet',
             'complete':'Training und Probe-Bilder sind fertig', 'stopped':'Gespeichert und angehalten',
             'failed':'Ein Fehler ist aufgetreten'}
    print(names.get(status, status))
    if status == 'training':
        stage = state.get('status')
        if stage != 'training':
            print({'loading_runtime':'Trainingsprogramme laden', 'caching_text':'Texte vorbereiten',
                   'caching_latents':'Bilder vorbereiten', 'loading_unet':'Bildmodell laden'}.get(stage, stage))
        print('Lernschritt:', state.get('step', 0), 'von', state.get('total_steps', '?'))
        estimate = state.get('estimated_remaining_seconds')
        if estimate is not None:
            hours, minutes = divmod(round(estimate / 60), 60)
            print('Grobe Restzeit fuer das Lernen:', hours, 'Stunden und', minutes, 'Minuten')
    if status == 'rendering':
        rendering = read(work / 'review-local/progress.json')
        print('Pose:', rendering.get('pose', 'Modell wird geladen'), 'Bildschritt:', rendering.get('step', 0), '/ 28')
    if status == 'failed':
        print(job.get('error', 'Bitte die Logs im Arbeitsordner pruefen.'))
        print(state.get('error', ''))
    print('Arbeitsordner:', work)
    print('LoRA-Datei nach Abschluss:', training / 'final/pytorch_lora_weights.safetensors')
    print('Probe-Bilder nach Abschluss:', work / 'review-local')


if __name__ == '__main__':
    main()
