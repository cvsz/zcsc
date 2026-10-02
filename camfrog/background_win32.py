from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Callable, Iterable

from status_text import comparable_status

log = logging.getLogger(__name__)


class AmbiguousNativeControlError(RuntimeError):
    """Raised when background automation cannot uniquely identify a control."""

STATUS_INPUT_SETTLE_SECONDS = 0.45
STATUS_COMMIT_SETTLE_SECONDS = 0.25


@dataclass
class BackgroundResult:
    ok: bool
    message: str
    hwnd: int = 0
    verified: bool = False
    observed_value: str = ""
    ambiguous: bool = False


def _require_windows() -> None:
    if os.name != "nt":
        raise RuntimeError("Win32 background automation is available on Windows only")


def _make_wparam(low: int, high: int) -> int:
    return (low & 0xFFFF) | ((high & 0xFFFF) << 16)


def _send_timeout(hwnd: int, msg: int, wparam=0, lparam=0, timeout_ms: int = 800):
    import win32con
    import win32gui
    return win32gui.SendMessageTimeout(
        hwnd, msg, wparam, lparam,
        win32con.SMTO_ABORTIFHUNG | win32con.SMTO_BLOCK,
        timeout_ms,
    )


def _children(parent_hwnd: int) -> list[int]:
    import win32gui
    result: list[int] = []
    try:
        win32gui.EnumChildWindows(parent_hwnd, lambda h, _: result.append(h) or True, None)
    except Exception:
        pass
    return result


def enumerate_native_controls(parent_hwnd: int) -> list[dict]:
    _require_windows()
    import win32gui
    out: list[dict] = []
    for hwnd in [parent_hwnd] + _children(parent_hwnd):
        try:
            out.append({
                "hwnd": int(hwnd),
                "control_id": int(win32gui.GetDlgCtrlID(hwnd)),
                "class_name": win32gui.GetClassName(hwnd) or "",
                "text": win32gui.GetWindowText(hwnd) or "",
                "visible": bool(win32gui.IsWindowVisible(hwnd)),
                "enabled": bool(win32gui.IsWindowEnabled(hwnd)),
                "rect": list(win32gui.GetWindowRect(hwnd)),
            })
        except Exception:
            continue
    return out


def _smallest_child_at_point(parent_hwnd: int, screen_x: int, screen_y: int) -> int:
    import win32gui
    candidates: list[tuple[int, int]] = []
    for hwnd in _children(parent_hwnd):
        try:
            if not win32gui.IsWindow(hwnd):
                continue
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            if left <= screen_x < right and top <= screen_y < bottom:
                area = max(1, right - left) * max(1, bottom - top)
                candidates.append((area, hwnd))
        except Exception:
            pass
    if candidates:
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]
    return parent_hwnd


def _read_text(hwnd: int) -> str:
    import win32gui
    try:
        return win32gui.GetWindowText(hwnd) or ""
    except Exception:
        return ""


def _class_name(hwnd: int) -> str:
    import win32gui
    try:
        return win32gui.GetClassName(hwnd) or ""
    except Exception:
        return ""


def _find_edit_candidate(hwnd: int) -> int | None:
    pool = [hwnd] + _children(hwnd)
    for child in pool:
        cls = _class_name(child).lower()
        if "edit" in cls or "richedit" in cls:
            return child
    return None


def _find_camfrog_status_combo(
    parent_hwnd: int,
    current_text: str = "",
    known_statuses: Iterable[str] = (),
) -> int | None:
    """Locate Camfrog's custom-status CComboBoxTS using text + geometry scoring."""
    import win32gui

    known = {str(x).strip().casefold() for x in known_statuses if str(x).strip()}
    candidates: list[tuple[int, int]] = []
    try:
        pl, pt, pr, pb = win32gui.GetWindowRect(parent_hwnd)
        ph = max(1, pb - pt)
        pw = max(1, pr - pl)
    except Exception:
        pl = pt = pr = pb = 0
        ph = pw = 1

    for hwnd in _children(parent_hwnd):
        try:
            cls = _class_name(hwnd).lower()
            if cls != "ccomboboxts" and "combobox" not in cls:
                continue
            text = _read_text(hwnd).strip()
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = max(0, right - left)
            height = max(0, bottom - top)
            rel_y = (top - pt) / ph if ph else 1.0
            rel_x = (left - pl) / pw if pw else 1.0
            score = 0
            if cls == "ccomboboxts":
                score += 100
            if current_text and text.casefold() == current_text.strip().casefold():
                score += 500
            if text and text.casefold() in known:
                score += 400
            # Screenshot/build: custom status spans most of window under profile header.
            if 0.12 <= rel_y <= 0.32:
                score += 120
            if rel_x <= 0.15:
                score += 20
            if width >= int(pw * 0.60):
                score += 100
            elif width >= 160:
                score += 30
            if 18 <= height <= 60:
                score += 20
            candidates.append((score, hwnd))
        except Exception:
            continue

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score = candidates[0][0]
    if sum(score == best_score for score, _hwnd in candidates) > 1:
        raise AmbiguousNativeControlError(
            "Multiple Camfrog status controls matched equally; background fallback was stopped"
        )
    log.info("Camfrog combo candidates: %s", candidates[:5])
    return candidates[0][1]


def _send_key(hwnd: int, vk: int, *, ctrl: bool = False) -> None:
    import win32con
    if ctrl:
        _send_timeout(hwnd, win32con.WM_KEYDOWN, win32con.VK_CONTROL, 0)
    _send_timeout(hwnd, win32con.WM_KEYDOWN, vk, 0)
    _send_timeout(hwnd, win32con.WM_KEYUP, vk, 0)
    if ctrl:
        _send_timeout(hwnd, win32con.WM_KEYUP, win32con.VK_CONTROL, 0)


def _paste_text(hwnd: int, value: str) -> None:
    """Paste text into an edit control while restoring the user's text clipboard."""
    import pyperclip
    import win32con

    old_clipboard = pyperclip.paste()
    try:
        pyperclip.copy(value)
        _send_key(hwnd, ord("A"), ctrl=True)
        _send_key(hwnd, win32con.VK_BACK)
        _send_timeout(hwnd, win32con.WM_PASTE, 0, 0, timeout_ms=1200)
    finally:
        pyperclip.copy(old_clipboard or "")


def _parent_chain(hwnd: int, limit: int = 8) -> list[int]:
    import win32gui
    out: list[int] = []
    seen: set[int] = set()
    current = int(hwnd)
    for _ in range(limit):
        try:
            parent = int(win32gui.GetParent(current) or 0)
        except Exception:
            break
        if not parent or parent in seen:
            break
        seen.add(parent)
        out.append(parent)
        current = parent
    return out


def _notify_combo_parent(top_hwnd: int, combo_hwnd: int) -> None:
    """Send combo notifications to the real owner chain.

    Camfrog's CComboBoxTS is nested. Sending WM_COMMAND only to the top-level
    window misses the immediate owner in builds where the status handler lives
    on a child panel/dialog. We notify immediate parent first and then bubble
    upward, stopping at the top-level window.
    """
    import win32gui

    control_id = int(win32gui.GetDlgCtrlID(combo_hwnd))
    if control_id < 0:
        return
    notifications = [
        getattr(win32con, "CBN_EDITUPDATE", 6),
        getattr(win32con, "CBN_EDITCHANGE", 5),
    ]
    targets = _parent_chain(combo_hwnd)
    if int(top_hwnd) not in targets:
        targets.append(int(top_hwnd))

    wparam_cache = [_make_wparam(control_id, code) for code in notifications]
    for owner in targets:
        for wp, code in zip(wparam_cache, notifications):
            try:
                _send_timeout(owner, win32con.WM_COMMAND, wp, combo_hwnd, 1000)
            except Exception as exc:
                log.debug("Combo notification %s to hwnd=%s failed: %s", code, owner, exc)


def _notify_edit_parent(edit_hwnd: int) -> None:
    """Emit standard edit-change notifications without foreground activation."""
    import win32con
    import win32gui

    if not edit_hwnd:
        return
    control_id = int(win32gui.GetDlgCtrlID(edit_hwnd))
    if control_id < 0:
        return
    parent = int(win32gui.GetParent(edit_hwnd) or 0)
    if not parent:
        return
    for code in (getattr(win32con, "EN_UPDATE", 0x0400), getattr(win32con, "EN_CHANGE", 0x0300)):
        try:
            _send_timeout(parent, win32con.WM_COMMAND, _make_wparam(control_id, code), edit_hwnd, 1000)
        except Exception as exc:
            log.debug("Edit notification %s failed: %s", code, exc)

def _verify_combo_value(combo_hwnd: int, value: str, retries: int = 4) -> tuple[bool, str]:
    expected = comparable_status(value)
    observed = ""
    edit = _find_edit_candidate(combo_hwnd)
    for _ in range(retries):
        for hwnd in ([edit] if edit else []) + [combo_hwnd]:
            if not hwnd:
                continue
            observed = _read_text(hwnd).strip()
            if comparable_status(observed) == expected:
                return True, observed
        time.sleep(0.12)
    return False, observed


def _commit_status_input(
    target_hwnd: int,
    expected_value: str,
    *,
    read_value: Callable[[int], str] | None = None,
) -> tuple[bool, str]:
    """Poll a bounded time for the exact edit value, then dispatch one Enter."""
    import win32con

    reader = read_value or _read_text
    expected = comparable_status(expected_value)
    deadline = time.monotonic() + STATUS_INPUT_SETTLE_SECONDS
    observed = ""
    while True:
        observed = str(reader(target_hwnd) or "").strip()
        if comparable_status(observed) == expected:
            _send_key(target_hwnd, win32con.VK_RETURN)
            time.sleep(STATUS_COMMIT_SETTLE_SECONDS)
            return True, observed
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False, observed
        time.sleep(min(0.025, remaining))


def commit_verified_ui_status_background(
    parent_hwnd: int,
    combo_hwnd: int,
    edit_hwnd: int,
    value: str,
    *,
    read_verified_text: Callable[[int], str] | None = None,
) -> BackgroundResult:
    """Commit UIA-verified text without writing or typing the payload again."""
    _require_windows()
    import win32gui

    if not value.strip():
        return BackgroundResult(False, "Status cannot be empty", combo_hwnd)
    for hwnd, label in ((parent_hwnd, "Camfrog window"), (combo_hwnd, "status combo"), (edit_hwnd, "status edit")):
        if not hwnd or not win32gui.IsWindow(hwnd):
            return BackgroundResult(False, f"{label} handle is no longer valid", combo_hwnd)

    # The UIA child Edit already confirmed this exact value. Do not issue
    # WM_SETTEXT/WM_PASTE here: Win32's text getter can disagree with UIA for
    # Camfrog's custom combo, and a second writer can append the same payload.
    # Commit with one Enter on the verified editor. Sending Enter to both the
    # edit and combo, followed by selection notifications and a button click,
    # can submit the same text multiple times or alter the editor contents.
    committed, observed = _commit_status_input(
        edit_hwnd,
        value,
        read_value=read_verified_text,
    )
    if not committed:
        return BackgroundResult(
            False,
            "Camfrog status Edit changed before Enter; commit was skipped",
            combo_hwnd,
            False,
            observed,
        )
    return BackgroundResult(
        True,
        "Status text verified; one Enter sent to Camfrog (server acceptance is not independently confirmed)",
        combo_hwnd,
        True,
        observed,
    )


def _set_native_combo_text(parent_hwnd: int, combo_hwnd: int, value: str) -> BackgroundResult:
    edit = _find_edit_candidate(combo_hwnd)
    target = edit or combo_hwnd

    # Prefer clipboard paste consistently with the foreground UIA path. Direct
    # WM_SETTEXT is not accepted by every Camfrog status-combo build.
    _paste_text(target, value)
    if edit:
        _notify_edit_parent(edit)
    _notify_combo_parent(parent_hwnd, combo_hwnd)
    entered, observed = _verify_combo_value(combo_hwnd, value)
    if not entered:
        return BackgroundResult(
            False,
            "Camfrog status field did not accept the text; commit was skipped",
            combo_hwnd,
            False,
            observed,
        )

    committed, observed = _commit_status_input(target, value)
    if not committed:
        return BackgroundResult(
            False,
            "Camfrog status Edit changed before Enter; commit was skipped",
            combo_hwnd,
            False,
            observed,
        )
    return BackgroundResult(
        True,
        "Status text verified before one Enter dispatch; server acceptance is not independently confirmed",
        combo_hwnd,
        True,
        observed,
    )


def set_status_background(
    parent_hwnd: int,
    relative_x: float,
    relative_y: float,
    value: str,
    *,
    current_text: str = "",
    known_statuses: Iterable[str] = (),
    allow_coordinate_fallback: bool = False,
) -> BackgroundResult:
    """Background-first Camfrog status edit without activating/restoring Camfrog."""
    _require_windows()
    if not value:
        return BackgroundResult(False, "Status cannot be empty")
    if not (0.0 <= relative_x <= 1.0 and 0.0 <= relative_y <= 1.0):
        return BackgroundResult(False, "Relative target coordinates must be between 0.0 and 1.0")

    import win32gui

    if not win32gui.IsWindow(parent_hwnd):
        return BackgroundResult(False, "Camfrog window handle is no longer valid")

    try:
        combo = _find_camfrog_status_combo(
            parent_hwnd,
            current_text=current_text,
            known_statuses=known_statuses,
        )
        if combo:
            result = _set_native_combo_text(parent_hwnd, combo, value)
            if result.ok:
                return result
            # If we confidently found CComboBoxTS but could not commit it, do not
            # return a false success from the coordinate compatibility path.
            if _class_name(combo).lower() == "ccomboboxts":
                return result

        if not allow_coordinate_fallback:
            return BackgroundResult(
                False,
                "Coordinate fallback is disabled until per-monitor v2 DPI awareness is confirmed",
                parent_hwnd,
            )

        # Compatibility route for older/different builds.
        try:
            placement = win32gui.GetWindowPlacement(parent_hwnd)
            normal_left, normal_top, normal_right, normal_bottom = placement[4]
            width = max(1, normal_right - normal_left)
            height = max(1, normal_bottom - normal_top)
            screen_x = int(normal_left + width * relative_x)
            screen_y = int(normal_top + height * relative_y)
        except Exception:
            left, top, right, bottom = win32gui.GetWindowRect(parent_hwnd)
            width = max(1, right - left)
            height = max(1, bottom - top)
            screen_x = int(left + width * relative_x)
            screen_y = int(top + height * relative_y)

        target_hwnd = _smallest_child_at_point(parent_hwnd, screen_x, screen_y)
        edit_hwnd = _find_edit_candidate(target_hwnd)
        if edit_hwnd:
            # Keep compatibility builds on the same paste path as the native
            # status control. A direct WM_SETTEXT can update a shadow value
            # without populating Camfrog's actual editable status field.
            _paste_text(edit_hwnd, value)
            _notify_edit_parent(edit_hwnd)
            committed, observed = _commit_status_input(edit_hwnd, value)
            if not committed:
                return BackgroundResult(
                    False,
                    "Background status Edit did not verify the pasted text; commit was skipped",
                    edit_hwnd,
                    False,
                    observed,
                )
            return BackgroundResult(
                True,
                "Status text verified before one Enter dispatch; server acceptance is not independently confirmed",
                edit_hwnd,
                True,
                observed,
            )

        # Coordinates alone do not establish that this is Camfrog's status
        # editor. Never paste or send Enter to an unknown child/control.
        return BackgroundResult(
            False,
            "Background compatibility control has no uniquely identified Edit; paste and commit were skipped",
            target_hwnd,
            False,
            _read_text(target_hwnd),
        )
    except AmbiguousNativeControlError as exc:
        return BackgroundResult(False, str(exc), parent_hwnd, False, "", True)
    except Exception as exc:
        log.exception("Background Win32 automation failed")
        return BackgroundResult(False, f"Background Win32 automation failed: {exc}")
