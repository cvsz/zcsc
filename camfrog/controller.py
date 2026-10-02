from __future__ import annotations

import logging
import os
import re
import subprocess
import time
import threading
from dataclasses import dataclass

from .detector import find_processes
from .background_win32 import (
    STATUS_INPUT_SETTLE_SECONDS,
    STATUS_COMMIT_SETTLE_SECONDS,
    set_status_background,
)
from .native_profile import identify_profile
from status_text import comparable_status

log = logging.getLogger(__name__)

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


class CamfrogController:
    def __init__(self, config: dict):
        self.config = config
        self._apply_lock = threading.Lock()
        self._last_send_monotonic = 0.0

    def client_processes(self):
        executable = str(self.config.get("camfrog", {}).get("executable", "")).strip()
        return find_processes(executable_path=executable or None)

    def _wait_for_send_slot(self) -> None:
        """Enforce spacing between Camfrog send attempts instead of dropping early ones."""
        minimum = max(1, int(self.config.get("advanced", {}).get("minimum_interval_seconds", 5)))
        while self._last_send_monotonic:
            remaining = minimum - (time.monotonic() - self._last_send_monotonic)
            if remaining <= 0:
                break
            log.info("Waiting %.2fs before the next Camfrog status send", remaining)
            time.sleep(remaining)
        self._last_send_monotonic = time.monotonic()

    def ensure_running(self) -> ChangeResult:
        if self.client_processes():
            return ChangeResult(True, "Camfrog is running")
        exe = self.config["camfrog"].get("executable", "").strip()
        if not exe:
            return ChangeResult(False, "Camfrog executable is not configured")
        try:
            subprocess.Popen([exe], shell=False)
        except Exception as exc:
            return ChangeResult(False, f"Failed to start Camfrog: {exc}")
        for _ in range(30):
            if self.client_processes():
                return ChangeResult(True, "Camfrog started")
            time.sleep(0.5)
        return ChangeResult(False, "Camfrog did not start within timeout")

    def _desktop(self):
        if os.name != "nt":
            raise RuntimeError("Windows UI Automation is only available on Windows")
        from pywinauto import Desktop
        return Desktop(backend="uia")

    def _find_window_by_pid(self):
        """Locate Camfrog's main top-level HWND from its process id(s).

        This avoids depending on the localized/window title, which can change
        between Camfrog releases.  The returned HWND is wrapped with the UIA
        backend so the rest of the controller can keep using pywinauto.
        """
        if os.name != "nt":
            return None

        import win32gui

        processes = self.client_processes()
        pids = {int(p.pid) for p in processes}
        if not pids:
            return None

        candidates = []

        def enum_cb(hwnd, _):
            try:
                if not win32gui.IsWindow(hwnd):
                    return True
                _tid, pid = win32gui.GetWindowThreadProcessId(hwnd)
                if int(pid) not in pids:
                    return True

                title = win32gui.GetWindowText(hwnd) or ""
                cls = win32gui.GetClassName(hwnd) or ""
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                width = max(0, right - left)
                height = max(0, bottom - top)
                area = width * height

                score = 0
                if "camfrog" in title.lower():
                    score += 300
                if "video chat" in title.lower():
                    score += 150
                if win32gui.IsWindowVisible(hwnd):
                    score += 80
                if area >= 200 * 300:
                    score += 60
                if width >= 250 and height >= 400:
                    score += 40
                if title:
                    score += 20

                candidates.append((score, area, hwnd, title, cls, int(pid)))
            except Exception:
                pass
            return True

        win32gui.EnumWindows(enum_cb, None)
        if not candidates:
            return None

        process_ids = {item[5] for item in candidates}
        if len(process_ids) > 1:
            raise CamfrogInstanceAmbiguityError(
                "Multiple Camfrog client windows are open. Close all but the client to automate, then retry."
            )

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        best_rank = candidates[0][:2]
        best_candidates = [item for item in candidates if item[:2] == best_rank]
        if len(best_candidates) != 1:
            raise CamfrogInstanceAmbiguityError(
                "Multiple Camfrog windows have the same main-window score; refusing to guess"
            )
        hwnd = int(best_candidates[0][2])
        log.info(
            "Camfrog window selected by PID: hwnd=%s title=%r class=%r score=%s",
            hwnd, best_candidates[0][3], best_candidates[0][4], best_candidates[0][0],
        )
        return self._desktop().window(handle=hwnd)

    def find_window(self):
        # Prefer PID-based discovery. It survives title/localization changes and
        # also finds minimized windows because EnumWindows does not require them
        # to be foreground/visible.
        try:
            win = self._find_window_by_pid()
            if win is not None:
                return win
        except CamfrogInstanceAmbiguityError:
            raise
        except Exception as exc:
            log.warning("PID-based Camfrog window discovery failed: %s", exc)

        # Compatibility fallback for older installations.
        title_re = self.config["camfrog"].get("window_title_regex") or ".*Camfrog Video Chat.*"
        desktop = self._desktop()
        wins = desktop.windows(title_re=title_re, visible_only=False)
        if not wins:
            raise RuntimeError(
                "Camfrog process is running, but its main window was not found. "
                "Use Detect after Camfrog has finished opening, or restart Camfrog and retry."
            )
        if len(wins) != 1:
            raise CamfrogInstanceAmbiguityError(
                "Multiple Camfrog windows match the configured title. Narrow the title filter or close extra matching windows."
            )
        return wins[0]

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
        target_pids = {int(process.pid) for process in self.client_processes()}
        if not target_pids:
            raise RuntimeError("No Camfrog process was found. Start Camfrog, open Text Over Video, and inspect again")

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
                if cls == "ccomboboxts":
                    score += 1000
                if title.strip().casefold() in known_statuses:
                    score += 500
                if info.control_type == control_type:
                    score += 100
                candidates.append((score, ctrl))
            except Exception:
                continue
        if not candidates:
            raise RuntimeError("Configured status control was not found")
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
                return ChangeResult(False, "Camfrog is not running; no status draft was written")

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
        target = self.config.get("target", {})
        rx = float(target.get("fallback_relative_x", 0.50))
        ry = float(target.get("fallback_relative_y", 0.19))
        if not (0.0 <= rx <= 1.0 and 0.0 <= ry <= 1.0):
            raise RuntimeError("Fallback relative coordinates must be between 0.0 and 1.0")

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

        mouse.click(button="left", coords=(x, y))
        time.sleep(0.15)
        send_keys("^a{BACKSPACE}")
        pyperclip.copy(value)
        send_keys("^v")
        time.sleep(STATUS_INPUT_SETTLE_SECONDS)
        send_keys("{ENTER}")

        if old_clipboard is not None:
            try:
                time.sleep(0.1)
                pyperclip.copy(old_clipboard)
            except Exception:
                pass

    def set_status(self, value: str) -> ChangeResult:
        value = value.replace("\x00", "")
        # Preserve intentional CRLF between line 1/2; only reject all-whitespace payloads.
        if not value.strip():
            return ChangeResult(False, "Status cannot be empty")
        max_len = int(self.config.get("advanced", {}).get("max_status_length", 160))
        if len(value) > max_len:
            return ChangeResult(False, f"Status exceeds configured maximum length ({max_len})")

        if not self._apply_lock.acquire(blocking=False):
            return ChangeResult(False, "Another status change is already in progress")
        try:
            running = self.ensure_running()
            if not running.ok:
                return running
            self._wait_for_send_slot()

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
                    # Use exactly one UIA writer. On Camfrog's custom combo,
                    # ValuePattern and the child Edit can both target the same
                    # native text box, so invoking both may duplicate input.
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

                    setter = getattr(edit, "set_edit_text", None) if edit is not None else None
                    if callable(setter):
                        try:
                            setter(value)
                            time.sleep(0.10)
                            observed = self._read_value(edit).strip()
                            if comparable_status(observed) == comparable_status(value):
                                verified_editor = edit
                                log.info("UIA child Edit text verified; committing without a second text write")
                            else:
                                errors.append(f"UIA child Edit verification read {observed!r}")
                        except Exception as exc:
                            errors.append(f"UIA child Edit set failed: {exc}")
                    elif edit is None:
                        # Non-editable controls may expose ValuePattern. Do not
                        # combine it with a child Edit write on the same control.
                        try:
                            iface_value = getattr(ctrl, "iface_value", None)
                            if iface_value is not None:
                                iface_value.SetValue(value)
                                time.sleep(0.10)
                                observed = self._read_value(ctrl).strip()
                                if comparable_status(observed) == comparable_status(value):
                                    verified_editor = ctrl
                                    log.info("UIA ValuePattern text verified; committing without a second text write")
                                else:
                                    errors.append(f"UIA ValuePattern verification read {observed!r}")
                        except Exception as exc:
                            errors.append(f"UIA ValuePattern: {exc}")

                    if verified_editor is not None:
                        try:
                            # Camfrog's custom combo does not reliably treat a
                            # background WM_KEYDOWN as a keyboard commit. The
                            # UIA text write is already verified, so focus that
                            # same editor and send exactly one real Enter.
                            win.restore()
                            win.set_focus()
                            verified_editor.set_focus()
                            time.sleep(STATUS_INPUT_SETTLE_SECONDS)
                            verified_editor.type_keys("{ENTER}")
                            time.sleep(STATUS_COMMIT_SETTLE_SECONDS)
                            return ChangeResult(
                                True,
                                "Status text verified; one foreground Enter sent (server acceptance is not independently confirmed)",
                                previous,
                                value,
                            )
                        except Exception as exc:
                            return ChangeResult(False, f"Verified status text was not retyped; foreground Enter failed: {exc}", previous, value)

                    # UIA could not verify a value. The Win32 path now owns the
                    # single fallback write and commit attempt.
                except AmbiguousStatusControlError as exc:
                    return ChangeResult(False, f"Status change failed: {exc}", previous, value)
                except Exception as exc:
                    errors.append(f"UIA target: {exc}")

                if self.config.get("target", {}).get("background_enabled", True):
                    try:
                        hwnd = int(win.handle)
                        target = self.config.get("target", {})
                        result = set_status_background(
                            hwnd,
                            float(target.get("fallback_relative_x", 0.50)),
                            float(target.get("fallback_relative_y", 0.19)),
                            value,
                            current_text=previous,
                            known_statuses=self.config.get("status", {}).get("presets", []),
                        )
                        if result.ok and result.verified:
                            return ChangeResult(True, result.message, previous, value)
                        if getattr(result, "ambiguous", False):
                            return ChangeResult(False, f"Status change failed: {result.message}", previous, value)
                        errors.append(result.message)
                    except Exception as exc:
                        errors.append(f"Win32 background: {exc}")

                advanced = self.config.get("advanced", {})
                if advanced.get("fallback_enabled", False):
                    try:
                        self._coordinate_fallback(win, value)
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
