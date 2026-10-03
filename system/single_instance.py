from __future__ import annotations

import os


class SingleInstance:
    """Use a Windows named mutex; the OS releases it when a process exits."""

    def __init__(self, name: str = "Local\\CamfrogStatusChanger.SingleInstance") -> None:
        self.name = name
        self._handle = None

    def acquire(self) -> bool:
        if os.name != "nt":
            return True
        import win32api
        import win32event
        import winerror
        handle = win32event.CreateMutex(None, False, self.name)
        last_error = win32api.GetLastError()
        if handle is None:
            raise OSError(last_error, "CreateMutex failed for the single-instance guard")
        if last_error == winerror.ERROR_ALREADY_EXISTS:
            try:
                win32api.CloseHandle(handle)
            except Exception:
                pass
            return False
        self._handle = handle
        return True

    def release(self) -> None:
        if self._handle is not None:
            import win32api
            handle, self._handle = self._handle, None
            try:
                win32api.CloseHandle(handle)
            except Exception:
                pass
