from __future__ import annotations

import logging
import os
import re
import threading
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from .auto_respond import _find_history_control, _history_lines, _new_lines, _parse_message
from .bad_word_catalog import DEFAULT_BAD_WORD_ALLOWLIST, DEFAULT_BAD_WORD_PATTERNS
from .room_actions import room_title_matches

log = logging.getLogger(__name__)
_SEPARATOR_PATTERN = r"[.\-_ *\s]*"


@lru_cache(maxsize=1024)
def _compile_term_pattern(term: str) -> re.Pattern[str]:
    pieces = [_SEPARATOR_PATTERN.join(re.escape(character) for character in term)]
    pattern = pieces[0]
    if any(character.isascii() and character.isalnum() for character in term):
        pattern = rf"(?<![A-Za-z0-9]){pattern}(?![A-Za-z0-9])"
    return re.compile(pattern, re.IGNORECASE)


def _is_allowlisted_match(text: str, start: int, end: int) -> bool:
    for exception in DEFAULT_BAD_WORD_ALLOWLIST:
        for safe_match in re.finditer(re.escape(exception), text, re.IGNORECASE):
            if safe_match.start() <= start and end <= safe_match.end():
                return True
    return False


def find_bad_word_term(body: str, terms: tuple[str, ...] | list[str]) -> str | None:
    """Return the configured term detected in a new message, if any."""
    text = unicodedata.normalize("NFKC", str(body))
    configured = [str(term).strip() for term in terms if len(str(term).strip()) >= 2]
    for term in configured:
        match = _compile_term_pattern(term).search(text)
        if match and not _is_allowlisted_match(text, match.start(), match.end()):
            return term

    configured_by_fold = {term.casefold(): term for term in configured}
    for canonical_term, pattern in DEFAULT_BAD_WORD_PATTERNS:
        configured_term = configured_by_fold.get(canonical_term.casefold())
        if configured_term is None:
            continue
        for match in pattern.finditer(text):
            if not _is_allowlisted_match(text, match.start(), match.end()):
                return configured_term
    return None


@dataclass(frozen=True)
class BadWordMatch:
    room_title: str
    sender: str
    body: str
    term: str


def submit_bad_word_kick(
    config: dict[str, Any],
    match: BadWordMatch,
    room_action_controller: Any,
    confirm: Callable[[str], bool],
) -> Any | None:
    """Submit a current configured kick rule without broadening it to stale matches."""
    moderation = config.get("bad_word_moderation", {})
    room_actions = config.get("room_actions", {})
    if (
        not isinstance(moderation, dict)
        or moderation.get("enabled") is not True
        or not isinstance(room_actions, dict)
        or room_actions.get("enabled") is not True
    ):
        return None
    terms = moderation.get("terms", [])
    if not isinstance(terms, list) or not any(
        str(term).casefold() == match.term.casefold() for term in terms
    ):
        return None

    # Automatic moderation is an explicit, persisted opt-in. It still passes
    # through the same nickname, exact-room, empty-draft, UIA verification, and
    # single-send checks as a manually approved room command.
    approval = (lambda _command: True) if moderation.get("auto_kick") is True else confirm
    return room_action_controller.send_action(
        config,
        "kick",
        match.sender,
        approval,
        expected_room_title=match.room_title,
    )


class CamfrogBadWordMonitor:
    """Read configured visible room history and report new matching messages."""

    def __init__(self, controller):
        self.controller = controller
        self._snapshots: dict[tuple[int, str], tuple[str, ...]] = {}
        self._last_alert: dict[tuple[int, str, str], float] = {}

    def poll_once(self, config: dict[str, Any]) -> tuple[tuple[BadWordMatch, ...], str]:
        moderation = config.get("bad_word_moderation", {})
        if not isinstance(moderation, dict) or moderation.get("enabled") is not True:
            return (), "Bad-word monitoring is disabled"
        if os.name != "nt":
            return (), "Bad-word monitoring requires Windows UI Automation"
        if config.get("room_actions", {}).get("enabled") is not True:
            return (), "Enable configured room actions before bad-word monitoring"
        configured_room_title = str(config.get("room_actions", {}).get("room_title", "")).strip()
        if not configured_room_title:
            return (), "Configure the exact room title before bad-word monitoring"
        selectors = config.get("auto_respond", {}).get("room", {})
        if not isinstance(selectors, dict):
            return (), "Configure room chat UIA selectors first"
        title_fragment = str(selectors.get("window_title_contains", "")).strip()
        history_id = str(selectors.get("history_automation_id", "")).strip()
        if not title_fragment or not history_id:
            return (), "Configure the room title and history UIA ID first"
        own_username = str(config.get("auto_respond", {}).get("own_username", "")).strip()
        if not own_username:
            return (), "Enter your Camfrog nickname to ignore your own messages"
        terms = tuple(
            str(term).strip()
            for term in moderation.get("terms", [])
            if len(str(term).strip()) >= 2
        )
        if not terms:
            return (), "Add at least one bad-word term"
        if not self.controller.client_processes():
            return (), "Camfrog is not running"

        try:
            main_window = self.controller.find_window()
            target_pid = int(main_window.process_id())
            windows = self.controller._desktop().windows(visible_only=True)
        except Exception:
            log.warning("Bad-word monitor could not inspect Camfrog windows")
            return (), "Could not inspect the selected Camfrog process"

        cooldown = min(3600, max(10, int(moderation.get("cooldown_seconds", 60))))
        now = time.monotonic()
        matches: list[BadWordMatch] = []
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
                key = (int(window.handle), room_title)
                current = _history_lines(history)
                previous = self._snapshots.get(key)
                self._snapshots[key] = current
                if previous is None:
                    # Establish a baseline so existing chat lines never trigger moderation.
                    continue
                for line in _new_lines(previous, current):
                    parsed = _parse_message(line)
                    if parsed is None:
                        continue
                    sender, body = parsed
                    if sender.casefold() == own_username.casefold():
                        continue
                    term = find_bad_word_term(body, terms)
                    if term is None:
                        continue
                    throttle_key = (int(window.handle), sender.casefold(), term.casefold())
                    if now - self._last_alert.get(throttle_key, 0.0) < cooldown:
                        continue
                    self._last_alert[throttle_key] = now
                    matches.append(BadWordMatch(room_title, sender, body, term))
            except Exception:
                log.debug("Skipping a Camfrog room window after a UIA error")
        if matches:
            state = (
                "Configured bad-word match detected; auto-kick enabled"
                if moderation.get("auto_kick") is True
                else "Configured bad-word match detected; awaiting operator confirmation"
            )
            return tuple(matches[:10]), state
        if matched_room:
            return (), "Bad-word monitor is watching configured room history"
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


class BadWordMonitorWorker:
    def __init__(
        self,
        controller,
        get_config: Callable[[], dict[str, Any]],
        on_matches: Callable[[tuple[BadWordMatch, ...]], None] | None = None,
        on_state: Callable[[str], None] | None = None,
    ):
        self.controller = controller
        self.get_config = get_config
        self.on_matches = on_matches
        self.on_state = on_state
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._generation = 0

    def start(self) -> None:
        self.stop()
        self._stop.clear()
        self._generation += 1
        generation = self._generation
        monitor = CamfrogBadWordMonitor(self.controller)

        def run() -> None:
            previous_state = ""
            while generation == self._generation and not self._stop.is_set():
                try:
                    config = self.get_config()
                    matches, state = monitor.poll_once(config)
                    if matches and self.on_matches is not None:
                        self.on_matches(matches)
                    if state != previous_state and self.on_state is not None:
                        self.on_state(state)
                    previous_state = state
                    interval = max(1, int(config.get("auto_respond", {}).get("poll_interval_seconds", 2)))
                except Exception:
                    log.exception("Bad-word monitor polling failed")
                    interval = 2
                self._stop.wait(interval)

        self._thread = threading.Thread(target=run, daemon=True, name="camfrog-bad-word-monitor")
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
