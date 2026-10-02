"""Windows per-monitor-v2 DPI awareness setup for coordinate automation."""

from __future__ import annotations

import os


DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
_PER_MONITOR_V2_READY: bool | None = None


class _Win32DpiApi:
    def __init__(self) -> None:
        import ctypes

        self._ctypes = ctypes
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._set_context = self._user32.SetProcessDpiAwarenessContext
        self._set_context.argtypes = [ctypes.c_void_p]
        self._set_context.restype = ctypes.c_bool
        self._get_context = self._user32.GetThreadDpiAwarenessContext
        self._get_context.argtypes = []
        self._get_context.restype = ctypes.c_void_p
        self._contexts_equal = self._user32.AreDpiAwarenessContextsEqual
        self._contexts_equal.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self._contexts_equal.restype = ctypes.c_bool

    def set_process_dpi_awareness_context(self, context: int) -> bool:
        return bool(self._set_context(self._ctypes.c_void_p(context)))

    def get_thread_dpi_awareness_context(self):
        return self._get_context()

    def are_dpi_awareness_contexts_equal(self, actual, expected: int) -> bool:
        return bool(
            self._contexts_equal(actual, self._ctypes.c_void_p(expected))
        )


def configure_process_dpi_awareness(*, api=None) -> bool:
    """Set or confirm per-monitor-v2 before Tk creates its first window.

    ``api`` is an injection seam for platform-independent tests. If the process
    already has a different awareness context, coordinate automation stays off.
    """
    global _PER_MONITOR_V2_READY

    if api is None:
        if os.name != "nt":
            _PER_MONITOR_V2_READY = False
            return False
        try:
            api = _Win32DpiApi()
        except Exception:
            _PER_MONITOR_V2_READY = False
            return False

    ready = False
    try:
        ready = bool(
            api.set_process_dpi_awareness_context(
                DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
            )
        )
    except Exception:
        ready = False

    if not ready:
        try:
            current = api.get_thread_dpi_awareness_context()
            ready = bool(
                api.are_dpi_awareness_contexts_equal(
                    current,
                    DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2,
                )
            )
        except Exception:
            ready = False

    _PER_MONITOR_V2_READY = ready
    return ready


def per_monitor_v2_ready() -> bool:
    """Return whether per-monitor-v2 awareness was positively confirmed."""
    return _PER_MONITOR_V2_READY is True
