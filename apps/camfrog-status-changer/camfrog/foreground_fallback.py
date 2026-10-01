from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

log = logging.getLogger(__name__)

@dataclass
class ForegroundResult:
    ok: bool
    message: str


def _require_windows() -> None:
    if os.name != "nt":
        raise RuntimeError("Foreground fallback is Windows-only")


def apply_status_foreground(parent_hwnd: int, relative_x: float, relative_y: float, value: str) -> ForegroundResult:
    _require_windows()
    import pyperclip
    import win32api
    import win32con
    import win32gui
    from pywinauto.keyboard import send_keys

    hwnd = int(parent_hwnd)
    if not win32gui.IsWindow(hwnd):
        return ForegroundResult(False, "Camfrog window handle is no longer valid")

    previous_clipboard = None
    clipboard_saved = False
    try:
        placement = win32gui.GetWindowPlacement(hwnd)
        was_minimized = placement[1] == win32con.SW_SHOWMINIMIZED
        if was_minimized:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        time.sleep(0.20)
        if win32gui.GetForegroundWindow() != hwnd:
            return ForegroundResult(False, "Windows did not allow Camfrog to become the foreground window")

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = max(1, right - left)
        height = max(1, bottom - top)
        rx = min(1.0, max(0.0, float(relative_x)))
        ry = min(1.0, max(0.0, float(relative_y)))
        x = left + int(width * rx)
        y = top + int(height * ry)
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.12)

        text = str(value).replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
        try:
            previous_clipboard = pyperclip.paste()
            clipboard_saved = True
        except Exception:
            clipboard_saved = False
        pyperclip.copy(text)
        send_keys("^a")
        send_keys("^v")
        send_keys("{ENTER}")
        time.sleep(0.25)
        if was_minimized:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        return ForegroundResult(True, "Foreground fallback submitted one status message to Camfrog")
    except Exception as exc:
        log.exception("Foreground fallback failed")
        return ForegroundResult(False, f"Foreground fallback failed: {exc}")
    finally:
        if clipboard_saved:
            try:
                pyperclip.copy(previous_clipboard)
            except Exception:
                log.debug("Could not restore clipboard", exc_info=True)
