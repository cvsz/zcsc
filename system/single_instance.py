from __future__ import annotations

import os


class SingleInstance:
    def __init__(self, name: str = "Local\\CamfrogStatusChanger.SingleInstance") -> None:
        self.name = name
        self._handle = None

    def acquire(self) -> bool:
        if os.name != "nt":
            return True
        import win32api
        import win32event
        import winerror
        self._handle = win32event.CreateMutex(None, False, self.name)
        return win32api.GetLastError() != winerror.ERROR_ALREADY_EXISTS

    def release(self) -> None:
        if self._handle is not None and os.name == "nt":
            import win32api
            try:
                win32api.CloseHandle(self._handle)
            except Exception:
                pass
            self._handle = None
