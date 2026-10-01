from __future__ import annotations
import os

class SingleInstance:
    def __init__(self):
        self.handle=None
    def acquire(self):
        if os.name!="nt":
            return True
        import win32api, win32event, winerror
        self.handle=win32event.CreateMutex(None,False,"Local\\CamfrogStatusChanger")
        return win32api.GetLastError()!=winerror.ERROR_ALREADY_EXISTS
    def release(self):
        if self.handle and os.name=="nt":
            import win32api
            try: win32api.CloseHandle(self.handle)
            except Exception: pass
        self.handle=None
