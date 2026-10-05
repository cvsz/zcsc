from __future__ import annotations

import logging
import os
import re
import subprocess
import time
import threading
from dataclasses import dataclass

from .detector import find_process_by_pid, find_processes
from .background_win32 import (
    STATUS_INPUT_SETTLE_SECONDS,
    STATUS_COMMIT_SETTLE_SECONDS,
    set_status_background,
)
from .native_profile import identify_profile
from status_text import comparable_status
from system.dpi_awareness import per_monitor_v2_ready

log = logging.getLogger(__name__)

FOREGROUND_VERIFY_TIMEOUT_SECONDS = 1.0
FOREGROUND_VERIFY_POLL_SECONDS = 0.025

_TOV_SAFE_ACTION_TITLES = {
    "apply",
    "cancel",
    "font",
    "ok",
    "text over video",
}
_TOV_SAFE_CHECKBOX_TITLES = {"enable text over video settings"}
_TOV_SAFE_STATIC_LABELS = {
    "background:",
    "horizontal alignment:",
    "text color:",
    "transparency:",
    "vertical alignment:",
}


@dataclass
class ChangeResult:
    ok: bool
    message: str
    previous_value: str = ""
    new_value: str = ""


class CamfrogInstanceAmbiguityError(RuntimeError):
    """Raised when more than one client could receive an automation action."""


class AmbiguousStatusControlError(RuntimeError):
    """Raised when status text could be written to more than one UI control."""


class UnverifiedStatusControlError(RuntimeError):
    """Raised when UIA exposes only generic controls that cannot be identified as status."""


class CamfrogController:
    def __init__(self, config: dict, *, clock=None):
        self.config = config
        self.clock = clock
        self._apply_lock = threading.Lock()
        self._runtime_lock = threading.Lock()
        self._last_send_monotonic = 0.0
        self._bound_pid: int | None = None
        self._session_state = "unbound"

    def _monotonic(self) -> float:
        return float(self.clock.monotonic()) if self.clock is not None else time.monotonic()

    def _sleep(self, seconds: float) -> None:
        if self.clock is not None:
            self.clock.sleep(seconds)
        else:
            time.sleep(seconds)

    @staticmethod
    def _is_cancelled(cancelled) -> bool:
        return bool(cancelled and cancelled())

    def _acquire_apply_lock(self, cancelled=None) -> bool:
        """Acquire the send lock while allowing a stopped rotation to exit."""
        if cancelled is None:
            self._apply_lock.acquire()
            return True
        while not self._is_cancelled(cancelled):
            if self._apply_lock.acquire(timeout=0.05):
                if self._is_cancelled(cancelled):
                    self._apply_lock.release()
                    return False
                return True
        return False

    @property
    def bound_pid(self) -> int | None:
        return self._bound_pid

    def _configured_executable(self) -> str:
        return str(self.config.get("camfrog", {}).get("executable", "")).strip()

    def _bound_process(self):
        if not self._bound_pid:
            return None
        process = find_process_by_pid(
            self._bound_pid,
            executable_path=self._configured_executable() or None,
        )
        if process is None:
            log.warning("Bound Camfrog PID %s is no longer valid; marking session lost", self._bound_pid)
            self._bound_pid = None
            self._session_state = "lost"
        return process

    def bind_pid(self, pid: int) -> ChangeResult:
        if not self._runtime_lock.acquire(blocking=False):
            return ChangeResult(False, "Another Camfrog runtime connection operation is already in progress")
        try:
            process = find_process_by_pid(
                int(pid),
                executable_path=self._configured_executable() or None,
            )
            if process is None:
                return ChangeResult(False, "Selected PID is not the configured Camfrog executable or is no longer running")
            self._bound_pid = int(process.pid)
            self._session_state = "connected"
            return ChangeResult(True, f"Camfrog PID {self._bound_pid} connected")
        finally:
            self._runtime_lock.release()

    def disconnect_pid(self) -> ChangeResult:
        with self._runtime_lock:
            previous = self._bound_pid
            self._bound_pid = None
            self._session_state = "disconnected"
        return ChangeResult(True, f"Camfrog PID {previous} disconnected" if previous else "Camfrog is disconnected")

    def available_client_processes(self):
        return find_processes(executable_path=self._configured_executable() or None)

    def client_processes(self):
        process = self._bound_process()
        return [process] if process is not None else []

    def _wait_for_send_slot(self, cancelled=None) -> bool:
        """Enforce spacing between Camfrog send attempts instead of dropping early ones."""
        minimum = max(1, int(self.config.get("advanced", {}).get("minimum_interval_seconds", 5)))
        while self._last_send_monotonic:
            if self._is_cancelled(cancelled):
                return False
            remaining = minimum - (self._monotonic() - self._last_send_monotonic)
            if remaining <= 0:
                break
            log.info("Waiting %.2fs before the next Camfrog status send", remaining)
            self._sleep(min(remaining, 0.05) if cancelled is not None else remaining)
        if self._is_cancelled(cancelled):
            return False
        # Reserve this slot as well as recording the actual dispatch below. If
        # preparation later fails, retrying still observes the send guard.
        self._last_send_monotonic = self._monotonic()
        return True

    def _record_send_time(self) -> None:
        """Record the dispatch time so the next request spaces actual sends."""
        self._last_send_monotonic = self._monotonic()

    def _foreground_status_snapshot(self, window, editor, expected: str) -> tuple[bool, str, str]:
        """Check process ownership and the exact editor value before an Enter."""
        try:
            import win32gui

            expected_pid = int(window.process_id())
            main_hwnd = int(window.handle)
            edit_hwnd = int(editor.handle)
            if not expected_pid or not edit_hwnd or not win32gui.IsWindow(edit_hwnd):
                return False, "", "the verified Camfrog Edit handle is no longer valid"

            _thread_id, main_pid = win32gui.GetWindowThreadProcessId(main_hwnd)
            _thread_id, edit_pid = win32gui.GetWindowThreadProcessId(edit_hwnd)
            if int(main_pid) != expected_pid or int(edit_pid) != expected_pid:
                return False, "", "the selected status Edit no longer belongs to the selected Camfrog process"

            observed = self._read_value(editor).strip()
            if comparable_status(observed) != comparable_status(expected):
                return False, observed, "the status Edit text changed after verification"

            foreground_hwnd = int(win32gui.GetForegroundWindow() or 0)
            if not foreground_hwnd:
                return False, observed, "Windows has no foreground window"
            _thread_id, foreground_pid = win32gui.GetWindowThreadProcessId(foreground_hwnd)
            if int(foreground_pid) != expected_pid:
                return False, observed, "another process owns the foreground window"
            return True, observed, ""
        except Exception as exc:
            return False, "", f"foreground or status Edit verification failed: {exc}"

    def _wait_for_foreground_status(self, window, editor, expected: str) -> tuple[bool, str, str]:
        """Poll foreground ownership briefly, then validate the editor again."""
        deadline = self._monotonic() + FOREGROUND_VERIFY_TIMEOUT_SECONDS
        observed = ""
        reason = "another process owns the foreground window"
        while True:
            ready, observed, reason = self._foreground_status_snapshot(window, editor, expected)
            if ready:
                return True, observed, ""
            if reason != "another process owns the foreground window":
                return False, observed, reason
            remaining = deadline - self._monotonic()
            if remaining <= 0:
                return False, observed, reason
            self._sleep(min(FOREGROUND_VERIFY_POLL_SECONDS, remaining))

    def ensure_running(self) -> ChangeResult:
        """Validate the currently bound PID without discovering or launching a client."""
        bound = self._bound_process()
        if bound is not None:
            self._session_state = "connected"
            return ChangeResult(True, f"Camfrog PID {bound.pid} is connected")
        if self._session_state == "lost":
            return ChangeResult(
                False,
                "The bound Camfrog PID was lost. Use Start / Connect or Bind PID to establish a new session.",
            )
        if self._session_state == "disconnected":
            return ChangeResult(
                False,
                "Camfrog is disconnected. Use Start / Connect or Bind PID to establish a session.",
            )
        return ChangeResult(
            False,
            "No Camfrog PID is connected. Use Start / Connect or Bind PID before automation.",
        )

    def start_or_connect(self) -> ChangeResult:
        """Explicitly discover or launch Camfrog and bind exactly one verified PID."""
        if not self._runtime_lock.acquire(blocking=False):
            return ChangeResult(False, "Another Camfrog runtime connection operation is already in progress")
        try:
            bound = self._bound_process()
            if bound is not None:
                self._session_state = "connected"
                return ChangeResult(True, f"Camfrog PID {bound.pid} is connected")

            exe = self._configured_executable()
            if not exe:
                return ChangeResult(False, "Camfrog executable is not configured")

            existing = self.available_client_processes()
            if len(existing) == 1:
                self._bound_pid = int(existing[0].pid)
                self._session_state = "connected"
                return ChangeResult(True, f"Connected to existing Camfrog PID {self._bound_pid}")
            if len(existing) > 1:
                pids = ", ".join(str(int(process.pid)) for process in existing)
                return ChangeResult(
                    False,
                    f"Multiple Camfrog processes are already running ({pids}). "
                    "Select one PID explicitly with Bind PID.",
                )

            before = {int(process.pid) for process in existing}
            try:
                launched = subprocess.Popen([exe], shell=False)
            except Exception as exc:
                return ChangeResult(False, f"Failed to start Camfrog: {exc}")

            launched_pid = int(launched.pid)
            for _ in range(40):
                direct = find_process_by_pid(launched_pid, executable_path=exe)
                if direct is not None:
                    self._bound_pid = launched_pid
                    self._session_state = "connected"
                    return ChangeResult(True, f"Camfrog started and bound to PID {launched_pid}")

                candidates = [
                    process
                    for process in self.available_client_processes()
                    if int(process.pid) not in before
                ]
                if len(candidates) == 1:
                    self._bound_pid = int(candidates[0].pid)
                    self._session_state = "connected"
                    return ChangeResult(
                        True,
                        f"Camfrog started and rebound to child PID {self._bound_pid}",
                    )
                if len(candidates) > 1:
                    self._session_state = "unbound"
                    return ChangeResult(
                        False,
                        "Camfrog launch produced multiple new client processes; refusing to guess a PID",
                    )
                time.sleep(0.25)

            self._session_state = "unbound"
            return ChangeResult(False, "Camfrog did not expose a verifiable client PID within timeout")
        finally:
            self._runtime_lock.release()

    def _desktop(self):
        if os.name != "nt":
            raise RuntimeError("Windows UI Automation is only available on Windows")
        from pywinauto import Desktop
        return Desktop(backend="uia")

    def _find_window_by_pid(self):
        """Return the best top-level window owned by the single bound PID."""
        if os.name != "nt":
            return None

        import win32gui

        process = self._bound_process()
        if process is None:
            return None
        target_pid = int(process.pid)
        candidates = []

        def enum_cb(hwnd, _):
            try:
                if not win32gui.IsWindow(hwnd):
                    return True
                _tid, pid = win32gui.GetWindowThreadProcessId(hwnd)
                if int(pid) != target_pid:
                    return True

                title = win32gui.GetWindowText(hwnd) or ""
                cls = win32gui.GetClassName(hwnd) or ""
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                width = max(0, right - left)
                height = max(0, bottom - top)
                area = width * height

                score = 0
                if "camfrog" in title.casefold():
                    score += 300
                if "video chat" in title.casefold():
                    score += 150
                if win32gui.IsWindowVisible(hwnd):
                    score += 80
                if area >= 200 * 300:
                    score += 60
                if width >= 250 and height >= 400:
                    score += 40
                if title:
                    score += 20
                candidates.append((score, area, int(hwnd), title, cls))
            except Exception:
                pass
            return True

        win32gui.EnumWindows(enum_cb, None)
        if not candidates:
            return None

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        best_rank = candidates[0][:2]
        best_candidates = [item for item in candidates if item[:2] == best_rank]
        if len(best_candidates) != 1:
            raise CamfrogInstanceAmbiguityError(
                f"Camfrog PID {target_pid} exposes multiple equally ranked top-level windows; refusing to guess"
            )
        best = best_candidates[0]
        hwnd = best[2]
        log.info(
            "Camfrog window selected inside bound PID %s: hwnd=%s title=%r class=%r score=%s",
            target_pid, hwnd, best[3], best[4], best[0],
        )
        return self._desktop().window(handle=hwnd)

    def find_window(self):
        process = self._bound_process()
        if process is None:
            result = self.ensure_running()
            raise RuntimeError(result.message)

        target_pid = int(process.pid)
        win = self._find_window_by_pid()
        if win is None:
            raise RuntimeError(
                f"Camfrog PID {target_pid} is running, but no top-level window owned by that PID was found"
            )
        return win

    def native_profile_info(self) -> dict:
        exe = self.config.get("camfrog", {}).get("executable", "")
        try:
            profile, digest = identify_profile(exe)
        except Exception as exc:
            log.warning("Camfrog fingerprint failed: %s", exc)
            return {"matched": False, "sha256": "", "name": "", "error": str(exc)}
        return {
            "matched": bool(profile),
            "sha256": digest,
            "name": profile.name if profile else "",
            "architecture": profile.architecture if profile else "",
            "image_base": profile.image_base if profile else None,
            "classes": list(profile.classes) if profile else [],
            "anchors": dict(profile.anchors) if profile else {},
        }

    def inspect_controls(self) -> list[dict]:
        win = self.find_window()
        out = []
        for ctrl in win.descendants():
            try:
                info = ctrl.element_info
                out.append({
                    "title": ctrl.window_text(),
                    "control_type": info.control_type,
                    "automation_id": info.automation_id,
                    "class_name": info.class_name,
                })
            except Exception:
                continue
        return out

    def inspect_chat_controls(self) -> list[dict]:
        """Return visible UIA control metadata for the selected Camfrog process.

        Control names and values are deliberately omitted because chat history
        may contain private message text. Window titles are retained so an
        operator can configure the title fragment for each chat type.
        """
        main = self.find_window()
        target_pid = int(main.process_id())
        rows: list[dict] = []
        for index, window in enumerate(self._desktop().windows(visible_only=True), start=1):
            try:
                if int(window.process_id()) != target_pid:
                    continue
                title = str(window.window_text() or "").strip()
                window_type = str(getattr(window.element_info, "control_type", "") or "")
                controls = []
                for control in window.descendants():
                    try:
                        info = control.element_info
                        control_type = str(info.control_type or "")
                        automation_id = str(info.automation_id or "")
                        class_name = str(info.class_name or "")
                        if automation_id or control_type in {"Document", "List", "ListItem", "Text", "Edit", "Button", "Pane"}:
                            controls.append({
                                "control_type": control_type,
                                "automation_id": automation_id,
                                "class_name": class_name,
                            })
                    except Exception:
                        continue
                rows.append({
                    "window_index": index,
                    "window_title": title,
                    "window_control_type": window_type,
                    "controls": controls[:500],
                })
            except Exception:
                continue
        return rows

    @staticmethod
    def _video_overlay_control_metadata(control) -> dict:
        """Return identifiers for TOV controls without collecting entered values."""
        info = control.element_info
        control_type = str(info.control_type or "")
        title = str(control.window_text() or "").strip()
        normalized_title = title.casefold()
        safe_title = ""
        if control_type in {"Button", "Tab", "TabItem"} and normalized_title in _TOV_SAFE_ACTION_TITLES:
            safe_title = title
        elif control_type == "CheckBox" and normalized_title in _TOV_SAFE_CHECKBOX_TITLES:
            safe_title = title
        elif control_type == "Text" and normalized_title in _TOV_SAFE_STATIC_LABELS:
            safe_title = title
        return {
            "title": safe_title,
            "control_type": control_type,
            "automation_id": str(info.automation_id or ""),
            "class_name": str(info.class_name or ""),
        }

    def inspect_video_overlay_controls(self) -> list[dict]:
        """Inspect the selected Camfrog process while leaving TOV state untouched.

        Edit/combo values are deliberately excluded so overlay text and selected
        colors are not copied into the diagnostic report. Camfrog hosts Settings
        in different top-level windows across versions, so discovery includes all
        visible windows belonging to the configured Camfrog process.
        """
        processes = self.client_processes()
        if not processes:
            result = self.ensure_running()
            raise RuntimeError("No Camfrog process is bound. " + result.message)
        target_pids = {int(process.pid) for process in processes}

        rows: list[dict] = []
        for window in self._desktop().windows(visible_only=True):
            try:
                process_id = int(window.process_id())
                if process_id not in target_pids:
                    continue
                title = str(window.window_text() or "").strip()
                normalized_title = " ".join(title.casefold().split())
                if "settings" in normalized_title or "text over video" in normalized_title:
                    safe_window_title = "Camfrog Settings"
                    match_reason = "settings_title"
                elif "camfrog" in normalized_title or "video chat" in normalized_title:
                    safe_window_title = "Camfrog Video Chat"
                    match_reason = "camfrog_window"
                else:
                    # Never copy an arbitrary window title: it may contain a
                    # room name, login, or other user-provided text.
                    safe_window_title = ""
                    match_reason = "other_camfrog_window"

                controls = []
                for control in window.descendants():
                    try:
                        controls.append(self._video_overlay_control_metadata(control))
                    except Exception:
                        continue

                has_tov_markers = any(
                    control["automation_id"].casefold().startswith("tov_")
                    or control["title"].casefold() in _TOV_SAFE_STATIC_LABELS | _TOV_SAFE_ACTION_TITLES
                    or control["title"].casefold() in _TOV_SAFE_CHECKBOX_TITLES
                    for control in controls
                )
                if has_tov_markers:
                    match_reason = "tov_controls"

                rows.append({
                    "window_title": safe_window_title,
                    "process_id": process_id,
                    "match_reason": match_reason,
                    "has_tov_markers": has_tov_markers,
                    "window_control_type": str(getattr(window.element_info, "control_type", "") or ""),
                    "controls": controls[:500],
                })
            except Exception:
                continue
        if not rows:
            raise RuntimeError(
                "UI Automation found no visible windows for Camfrog processes. "
                "Keep Camfrog Settings → Video & Audio → Text Over Video open and inspect again"
            )

        # Prefer a Settings title or controls that identify the TOV page. If
        # neither is surfaced by UIA, return the Camfrog main window metadata
        # as a useful diagnostic instead of failing on an exact title check.
        candidates = [row for row in rows if row["match_reason"] == "settings_title" or row["has_tov_markers"]]
        if candidates:
            return candidates
        main_windows = [row for row in rows if row["match_reason"] == "camfrog_window"]
        return main_windows or rows

    def _find_target(self, win):
        target = self.config.get("target", {})
        automation_id = target.get("automation_id", "").strip()
        control_type = target.get("control_type", "ComboBox").strip() or "ComboBox"
        title_re = target.get("title_regex", ".*") or ".*"

        candidates = []
        # First use configured UIA control type.
        try:
            pool = list(win.descendants(control_type=control_type))
        except Exception:
            pool = []
        # Camfrog's known status control is a custom native CComboBoxTS and may
        # be exposed with a surprising UIA control type. Search all descendants
        # as a second pass and score the native class directly.
        try:
            pool += [c for c in win.descendants() if str(getattr(c.element_info, "class_name", "")).lower() == "ccomboboxts"]
        except Exception:
            pass

        seen = set()
        unverified_controls = 0
        known_statuses = {str(x).strip().casefold() for x in self.config.get("status", {}).get("presets", []) if str(x).strip()}
        for ctrl in pool:
            try:
                handle = int(getattr(ctrl, "handle", 0) or 0)
                marker = handle or id(ctrl)
                if marker in seen:
                    continue
                seen.add(marker)
                info = ctrl.element_info
                title = ctrl.window_text() or ""
                if automation_id and info.automation_id != automation_id:
                    continue
                if title_re and not re.match(title_re, title):
                    continue
                score = 0
                cls = str(info.class_name or "").lower()
                is_native_status = cls == "ccomboboxts"
                matches_known_status = title.strip().casefold() in known_statuses
                matches_configured_id = bool(automation_id and info.automation_id == automation_id)
                # A generic ComboBox match alone is not enough evidence: writing
                # it and sending Enter could alter an unrelated Camfrog field.
                if not (is_native_status or matches_known_status or matches_configured_id):
                    unverified_controls += 1
                    continue
                if matches_configured_id:
                    score += 2000
                if is_native_status:
                    score += 1000
                if matches_known_status:
                    score += 500
                if info.control_type == control_type:
                    score += 100
                candidates.append((score, ctrl))
            except Exception:
                continue
        if not candidates:
            if unverified_controls:
                raise UnverifiedStatusControlError(
                    "UIA found a generic ComboBox but no verified Camfrog status control; configure its exact automation ID"
                )
            raise RuntimeError("No positively identified Camfrog status control was found")
        candidates.sort(key=lambda item: item[0], reverse=True)
        best_score = candidates[0][0]
        if sum(score == best_score for score, _control in candidates) > 1:
            raise AmbiguousStatusControlError("Multiple Camfrog status controls matched equally; refusing to guess")
        return candidates[0][1]

    @staticmethod
    def _read_value(ctrl) -> str:
        for getter in (
            lambda: ctrl.get_value(),
            lambda: ctrl.window_text(),
        ):
            try:
                value = getter()
                if value is not None:
                    return str(value)
            except Exception:
                pass
        return ""

    @staticmethod
    def _find_status_editor(ctrl):
        """Find one unambiguous editor belonging to the selected status combo."""
        try:
            descendants = list(ctrl.descendants())
        except Exception as exc:
            raise RuntimeError(f"Could not inspect status editor children: {exc}") from exc

        native_editors = []
        edit_controls = []
        for child in descendants:
            try:
                info = child.element_info
                class_name = str(info.class_name or "").casefold()
                if class_name == "cedit4comboinnerts":
                    native_editors.append(child)
                if str(info.control_type or "") == "Edit":
                    edit_controls.append(child)
            except Exception:
                continue

        if len(native_editors) == 1:
            return native_editors[0]
        if len(native_editors) > 1:
            raise AmbiguousStatusControlError("Camfrog exposed multiple CEdit4ComboInnerTS status editors")
        if len(edit_controls) == 1:
            return edit_controls[0]
        if not edit_controls:
            raise RuntimeError("Camfrog did not expose a status Edit control")
        raise AmbiguousStatusControlError("Camfrog exposed multiple status Edit controls without a unique native editor")

    def stage_status_text(self, value: str) -> ChangeResult:
        """Write and verify a status draft in the foreground without pressing Enter."""
        value = value.replace("\x00", "")
        if not value.strip():
            return ChangeResult(False, "Status cannot be empty")
        max_len = int(self.config.get("advanced", {}).get("max_status_length", 160))
        if len(value) > max_len:
            return ChangeResult(False, f"Status exceeds configured maximum length ({max_len})")
        if not self._apply_lock.acquire(blocking=False):
            return ChangeResult(False, "Another status change is already in progress")

        clipboard_text = None
        clipboard_captured = False
        editor = None
        previous = ""
        try:
            import pyperclip
            from pywinauto.keyboard import send_keys

            if not self.client_processes():
                running = self.ensure_running()
                return ChangeResult(False, f"{running.message}; no status draft was written")

            win = self.find_window()
            combo = self._find_target(win)
            editor = self._find_status_editor(combo)
            previous = self._read_value(editor)
            clipboard_text = pyperclip.paste()
            clipboard_captured = True

            # The draft action explicitly restores Camfrog because minimized
            # custom controls do not consistently accept UIA/Win32 text writes.
            win.restore()
            win.set_focus()
            editor.set_focus()
            time.sleep(0.15)
            pyperclip.copy(value)
            send_keys("^a{BACKSPACE}")
            send_keys("^v")
            time.sleep(STATUS_INPUT_SETTLE_SECONDS)

            observed = self._read_value(editor)
            if comparable_status(observed) != comparable_status(value):
                restored = False
                try:
                    if previous:
                        pyperclip.copy(previous)
                        send_keys("^a{BACKSPACE}")
                        send_keys("^v")
                    else:
                        send_keys("^a{BACKSPACE}")
                    time.sleep(0.15)
                    restored = comparable_status(self._read_value(editor)) == comparable_status(previous)
                except Exception:
                    restored = False
                detail = "Previous draft restored" if restored else "Previous draft restoration could not be verified"
                return ChangeResult(
                    False,
                    f"Status draft did not verify; Enter was not sent. {detail}.",
                    previous,
                    value,
                )

            return ChangeResult(
                True,
                "Status text staged and verified in Camfrog; Enter was not sent",
                previous,
                value,
            )
        except Exception as exc:
            log.exception("Camfrog status draft staging failed")
            return ChangeResult(False, f"Status draft staging failed; Enter was not sent: {exc}", previous, value)
        finally:
            if clipboard_captured:
                try:
                    import pyperclip
                    pyperclip.copy(clipboard_text or "")
                except Exception:
                    log.warning("Could not restore the clipboard after status draft staging")
            self._apply_lock.release()

    def _coordinate_fallback(self, win, value: str) -> None:
        if not per_monitor_v2_ready():
            raise RuntimeError(
                "Coordinate fallback is disabled until per-monitor v2 DPI awareness is confirmed"
            )

        target = self.config.get("target", {})
        rx = float(target.get("fallback_relative_x", 0.50))
        ry = float(target.get("fallback_relative_y", 0.19))
        if not (0.0 <= rx <= 1.0 and 0.0 <= ry <= 1.0):
            raise RuntimeError("Fallback relative coordinates must be between 0.0 and 1.0")

        # Do not use a coordinate click as permission to edit an unknown field.
        ctrl = self._find_target(win)
        editor = self._find_status_editor(ctrl)

        try:
            win.restore()
        except Exception:
            pass
        try:
            win.set_focus()
        except Exception:
            pass
        time.sleep(0.25)

        rect = win.rectangle()
        x = int(rect.left + rect.width() * rx)
        y = int(rect.top + rect.height() * ry)

        from pywinauto import mouse
        from pywinauto.keyboard import send_keys
        import pyperclip

        old_clipboard = None
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            pass

        try:
            mouse.click(button="left", coords=(x, y))
            time.sleep(0.15)
            send_keys("^a{BACKSPACE}")
            pyperclip.copy(value)
            send_keys("^v")
            ready, observed, reason = self._wait_for_foreground_status(win, editor, value)
            if not ready:
                raise RuntimeError(
                    f"Coordinate fallback could not verify Camfrog foreground and status text; Enter was not sent: {reason}"
                )
            ready, observed, reason = self._foreground_status_snapshot(win, editor, value)
            if not ready:
                raise RuntimeError(
                    f"Coordinate fallback target changed before commit; Enter was not sent: {reason}"
                )
            send_keys("{ENTER}")
        finally:
            if old_clipboard is not None:
                try:
                    pyperclip.copy(old_clipboard)
                except Exception:
                    log.warning("Could not restore the clipboard after coordinate fallback")

    def set_status(self, value: str, *, cancelled=None) -> ChangeResult:
        value = value.replace("\x00", "")
        # Preserve intentional CRLF between line 1/2; only reject all-whitespace payloads.
        if not value.strip():
            return ChangeResult(False, "Status cannot be empty")
        max_len = int(self.config.get("advanced", {}).get("max_status_length", 160))
        if len(value) > max_len:
            return ChangeResult(False, f"Status exceeds configured maximum length ({max_len})")

        # Apply and rotation requests are serialized instead of discarding the
        # later request when both reach the sender in the same interval.
        if not self._acquire_apply_lock(cancelled):
            return ChangeResult(False, "Status change cancelled before sending", new_value=value)
        try:
            if self._is_cancelled(cancelled):
                return ChangeResult(False, "Status change cancelled before sending", new_value=value)
            running = self.ensure_running()
            if not running.ok:
                return running
            if self._is_cancelled(cancelled):
                return ChangeResult(False, "Status change cancelled before sending", new_value=value)
            if cancelled is None:
                self._wait_for_send_slot()
            elif not self._wait_for_send_slot(cancelled=cancelled):
                return ChangeResult(False, "Status change cancelled before sending", new_value=value)
            if self._is_cancelled(cancelled):
                return ChangeResult(False, "Status change cancelled before sending", new_value=value)

            try:
                win = self.find_window()
                previous = ""
                errors: list[str] = []
                profile_info = self.native_profile_info()
                verified_editor = None
                if profile_info.get("matched"):
                    log.info("Known Camfrog native profile matched: %s", profile_info.get("name"))
                elif profile_info.get("sha256"):
                    log.warning("Unknown Camfrog binary SHA-256: %s; using generic UI/Win32 integration only", profile_info.get("sha256"))

                try:
                    ctrl = self._find_target(win)
                    previous = self._read_value(ctrl)
                    # Use exactly one verified status editor. The payload is
                    # clipboard-pasted once; ValuePattern/direct text writers
                    # are deliberately not mixed with an editable child.
                    edit = None
                    try:
                        edit = self._find_status_editor(ctrl)
                    except AmbiguousStatusControlError:
                        raise
                    except RuntimeError as exc:
                        # Some builds expose only ValuePattern on the combo.
                        # Keep that compatibility route when no single Edit exists.
                        errors.append(f"UIA child Edit discovery: {exc}")
                    except Exception as exc:
                        errors.append(f"UIA child Edit discovery: {exc}")

                    clipboard_text = None
                    clipboard_captured = False
                    if edit is None:
                        # A combo may identify which Camfrog control is the
                        # status selector, but it is not safe to send keyboard
                        # input to it when UIA cannot uniquely identify its
                        # editable child. Let the guarded background path try.
                        errors.append("UIA commit skipped because no unique status Edit control was identified")
                    else:
                        try:
                            import pyperclip
                            from pywinauto.keyboard import send_keys

                            clipboard_text = pyperclip.paste()
                            clipboard_captured = True
                            # Camfrog's custom status editor has rejected direct
                            # UIA text writes on some builds. Paste the complete
                            # Unicode string into the unique verified editor,
                            # then read it back before allowing one Enter commit.
                            win.restore()
                            win.set_focus()
                            edit.set_focus()
                            time.sleep(0.15)
                            pyperclip.copy(value)
                            send_keys("^a{BACKSPACE}")
                            send_keys("^v")
                            time.sleep(0.10)
                            observed = self._read_value(edit).strip()
                            if comparable_status(observed) == comparable_status(value):
                                verified_editor = edit
                                log.info("UIA clipboard-pasted status text verified")
                            else:
                                errors.append(f"UIA clipboard paste verification read {observed!r}")
                        except Exception as exc:
                            errors.append(f"UIA clipboard paste failed: {exc}")
                        finally:
                            if clipboard_captured:
                                try:
                                    pyperclip.copy(clipboard_text or "")
                                except Exception:
                                    log.warning("Could not restore the clipboard after status paste")

                    if verified_editor is not None:
                        try:
                            # Poll for the intended process and retain the exact
                            # editor text; immediately recheck both before Enter.
                            verified_editor.set_focus()
                            ready, observed, reason = self._wait_for_foreground_status(
                                win, verified_editor, value
                            )
                            if not ready:
                                return ChangeResult(
                                    False,
                                    f"Status commit aborted; Enter was not sent: {reason}",
                                    previous,
                                    value,
                                )
                            ready, observed, reason = self._foreground_status_snapshot(
                                win, verified_editor, value
                            )
                            if not ready:
                                return ChangeResult(
                                    False,
                                    f"Status commit aborted; Enter was not sent: {reason}",
                                    previous,
                                    value,
                                )
                            if self._is_cancelled(cancelled):
                                return ChangeResult(False, "Status change cancelled before sending", previous, value)
                            self._record_send_time()
                            verified_editor.type_keys("{ENTER}")
                            time.sleep(STATUS_COMMIT_SETTLE_SECONDS)
                            return ChangeResult(
                                True,
                                "Status text verified; one foreground Enter sent (server acceptance is not independently confirmed)",
                                previous,
                                value,
                            )
                        except Exception as exc:
                            return ChangeResult(False, f"Verified status text was not committed; foreground Enter failed: {exc}", previous, value)

                    # UIA could not verify a value. The Win32 path now owns the
                    # single fallback write and commit attempt.
                except AmbiguousStatusControlError as exc:
                    return ChangeResult(False, f"Status change failed: {exc}", previous, value)
                except UnverifiedStatusControlError as exc:
                    return ChangeResult(False, f"Status change failed: {exc}", previous, value)
                except Exception as exc:
                    errors.append(f"UIA target: {exc}")

                if self.config.get("target", {}).get("background_enabled", True):
                    try:
                        if self._is_cancelled(cancelled):
                            return ChangeResult(False, "Status change cancelled before sending", previous, value)
                        hwnd = int(win.handle)
                        target = self.config.get("target", {})
                        result = set_status_background(
                            hwnd,
                            float(target.get("fallback_relative_x", 0.50)),
                            float(target.get("fallback_relative_y", 0.19)),
                            value,
                            current_text=previous,
                            known_statuses=self.config.get("status", {}).get("presets", []),
                            allow_coordinate_fallback=per_monitor_v2_ready(),
                        )
                        if result.ok and result.verified:
                            self._record_send_time()
                            return ChangeResult(True, result.message, previous, value)
                        if getattr(result, "ambiguous", False):
                            return ChangeResult(False, f"Status change failed: {result.message}", previous, value)
                        errors.append(result.message)
                    except Exception as exc:
                        errors.append(f"Win32 background: {exc}")

                advanced = self.config.get("advanced", {})
                if advanced.get("fallback_enabled", False):
                    try:
                        if self._is_cancelled(cancelled):
                            return ChangeResult(False, "Status change cancelled before sending", previous, value)
                        self._coordinate_fallback(win, value)
                        self._record_send_time()
                        return ChangeResult(True, "Status changed using foreground fallback (not background-verified)", previous, value)
                    except Exception as exc:
                        errors.append(f"Foreground fallback: {exc}")

                detail = "; ".join(errors[-5:]) or "No compatible background strategy succeeded"
                profile_note = "known native profile" if profile_info.get("matched") else "generic profile"
                return ChangeResult(False, f"Status change failed ({profile_note}). {detail}", previous_value=previous)
            except Exception as exc:
                log.exception("Status change failed")
                return ChangeResult(False, str(exc))
        finally:
            self._apply_lock.release()
