from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .auto_respond import _find_history_control, _history_lines, _new_lines
from .room_actions import room_title_matches

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RoomEventMatch:
    room_title: str
    trigger_phrase: str


class CamfrogRoomEventMonitor:
    """Notify on configured phrases in newly visible room-history lines."""

    def __init__(self, controller):
        self.controller = controller
        self._snapshots: dict[tuple[int, str], tuple[str, ...]] = {}
        self._last_alert: dict[tuple[int, str, str], float] = {}

    def poll_once(self, config: dict[str, Any]) -> tuple[tuple[RoomEventMatch, ...], str]:
        settings = config.get("room_event_notifications", {})
        if not isinstance(settings, dict) or settings.get("enabled") is not True:
            return (), "Room event notifications are disabled"
        if os.name != "nt":
            return (), "Room event notifications require Windows UI Automation"
        terms = tuple(
            " ".join(str(term).replace("\x00", "").split())
            for term in settings.get("phrases", [])
            if len(" ".join(str(term).replace("\x00", "").split())) >= 2
        ) if isinstance(settings.get("phrases", []), list) else ()
        if not terms:
            return (), "Add room event phrases to monitor"

        selectors = config.get("auto_respond", {}).get("room", {})
        if not isinstance(selectors, dict):
            return (), "Configure room chat UIA selectors first"
        configured_room_title = str(config.get("room_actions", {}).get("room_title", "")).strip()
        if not configured_room_title:
            return (), "Configure the exact room title before room event monitoring"
        title_fragment = str(selectors.get("window_title_contains", "")).strip()
        history_id = str(selectors.get("history_automation_id", "")).strip()
        if not title_fragment or not history_id:
            return (), "Configure the room title and history UIA ID first"
        if not self.controller.client_processes():
            return (), "Camfrog is not running"

        try:
            main_window = self.controller.find_window()
            target_pid = int(main_window.process_id())
            windows = self.controller._desktop().windows(visible_only=True)
        except Exception:
            log.warning("Room event monitor could not inspect Camfrog windows")
            return (), "Could not inspect the selected Camfrog process"

        cooldown = min(3600, max(1, int(settings.get("cooldown_seconds", 10))))
        now = time.monotonic()
        events: list[RoomEventMatch] = []
        matched_room = False
        for window in windows:
            try:
                if int(window.process_id()) != target_pid:
                    continue
                room_title = str(window.window_text() or "").strip()
                if not room_title_matches(room_title, configured_room_title):
                    continue
                if title_fragment.casefold() not in room_title.casefold():
                    continue
                history = _find_history_control(window, history_id)
                if history is None:
                    continue
                matched_room = True
                handle = int(window.handle)
                key = (handle, room_title)
                current = _history_lines(history)
                previous = self._snapshots.get(key)
                self._snapshots[key] = current
                if previous is None:
                    # Establish a baseline so old history never triggers alerts.
                    continue
                for line in _new_lines(previous, current):
                    line_folded = line.casefold()
                    for term in terms:
                        if term.casefold() not in line_folded:
                            continue
                        throttle_key = (handle, room_title, term.casefold())
                        last_alert = self._last_alert.get(throttle_key)
                        if last_alert is not None and now - last_alert < cooldown:
                            break
                        self._last_alert[throttle_key] = now
                        events.append(RoomEventMatch(room_title, term))
                        break
            except Exception:
                log.debug("Skipping a Camfrog room window after a UIA error")

        if events:
            return tuple(events[:10]), "New configured room event detected"
        if matched_room:
            return (), "Room event monitor is watching configured room history"
        return (), "Waiting for the configured room chat window"

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


class RoomEventMonitorWorker:
    def __init__(
        self,
        controller,
        get_config: Callable[[], dict[str, Any]],
        on_events: Callable[[tuple[RoomEventMatch, ...]], None] | None = None,
        on_state: Callable[[str], None] | None = None,
    ):
        self.controller = controller
        self.get_config = get_config
        self.on_events = on_events
        self.on_state = on_state
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._generation = 0

    def start(self) -> None:
        self.stop()
        self._stop.clear()
        self._generation += 1
        generation = self._generation
        monitor = CamfrogRoomEventMonitor(self.controller)

        def run() -> None:
            previous_state = ""
            while generation == self._generation and not self._stop.is_set():
                try:
                    config = self.get_config()
                    events, state = monitor.poll_once(config)
                    if events and self.on_events is not None:
                        self.on_events(events)
                    if state != previous_state and self.on_state is not None:
                        self.on_state(state)
                    previous_state = state
                    interval = max(1, int(config.get("auto_respond", {}).get("poll_interval_seconds", 2)))
                except Exception:
                    log.exception("Room event monitor polling failed")
                    interval = 2
                self._stop.wait(interval)

        self._thread = threading.Thread(target=run, daemon=True, name="camfrog-room-events")
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
