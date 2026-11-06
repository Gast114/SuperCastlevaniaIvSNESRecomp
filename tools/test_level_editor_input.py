"""Windows Num Lock selection, immediate Delete after adding, and startup bounds."""
import copy
import ctypes
import json
from pathlib import Path
import sys
import tempfile
import time
import tkinter as tk
import traceback
from enemy_workshop_native import ROOT
from level_editor import Editor
from level_window import work_area,initial_bounds


def check():
    folder=Path(tempfile.mkdtemp(prefix='editor-input-',dir=ROOT/'artwork-local/level-editor/tests'))
    print(folder,flush=True);report=dict(passed=False,checks=[],image_viewer_used=False)
    def passed(message):report['checks'].append(message);print('PASS:',message,flush=True)
    # A taskbar at the top/side and a monitor left of the primary must also
    # produce absolute bounds inside that monitor, not below the desktop.
    for area,scale in [((0,0,1920,1040),1),((0,0,3840,2080),1.7),((-1920,40,0,1080),1),((48,0,1280,720),1)]:
        width,height,x,y=initial_bounds(area,scale)
        assert area[0]<=x and area[1]<=y
        assert x+width+20<=area[2] and y+height+56<=area[3],(area,(width,height,x,y))
    root=tk.Tk();errors=[]
    root.report_callback_exception=lambda *exc:errors.append(''.join(traceback.format_exception(*exc)))
    app=Editor(root)
    def spin(predicate):
        deadline=time.monotonic()+35
        while time.monotonic()<deadline:
            root.update()
            if predicate():return
            time.sleep(.01)
        raise AssertionError('Default editor did not finish loading')
    try:
        spin(lambda:app.original_room is not None and 0 in app.assets)
        if sys.platform=='win32':
            from ctypes import wintypes as w
            user=ctypes.windll.user32
            user.GetAncestor.argtypes=[w.HWND,w.UINT];user.GetAncestor.restype=w.HWND
            user.GetWindowRect.argtypes=[w.HWND,ctypes.POINTER(w.RECT)]
            rect=w.RECT();assert user.GetWindowRect(user.GetAncestor(root.winfo_id(),2),ctypes.byref(rect))
            left,top,right,bottom=work_area(root)
            assert left<=rect.left and top<=rect.top and rect.right<=right and rect.bottom<=bottom,(work_area(root),tuple(getattr(rect,k) for k in ('left','top','right','bottom')))
            report['native_window_bounds']=[rect.left,rect.top,rect.right,rect.bottom]
        passed('Initial native window including its title bar stays inside the usable desktop; small, 4K, taskbar and negative-monitor layouts fit')
        root.lift();root.focus_force();app.open_palette('Gegner');app.monsters.selection_set('M-0011');root.update()
        original=copy.deepcopy(app.original_room);button=app.library_actions['Monster'][0]
        # Real Tk button press/release, not invoke(): this catches focus being
        # stranded on the hidden library button when the inspector opens.
        button.event_generate('<ButtonPress-1>',x=10,y=10,state=8);root.update()
        button.event_generate('<ButtonRelease-1>',x=10,y=10,state=8);root.update()
        actor=app.object();identifier=actor['id'];canvas=app.canvas
        assert not app.original_view and root.focus_get()==canvas
        canvas.event_generate('<Delete>',state=8);root.update()
        assert not any(a['id']==identifier for a in app.current()['actors'])
        app.undo();root.update();actor=next(a for a in app.current()['actors'] if a['id']==identifier)
        assert app.original_cache[0]==original
        passed('Fresh original-catalog startup: add by actual button click, immediately delete without an extra canvas click, and undo; original remains unchanged')
        for modifier in (0,8,10):
            app.open_palette('Gelände');app.tool.set('Bauteil');root.update()
            x1,y1,x2,y2=app.actor_bounds(actor);z=app.zoom.get()
            x=round((x1+x2)/2*z-canvas.canvasx(0));y=round((y1+y2)/2*z-canvas.canvasy(0))
            before=actor['x'],actor['y'];terrain=copy.deepcopy(app.current()['layers'])
            canvas.event_generate('<ButtonPress-1>',x=x,y=y,state=modifier);root.update()
            assert app.selected_object==('actor',identifier),(modifier,app.selected_object)
            canvas.event_generate('<B1-Motion>',x=x+20,y=y+12,state=modifier|0x100);root.update()
            canvas.event_generate('<ButtonRelease-1>',x=x+20,y=y+12,state=modifier);root.update()
            assert (actor['x'],actor['y'])==(before[0]+10,before[1]+6),(modifier,actor,before)
            assert app.current()['layers']==terrain and app.stats_window is None
        passed('Mouse selects and drags with Num Lock off/on and Caps Lock; terrain is untouched and no modal opens')
        if root.tk.call('tk','windowingsystem')=='win32':
            app.tool.set('Zeichnen');x1,y1,x2,y2=app.actor_bounds(actor)
            x=round((x1+x2)/2*z-canvas.canvasx(0));y=round((y1+y2)/2*z-canvas.canvasy(0))
            canvas.event_generate('<ButtonPress-1>',x=x,y=y,state=0x20008);root.update()
            canvas.event_generate('<ButtonRelease-1>',x=x,y=y,state=0x20008);root.update()
            assert app.selected_object is None and app.tool.get()=='Zeichnen'
            passed('Actual Windows Alt modifier still bypasses the actor for painting underneath it, including with Num Lock enabled')
        assert not errors,errors
        report['passed']=True
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:
        report['callback_errors']=errors
        (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        app.project.dirty=False;app.close();root.update()


if __name__=='__main__':check()
