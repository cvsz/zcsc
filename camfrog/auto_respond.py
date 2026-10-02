from __future__ import annotations

import logging
import os
import re
import threading
import time
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)

_KINDS = ("private", "room")
_MESSAGE_LINE = re.compile(
    r"^\s*(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s+)?"
    r"(?P<sender>[^:\r\n]{1,64}):\s*(?P<body>.+?)\s*$"
)


def normalize_reply_text(value: Any, max_length: int = 500) -> str:
    """Normalize a reply while preserving intentional line breaks."""
    text = str(value or "").replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.split()) for line in text.split("\n")]
    return "\n".join(lines).strip()[:max(1, int(max_length))]


def _read_control_value(control, allow_window_text: bool = True) -> tuple[bool, str]:
    names = ("get_value", "window_text") if allow_window_text else ("get_value",)
    for name in names:
        getter = getattr(control, name, None)
        if not callable(getter):
            continue
        try:
            value = getter()
            if value is not None:
                return True, str(value)
        except Exception:
            continue
    return False, ""


def _control_value(control) -> str:
    _readable, value = _read_control_value(control)
    return value


def _history_lines(control) -> tuple[str, ...]:
    """Read only visible UIA text from the configured message-history control."""
    try:
        is_visible = getattr(control, "is_visible", None)
        if callable(is_visible) and not is_visible():
            return ()
    except Exception:
        return ()
    try:
        descendants = list(control.descendants())
    except Exception:
        descendants = []
    leaves: list[str] = []
    for child in descendants:
        try:
            if str(child.element_info.control_type) not in {"Text", "ListItem"}:
                continue
            is_visible = getattr(child, "is_visible", None)
            if callable(is_visible) and not is_visible():
                continue
        except Exception:
            continue
        value = _control_value(child)
        if value.strip():
            leaves.extend(line.strip() for line in value.splitlines() if line.strip())
    if not leaves:
        value = _control_value(control)
        leaves = [line.strip() for line in value.splitlines() if line.strip()]

    # UIA providers can return the same accessible line from a parent and child.
    # Preserve order but collapse adjacent duplicates and cap memory use.
    clean: list[str] = []
    for line in leaves:
        if not clean or clean[-1] != line:
            clean.append(line[:1024])
    return tuple(clean[-300:])


def _new_lines(previous: tuple[str, ...], current: tuple[str, ...]) -> tuple[str, ...]:
    if not current:
        return ()
    if not previous:
        return current
    if len(current) >= len(previous) and current[: len(previous)] == previous:
        candidates = current[len(previous) :]
    else:
        overlap = min(len(previous), len(current))
        while overlap and previous[-overlap:] != current[:overlap]:
            overlap -= 1
        if not overlap:
            return ()
        candidates = current[overlap:]
    old_lines = set(previous)
    # Ambiguous repeated text is intentionally ignored. This may miss an exact
    # duplicate message, but cannot turn a refresh/reorder into an auto-reply.
    return tuple(line for line in candidates if line not in old_lines)


def _parse_message(line: str) -> tuple[str, str] | None:
    match = _MESSAGE_LINE.match(line)
    if not match:
        return None
    sender = match.group("sender").strip()
    body = match.group("body").strip()
    if not sender or not body:
        return None
    return sender, body


def _find_history_control(window, automation_id: str):
    """Resolve a unique history control, disambiguating duplicate IDs by message shape."""
    try:
        matches = [
            control for control in window.descendants()
            if str(getattr(control.element_info, "automation_id", "") or "") == automation_id
        ]
    except Exception:
        return None
    if len(matches) == 1:
        return matches[0]
    candidates = [
        control for control in matches
        if any(_parse_message(line) is not None for line in _history_lines(control))
    ]
    return candidates[0] if len(candidates) == 1 else None


class CamfrogAutoResponder:
    """Reply to newly visible incoming messages through explicit UIA controls.

    No message text is written to logs or disk. Chat control IDs and title
    fragments must be configured per conversation type; missing or ambiguous
    selectors fail closed.
    """

    def __init__(self, controller):
        self.controller = controller
        self._snapshots: dict[tuple[str, int, str], tuple[str, ...]] = {}
        self._last_reply: dict[tuple[str, int, str], float] = {}

    @staticmethod
    def _complete(selectors: dict[str, Any]) -> bool:
        return all(
            str(selectors.get(key, "")).strip()
            for key in (
                "window_title_contains",
                "history_automation_id",
                "input_automation_id",
                "send_automation_id",
            )
        )

    @staticmethod
    def _kind_for_title(title: str, config: dict[str, Any]) -> str | None:
        auto = config.get("auto_respond", {})
        matches = []
        for kind in _KINDS:
            if not bool(auto.get(f"{kind}_enabled", True)):
                continue
            selectors = auto.get(kind, {})
            if not isinstance(selectors, dict) or not CamfrogAutoResponder._complete(selectors):
                continue
            fragment = str(selectors.get("window_title_contains", "")).strip().casefold()
            if fragment and fragment in title.casefold():
                matches.append(kind)
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _find_exact_id(window, automation_id: str):
        try:
            matches = [
                control for control in window.descendants()
                if str(getattr(control.element_info, "automation_id", "") or "") == automation_id
            ]
        except Exception:
            return None
        return matches[0] if len(matches) == 1 else None

    def _send_reply(self, window, selectors: dict[str, Any], reply: str, cancelled: Callable[[], bool] | None = None) -> bool:
        if cancelled is not None and cancelled():
            return False
        compose = self._find_exact_id(window, str(selectors["input_automation_id"]))
        send = self._find_exact_id(window, str(selectors["send_automation_id"]))
        if compose is None or send is None:
            return False
        try:
            invoke_pattern = getattr(send, "iface_invoke", None)
            invoke = getattr(invoke_pattern, "Invoke", None)
        except Exception:
            return False
        if not callable(invoke):
            return False

        # Never overwrite a user's draft. A value that cannot be read is also
        # treated as unsafe, rather than assuming the field is empty.
        readable, current_value = _read_control_value(compose, allow_window_text=False)
        if not readable or current_value.strip():
            return False
        setter = getattr(compose, "set_edit_text", None)
        if not callable(setter):
            return False
        try:
            setter(reply)
            readable, current_value = _read_control_value(compose, allow_window_text=False)
            if not readable or current_value.strip() != reply:
                return False
            if cancelled is not None and cancelled():
                return False
            # Only invoke an explicit UIA InvokePattern. Do not click/focus a
            # control or send Enter into whichever window currently has focus.
            invoke()
            return True
        except Exception:
            log.exception("Auto reply UIA submission failed")
            return False

    def poll_once(self, config: dict[str, Any], cancelled: Callable[[], bool] | None = None) -> str:
        auto = config.get("auto_respond", {})
        if not bool(auto.get("enabled", False)):
            return "Auto respond is disabled"
        if os.name != "nt":
            return "Auto respond requires Windows UI Automation"
        username = str(auto.get("own_username", "")).strip()
        reply = normalize_reply_text(auto.get("reply_text", ""))
        if not username or not reply:
            return "Auto respond needs your Camfrog nickname and a reply text"

        configured_kinds = [
            kind for kind in _KINDS
            if bool(auto.get(f"{kind}_enabled", True))
            and isinstance(auto.get(kind), dict)
            and self._complete(auto[kind])
        ]
        if not configured_kinds:
            return "Auto respond needs UIA selectors for private chat and/or room chat"

        if not self.controller.client_processes():
            return "Auto respond is waiting for Camfrog"
        try:
            main_window = self.controller.find_window()
            target_pid = int(main_window.process_id())
            windows = self.controller._desktop().windows(visible_only=True)
        except Exception:
            log.exception("Auto respond could not inspect visible Camfrog windows")
            return "Auto respond is waiting for a visible Camfrog window"

        cooldown = max(10, int(auto.get("cooldown_seconds", 60)))
        now = time.monotonic()
        matched_window = False
        for window in windows:
            try:
                if cancelled is not None and cancelled():
                    return "Auto respond is disabled"
                if int(window.process_id()) != target_pid:
                    continue
                title = str(window.window_text() or "").strip()
                kind = self._kind_for_title(title, config)
                if kind is None:
                    continue
                selectors = auto[kind]
                history = _find_history_control(window, str(selectors["history_automation_id"]))
                if history is None:
                    continue
                matched_window = True
                lines = _history_lines(history)
                key = (kind, int(window.handle), title)
                previous = self._snapshots.get(key)
                self._snapshots[key] = lines
                if previous is None:
                    # Establish a baseline. Never reply to messages that were
                    # already present when monitoring began or was re-enabled.
                    continue
                added = _new_lines(previous, lines)
                if not added:
                    continue
                parsed = [message for line in added if (message := _parse_message(line)) is not None]
                if not parsed:
                    continue
                sender, body = parsed[-1]
                if sender.casefold() == username.casefold() or body.casefold() == reply.casefold():
                    continue
                throttle_key = (kind, int(window.handle), sender.casefold())
                if now - self._last_reply.get(throttle_key, 0.0) < cooldown:
                    continue
                if self._send_reply(window, selectors, reply, cancelled=cancelled):
                    self._last_reply[throttle_key] = now
                    log.info("Auto reply submitted through visible UIA controls (%s chat)", kind)
                    return f"Auto reply submitted ({kind} chat)"
            except Exception:
                log.debug("Skipping a Camfrog window after a UIA error")
        if matched_window:
            return "Auto respond is monitoring configured chat controls"
        return "Auto respond is waiting for a configured private or room chat window"


class AutoRespondWorker:
    def __init__(self, controller, get_config: Callable[[], dict[str, Any]], on_state: Callable[[str], None] | None = None):
        self.controller = controller
        self.get_config = get_config
        self.on_state = on_state
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._generation = 0

    def start(self) -> None:
        self.stop()
        self._stop.clear()
        self._generation += 1
        generation = self._generation
        responder = CamfrogAutoResponder(self.controller)

        def run() -> None:
            previous_state = ""
            while generation == self._generation and not self._stop.is_set():
                try:
                    config = self.get_config()
                    state = responder.poll_once(
                        config,
                        cancelled=lambda: generation != self._generation or self._stop.is_set(),
                    )
                    if state != previous_state and self.on_state is not None:
                        self.on_state(state)
                    previous_state = state
                    interval = max(1, int(config.get("auto_respond", {}).get("poll_interval_seconds", 2)))
                except Exception:
                    log.exception("Auto respond polling failed")
                    interval = 2
                self._stop.wait(interval)

        self._thread = threading.Thread(target=run, daemon=True, name="camfrog-auto-respond")
        self._thread.start()

    def stop(self) -> None:
        self._generation += 1
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._thread = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())
