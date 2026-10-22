"""One local job: public model download -> character LoRA -> three pose examples.

Runs with the isolated lora-runtime interpreter. No cloud uploads or paid calls.
Stages and child PIDs are recorded; a STOP file is honored between train updates.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--steps', type=int, default=600)
    parser.add_argument('--threads', type=int, default=0)
    parser.add_argument('--device', choices=('auto', 'cpu', 'cuda'), default='auto')
    parser.add_argument('--resume', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    work = args.work.resolve()
    os.environ['HF_HOME'] = str(root / 'artwork-local/lora-hf-cache')
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
    threads = args.threads or os.cpu_count() or 1
    os.environ['OMP_NUM_THREADS'] = str(threads)
    os.environ['MKL_NUM_THREADS'] = str(threads)
    lock = work / '.running.lock'
    with lock.open('x', encoding='ascii') as handle:
        handle.write(str(os.getpid()))
    state = {'status': 'starting', 'pid': os.getpid(), 'started_unix': time.time(),
             'uploaded': False, 'paid_calls': 0, 'work': str(work)}

    def save():
        temp = work / 'job.tmp'
        temp.write_text(json.dumps(state, indent=2), encoding='utf-8')
        temp.replace(work / 'job.json')

    def stage(name, arguments):
        state.update(status=name, child_pid=None)
        save()
        with (work / (name + '.stdout.log')).open('ab') as stdout, (work / (name + '.stderr.log')).open('ab') as stderr:
            child = subprocess.Popen([sys.executable, '-u', *map(str, arguments)], cwd=root,
                                     stdout=stdout, stderr=stderr)
            state['child_pid'] = child.pid
            save()
            code = child.wait()
        if code:
            raise RuntimeError(f'{name} exited with {code}; see {name}.stderr.log')

    try:
        if os.name == 'nt':
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
        save()
        model = work / 'models/sdxl'
        control = work / 'models/openpose-sdxl'
        dataset = work / 'dataset-v1'
        training = work / 'training-local'
        stage('download', [root / 'tools/lora/download_sdxl.py', '--out', model,
                           '--controlnet-out', control])
        command = [root / 'tools/lora/train_sdxl.py', '--model', model,
                   '--dataset', dataset, '--out', training, '--steps', args.steps,
                   '--threads', threads, '--device', args.device]
        if args.resume:
            (training / 'STOP').unlink(missing_ok=True)
            command += ['--resume', args.resume.resolve()]
        stage('training', command)
        trained = json.loads((training / 'progress.json').read_text(encoding='utf-8'))
        if trained['status'] != 'training_complete':
            state['status'] = trained['status']
            save()
            return
        stage('rendering', [root / 'tools/lora/render_sdxl_trial.py', '--model', model,
                           '--controlnet', control, '--lora', training / 'final',
                           '--guides', work / 'pose-guides', '--out', work / 'review-local',
                           '--threads', threads, '--device', args.device])
        state.update(status='complete', completed_unix=time.time(), child_pid=None)
        save()
    except BaseException as exc:
        state.update(status='failed', error=str(exc), traceback=traceback.format_exc())
        save()
        raise
    finally:
        lock.unlink(missing_ok=True)
        if os.name == 'nt':
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == '__main__':
    main()
