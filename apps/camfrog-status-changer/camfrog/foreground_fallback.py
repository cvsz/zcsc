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


def _exact_status_edit(parent_hwnd: int):
    """Return only the exact known Camfrog custom-status edit control."""
    from pywinauto import Desktop

    root = Desktop(backend="win32").window(handle=int(parent_hwnd))
    for ctrl in root.descendants():
        try:
            cls = str(getattr(ctrl.element_info, "class_name", "") or "").casefold()
            if cls == "cedit4comboinnerts":
                return ctrl
        except Exception:
            continue
    return None


def apply_status_foreground(parent_hwnd: int, relative_x: float, relative_y: float, value: str) -> ForegroundResult:
    _require_windows()
    import pyperclip
    import win32con
    import win32gui
    from pywinauto import Desktop, mouse
    from pywinauto.keyboard import send_keys

    hwnd = int(parent_hwnd)
    if not win32gui.IsWindow(hwnd):
        return ForegroundResult(False, "Camfrog window handle is no longer valid")

    previous_clipboard = None
    clipboard_saved = False
    was_minimized = False
    try:
        placement = win32gui.GetWindowPlacement(hwnd)
        was_minimized = placement[1] == win32con.SW_SHOWMINIMIZED
        if was_minimized:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        try:
            Desktop(backend="win32").window(handle=hwnd).set_focus()
        except Exception:
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass
        time.sleep(0.20)

        edit = None
        try:
            edit = _exact_status_edit(hwnd)
        except Exception:
            log.debug("Exact status edit discovery failed", exc_info=True)

        if edit is not None:
            try:
                edit.set_focus()
            except Exception:
                edit.click_input()
            log.info("Foreground commit target: exact CEdit4ComboInnerTS")
        else:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = max(1, right - left)
            height = max(1, bottom - top)
            rx = min(1.0, max(0.0, float(relative_x)))
            ry = min(1.0, max(0.0, float(relative_y)))
            x = left + int(width * rx)
            y = top + int(height * ry)
            mouse.click(button="left", coords=(x, y))
            log.info("Foreground commit target: configured status-field coordinate (%s,%s)", x, y)

        time.sleep(0.12)
        text = str(value).replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
        try:
            previous_clipboard = pyperclip.paste()
            clipboard_saved = True
        except Exception:
            pass

        pyperclip.copy(text)
        send_keys("^a")
        send_keys("^v")
        send_keys("{ENTER}")
        time.sleep(0.25)

        if was_minimized:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        return ForegroundResult(True, "Foreground pywinauto submitted one status message to Camfrog")
    except Exception as exc:
        log.exception("Foreground fallback failed")
        return ForegroundResult(False, f"Foreground fallback failed: {exc}")
    finally:
        if clipboard_saved:
            try:
                pyperclip.copy(previous_clipboard)
            except Exception:
                log.debug("Could not restore clipboard", exc_info=True)
