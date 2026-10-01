from __future__ import annotations
import logging, os, time
from dataclasses import dataclass
from status_text import comparable_status
log=logging.getLogger(__name__)

@dataclass
class BackgroundResult:
    ok: bool
    message: str
    hwnd: int=0
    verified: bool=False
    observed: str=""

def _require():
    if os.name!="nt": raise RuntimeError("Windows only")

def _children(parent):
    import win32gui
    out=[]
    win32gui.EnumChildWindows(parent,lambda h,_:(out.append(h),True)[1],None)
    return out

def _cls(h):
    import win32gui
    try:return win32gui.GetClassName(h) or ""
    except Exception:return ""

def _text(h):
    import win32gui
    try:return win32gui.GetWindowText(h) or ""
    except Exception:return ""

def _send(h,msg,wp=0,lp=0,timeout=1200):
    import win32gui
    return win32gui.SendMessageTimeout(h,msg,wp,lp,2,timeout)

def _find_combo(top,current="",known=()):
    cands=[]
    knownset={str(x).strip().casefold() for x in known if str(x).strip()}
    for h in _children(top):
        if _cls(h).casefold()=="ccomboboxts":
            score=1000
            t=_text(h).strip().casefold()
            if t and (t==str(current).strip().casefold() or t in knownset): score+=500
            cands.append((score,h))
    cands.sort(reverse=True)
    return cands[0][1] if cands else 0

def _find_edit(combo):
    for h in _children(combo):
        if "edit" in _cls(h).casefold(): return h
    return 0

def set_status_background(parent_hwnd,relative_x,relative_y,value,*,current_text="",known_statuses=()):
    _require()
    import win32con, win32gui
    combo=_find_combo(int(parent_hwnd),current_text,known_statuses)
    if not combo:
        return BackgroundResult(False,"CComboBoxTS status control was not found")
    edit=_find_edit(combo)
    target=edit or combo
    try:
        _send(target,win32con.WM_SETTEXT,0,value)
        # Standard change/commit notifications only; do not click generic buttons.
        cid=win32gui.GetDlgCtrlID(target)
        owner=win32gui.GetParent(target)
        if edit and owner:
            for code in (getattr(win32con,"EN_UPDATE",0x0400),getattr(win32con,"EN_CHANGE",0x0300)):
                _send(owner,win32con.WM_COMMAND,(code<<16)|(cid&0xffff),target)
        _send(target,win32con.WM_KEYDOWN,win32con.VK_RETURN,0)
        _send(target,win32con.WM_KEYUP,win32con.VK_RETURN,0)
        for _ in range(4):
            observed=_text(target).strip() or _text(combo).strip()
            if comparable_status(observed)==comparable_status(value):
                return BackgroundResult(True,"Camfrog status control updated and verified locally",combo,True,observed)
            time.sleep(.12)
        return BackgroundResult(False,"Camfrog control was reached but local commit could not be verified",combo,False,observed)
    except Exception as exc:
        log.exception("Background Win32 automation failed")
        return BackgroundResult(False,f"Background Win32 automation failed: {exc}",combo)
