"""Exercise the workshop's own Tk callbacks and worker with a private engine."""
import json
from pathlib import Path
import tempfile
import time
import tkinter as tk
from enemy_workshop import Workshop,ROOT


def main():
    folder=Path(tempfile.mkdtemp(prefix='ui-check-',dir=ROOT/'artwork-local/enemy-workshop'))
    root=tk.Tk();root.withdraw();app=Workshop(root,workspace=folder/'workspace',library=None)
    report={'passed':False,'checks':[],'desktop_screenshot':False}
    def wait(predicate,timeout=25):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            root.update()
            if predicate():return
            if not app.worker.is_alive():raise AssertionError(app.status.get())
            time.sleep(.01)
        raise AssertionError('Timeout: '+app.status.get())
    try:
        wait(lambda:bool(app.catalog))
        assert len(app.catalog)==106
        assert any(e.get('boss') for e in app.catalog)
        report['checks'].append('Catalog reaches the UI with enemy/object/unknown and experimental boss entries')
        app.single_step();wait(lambda:bool(app.snapshot.get('actors')))
        # Drain the final in-flight event before comparing paused native fields.
        until=time.monotonic()+.4
        while time.monotonic()<until:root.update();time.sleep(.01)
        tick=app.snapshot['tick'];until=time.monotonic()+.4
        while time.monotonic()<until:root.update();time.sleep(.01)
        assert app.snapshot['tick']==tick
        app.single_step();wait(lambda:app.snapshot['tick']!=tick)
        report['checks'].append('Pause holds the native field; single-step advances it')
        index=next(i for i,e in enumerate(app.catalog) if e['type']==7)
        app.enemy_box.current(index);app.spawn()
        wait(lambda:any(a['type']==7 for a in app.snapshot['actors']))
        wait(lambda:bool(app.tree.get_children()))
        assert all(app.workspace.frames[i]['actor_type']==7 for i in app.tree.get_children())
        assert tuple(app.action_box.cget('values'))==('Natürlich',)
        report['checks'].append('Spawning while paused updates the scene, action choices and filtered PNG list')
        app.parts.set(True);app.refresh_list()
        wait(lambda:bool(app.tree.get_children()) and all(app.workspace.frames[i]['component'] for i in app.tree.get_children()))
        report['checks'].append('Individual-part view uses captured component PNGs')
        report['passed']=True
    finally:
        app.close()
        deadline=time.monotonic()+15
        while app.worker.is_alive() and time.monotonic()<deadline:root.update();time.sleep(.02)
        assert not app.worker.is_alive(),'Private runtime did not close'
        report['checks'].append('Closing stops the owned worker and native session')
        (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(folder)
    for check in report['checks']:print('PASS: '+check)


if __name__=='__main__':main()
