"""F5 startup through the real Tk event queue, including cancellation/errors."""
import json
from pathlib import Path
import tempfile
import threading
import time
import tkinter as tk
from unittest.mock import patch

from enemy_resources import ROM_SHA256
from enemy_workshop_native import ROOT,NativeSession
from level_editor import Editor
from level_playtest import start_playtest_session


def check():
    folder=Path(tempfile.mkdtemp(prefix='startup-',dir=ROOT/'artwork-local/level-editor/tests'))
    print(folder,flush=True);report=dict(passed=False,image_viewer_used=False,checks=[])
    def passed(text):report['checks'].append(text);print('PASS:',text,flush=True)
    root=tk.Tk();root.withdraw();app=Editor(root);errors=[];gate=threading.Event()
    def spin(predicate,seconds=35):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            root.update()
            if predicate():return
            time.sleep(.01)
        raise AssertionError(f'Editor startup did not finish: {app.status.get()} / {errors}')
    try:
        spin(lambda:0 in app.assets)
        with patch('level_editor.messagebox.showerror',lambda *args,**kwargs:errors.append(args)):
            app.original_view=True;app.original_number=0;start=time.monotonic();app.test()
            assert app.play_pending and app.play_dialog.winfo_exists()
            assert str(app.play_progress.cget('mode'))=='indeterminate'
            spin(lambda:app.playtest is not None and not app.play_pending)
            report['original_ready_seconds']=round(time.monotonic()-start,3)
            first=app.playtest;s=first.session
            assert s.prepared_start and s.proc.poll() is None
            assert json.loads(s.command('window','status'))['visible']>0
            assert app.play_dialog is None and not errors
            s.lua.command('pause');assert s.read(0x70)==5
            app.stop_level_test();assert first.session is None
            report['audio_unavailable']=first.audio_unavailable
            passed('Real Original F5 shows a startup panel, restores the verified prepared state, removes the panel and exposes a live resumed game, including audio-device fallback')

            custom=app.assets[0].import_room(include_objects=True)
            app.project.data['rooms']=[custom];app.project.data['start_room']=custom['id'];app.room_id=custom['id'];app.original_view=False;app.refresh_rooms()
            start=time.monotonic();app.test();assert app.play_dialog is not None
            spin(lambda:app.playtest is not None and not app.play_pending)
            report['custom_ready_seconds']=round(time.monotonic()-start,3)
            s=app.playtest.session;s.lua.command('pause')
            assert json.loads(s.command('level_status'))['active'] and s.prepared_start
            assert json.loads(s.command('window','status'))['visible']>0 and app.play_dialog is None and not errors
            app.stop_level_test();app.original_view=True
            passed('Custom-map F5 also passes through the real editor queue and exposes the initialized project in a persistent game window')

            failed=[]
            def fail(number,destination,**kwargs):
                failed.append(Path(destination));raise RuntimeError('intentional startup failure')
            with patch('level_editor.OriginalPlaytest',fail):
                app.test();spin(lambda:not app.play_pending)
            assert app.play_dialog is None and errors and 'intentional startup failure' in errors[-1][1]
            assert 'intentional startup failure' in (failed[0]/'startup-error.log').read_text()
            errors.clear()
            passed('A startup failure closes the loading panel, shows an error and saves its traceback instead of disappearing silently')

            entered=threading.Event();stale=[]
            class Cancelled:
                def __init__(self,path):self.folder=Path(path);self.closed=False
                def close(self):self.closed=True
                def show(self):raise AssertionError('Cancelled startup must never be exposed')
            def slow(number,destination,**kwargs):
                entered.set()
                if not gate.wait(30):raise TimeoutError('Test gate not released')
                game=Cancelled(destination);stale.append(game);return game
            with patch('level_editor.OriginalPlaytest',slow):
                app.test();spin(entered.is_set);app.cancel_play_start()
                assert not app.play_pending and app.play_dialog is None
            app.test();spin(lambda:app.playtest is not None and not app.play_pending)
            current=app.playtest;gate.set();spin(lambda:stale and all(not t.is_alive() for t in app.workers))
            assert stale[0].closed and app.playtest is current and current.session.proc.poll() is None and not errors
            app.stop_level_test()
            passed('Cancel followed by another F5 cannot expose a stale window or close the newly started game')

        # Corruption of a cache must not turn it into an unverified user save
        # or prevent F5 from falling back to a fresh native bootstrap.
        private=folder/'isolated-root';base=private/'artwork-local/level-editor/rooms/00'
        (base/'capture/saves').mkdir(parents=True)
        (base/'room.json').write_text(json.dumps(dict(version=1,rom_sha256=ROM_SHA256,room=0)))
        (base/'capture/saves/save0.sav').write_bytes(b'broken prepared snapshot')
        s=NativeSession(folder=folder/'invalid-cache-game')
        try:
            with patch('level_playtest.ROOT',private):start_playtest_session(s)
            assert not s.prepared_start and (s.read(0x32),s.read(0x70))==(4,5)
        finally:s.close()
        passed('An invalid prepared snapshot is rejected and the private game falls back to a complete fresh bootstrap')
        report['passed']=True
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:
        gate.set();app.project.dirty=False
        if not app.closing:app.close()
        end=time.monotonic()+35
        while time.monotonic()<end:
            try:
                root.update()
                if not root.winfo_exists():break
            except tk.TclError:break
            time.sleep(.01)
        (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':check()
