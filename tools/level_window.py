"""Initial editor bounds in the current monitor's usable desktop coordinates."""
import sys


def work_area(root):
    fallback=(0,0,root.winfo_screenwidth(),root.winfo_screenheight())
    if sys.platform!='win32':return fallback
    try:
        import ctypes
        from ctypes import wintypes as w
        class MonitorInfo(ctypes.Structure):
            _fields_=[('size',w.DWORD),('monitor',w.RECT),('work',w.RECT),('flags',w.DWORD)]
        user=ctypes.windll.user32
        user.MonitorFromPoint.argtypes=[w.POINT,w.DWORD];user.MonitorFromPoint.restype=w.HANDLE
        user.GetMonitorInfoW.argtypes=[w.HANDLE,ctypes.POINTER(MonitorInfo)]
        point=w.POINT(root.winfo_pointerx(),root.winfo_pointery())
        monitor=user.MonitorFromPoint(point,2);info=MonitorInfo();info.size=ctypes.sizeof(info)
        if user.GetMonitorInfoW(monitor,ctypes.byref(info)):
            r=info.work;return r.left,r.top,r.right,r.bottom
    except (OSError,AttributeError):pass
    return fallback


def initial_bounds(area,scale):
    left,top,right,bottom=area;aw=max(1,right-left);ah=max(1,bottom-top)
    # Geometry sizes are client sizes. Leave room for native borders, the
    # title bar, taskbar and a visible desktop margin, even on small monitors.
    margin=min(32,max(12,round(20*scale)))
    maxw=max(1,aw-2*margin-20);maxh=max(1,ah-2*margin-56)
    width=min(round(1520*scale),round(aw*.88),maxw)
    height=min(round(900*scale),round(ah*.84)-40,maxh)
    width=max(1,width);height=max(1,height)
    return width,height,left+(aw-width-20)//2,top+margin


def configure(root,scale):
    width,height,x,y=initial_bounds(work_area(root),scale)
    root.geometry(f'{width}x{height}+{x}+{y}')
    root.minsize(min(round(1000*scale),width),min(round(640*scale),height))
