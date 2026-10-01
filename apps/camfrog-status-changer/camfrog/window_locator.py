from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Iterable

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class WindowMatch:
    hwnd: int
    score: int
    title: str = ""
    class_name: str = ""
    backend: str = ""


def score_candidate(title: str, class_name: str, visible: bool, area: int) -> int:
    title_l = str(title or "").casefold()
    cls_l = str(class_name or "").casefold()
    score = 0
    if "camfrog" in title_l:
        score += 400
    if "video chat" in title_l:
        score += 180
    if visible:
        score += 100
    if area >= 60000:
        score += 70
    if area >= 250000:
        score += 20
    if title_l:
        score += 20
    if "statuschanger" in title_l or "status changer" in title_l:
        score -= 1000
    if "camfrog" in cls_l:
        score += 30
    return score


def _require_windows() -> None:
    if os.name != "nt":
        raise RuntimeError("Camfrog window discovery is Windows-only")


def _valid_cached(hwnd: int, pids: set[int]) -> bool:
    if not hwnd:
        return False
    import win32gui

    try:
        if not win32gui.IsWindow(int(hwnd)):
            return False
        _tid, pid = win32gui.GetWindowThreadProcessId(int(hwnd))
        return int(pid) in pids
    except Exception:
        return False


def _from_pywinauto(pids: set[int], backend: str) -> list[WindowMatch]:
    from pywinauto import Desktop

    matches: list[WindowMatch] = []
    try:
        windows = Desktop(backend=backend).windows(visible_only=False)
    except TypeError:
        windows = Desktop(backend=backend).windows()

    for wrapper in windows:
        try:
            info = wrapper.element_info
            pid = int(getattr(info, "process_id", 0) or 0)
            if pid not in pids:
                continue
            hwnd = int(getattr(wrapper, "handle", 0) or getattr(info, "handle", 0) or 0)
            if not hwnd:
                continue
            title = wrapper.window_text() or ""
            class_name = str(getattr(info, "class_name", "") or "")
            rect = wrapper.rectangle()
            area = max(0, int(rect.width())) * max(0, int(rect.height()))
            try:
                visible = bool(wrapper.is_visible())
            except Exception:
                visible = False
            matches.append(
                WindowMatch(
                    hwnd,
                    score_candidate(title, class_name, visible, area),
                    title,
                    class_name,
                    backend,
                )
            )
        except Exception:
            continue
    return matches


def _from_win32(pids: set[int]) -> list[WindowMatch]:
    import win32gui

    matches: list[WindowMatch] = []

    def cb(hwnd, _):
        try:
            if not win32gui.IsWindow(hwnd):
                return True
            _tid, pid = win32gui.GetWindowThreadProcessId(hwnd)
            if int(pid) not in pids:
                return True
            title = win32gui.GetWindowText(hwnd) or ""
            class_name = win32gui.GetClassName(hwnd) or ""
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            area = max(0, right - left) * max(0, bottom - top)
            visible = bool(win32gui.IsWindowVisible(hwnd))
            matches.append(
                WindowMatch(
                    int(hwnd),
                    score_candidate(title, class_name, visible, area),
                    title,
                    class_name,
                    "win32-enum",
                )
            )
        except Exception:
            pass
        return True

    win32gui.EnumWindows(cb, None)
    return matches


def locate_camfrog_hwnd(pids: Iterable[int], cached_hwnd: int = 0) -> WindowMatch:
    """Find or reacquire Camfrog's best top-level HWND.

    Camfrog may recreate or hide its main window after minimize/tray actions, so
    discovery deliberately uses cached HWND validation, pywinauto UIA, pywinauto
    Win32 and raw EnumWindows as independent sources.
    """
    _require_windows()
    pid_set = {int(x) for x in pids if int(x) > 0}
    if not pid_set:
        raise RuntimeError("No Camfrog process is running")

    if _valid_cached(int(cached_hwnd or 0), pid_set):
        import win32gui

        hwnd = int(cached_hwnd)
        title = win32gui.GetWindowText(hwnd) or ""
        class_name = win32gui.GetClassName(hwnd) or ""
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        area = max(0, right - left) * max(0, bottom - top)
        visible = bool(win32gui.IsWindowVisible(hwnd))
        return WindowMatch(
            hwnd,
            score_candidate(title, class_name, visible, area) + 50,
            title,
            class_name,
            "cache",
        )

    candidates: list[WindowMatch] = []
    for backend in ("uia", "win32"):
        try:
            candidates.extend(_from_pywinauto(pid_set, backend))
        except Exception as exc:
            log.debug("pywinauto %s discovery failed: %s", backend, exc)

    try:
        candidates.extend(_from_win32(pid_set))
    except Exception as exc:
        log.debug("EnumWindows discovery failed: %s", exc)

    by_hwnd: dict[int, WindowMatch] = {}
    for item in candidates:
        previous = by_hwnd.get(item.hwnd)
        if previous is None or item.score > previous.score:
            by_hwnd[item.hwnd] = item

    if not by_hwnd:
        raise RuntimeError(
            "Camfrog process is running, but no usable top-level window was found. "
            "Restore Camfrog from the tray once, then retry."
        )

    ordered = sorted(by_hwnd.values(), key=lambda x: (x.score, x.hwnd), reverse=True)
    best = ordered[0]
    log.info(
        "Camfrog window reacquired: hwnd=%s backend=%s score=%s title=%r class=%r candidates=%s",
        best.hwnd,
        best.backend,
        best.score,
        best.title,
        best.class_name,
        [(x.hwnd, x.backend, x.score, x.title) for x in ordered[:5]],
    )
    return best
