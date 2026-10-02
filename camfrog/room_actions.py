from __future__ import annotations

import logging
import os
import unicodedata
from dataclasses import dataclass
from typing import Any, Callable

log = logging.getLogger(__name__)

ROOM_ACTIONS = ("op", "friend", "admin", "owner", "mute", "kick", "ban")
CAMFROG_ROOM_TITLE_SUFFIX = ": Video Chat Room"


def room_title_matches(window_title: str, room_name: str) -> bool:
    """Match a configured room name to Camfrog's exact decorated room title."""
    title = str(window_title or "").strip().casefold()
    name = str(room_name or "").strip().casefold()
    return bool(name) and title in {name, f"{name}{CAMFROG_ROOM_TITLE_SUFFIX.casefold()}"}


def is_safe_room_nickname(username: str) -> bool:
    """Accept one bounded nickname without command or display-control characters."""
    return bool(username) and len(username) <= 64 and all(
        (character.isalnum() or character in "_.-")
        and not character.isspace()
        and unicodedata.category(character) not in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for character in username
    )


@dataclass
class RoomActionResult:
    ok: bool
    message: str
    action: str = ""


def build_room_command(action: str, target: str, template: str) -> tuple[str | None, str]:
    if action not in ROOM_ACTIONS:
        return None, "Select a supported room action"
    username = target if isinstance(target, str) else ""
    if not is_safe_room_nickname(username):
        return None, "Enter one nickname using letters, numbers, dot, underscore, or hyphen"
    raw_template = str(template)
    if any(
        character in "\r\n\u0085\u2028\u2029"
        or unicodedata.category(character) in {"Cc", "Cf", "Cs"}
        for character in raw_template
    ):
        return None, "Configure a single-line command template with exactly one {username} token"
    value = raw_template.strip()
    if not value or value.count("{username}") != 1:
        return None, "Configure a single-line command template with exactly one {username} token"
    if not value.startswith("/"):
        return None, "Room command templates must start with /"
    command = value.replace("{username}", username)
    if len(command) > 512:
        return None, "Configured room command is too long"
    return command, ""


class CamfrogRoomActionController:
    """Submit one manually confirmed command through configured visible UIA controls."""

    def __init__(self, controller):
        self.controller = controller

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

    @staticmethod
    def _value(control) -> tuple[bool, str]:
        getter = getattr(control, "get_value", None)
        if not callable(getter):
            return False, ""
        try:
            value = getter()
        except Exception:
            return False, ""
        return (value is not None, "" if value is None else str(value))

    def send_action(
        self,
        config: dict[str, Any],
        action: str,
        target: str,
        confirm: Callable[[str], bool],
        expected_room_title: str | None = None,
    ) -> RoomActionResult:
        settings = config.get("room_actions", {})
        if not isinstance(settings, dict) or settings.get("enabled") is not True:
            return RoomActionResult(False, "Room actions are disabled", action)
        templates = settings.get("command_templates", {})
        template = templates.get(action, "") if isinstance(templates, dict) else ""
        command, error = build_room_command(action, target, template)
        if error:
            return RoomActionResult(False, error, action)
        configured_room_title = str(settings.get("room_title", "")).strip()
        if not configured_room_title:
            return RoomActionResult(False, "Configure the exact room title first", action)
        if expected_room_title and not room_title_matches(expected_room_title, configured_room_title):
            return RoomActionResult(False, "Selected room does not match the configured room", action)
        selectors = config.get("auto_respond", {}).get("room", {})
        if not isinstance(selectors, dict):
            return RoomActionResult(False, "Configure room chat UIA selectors first", action)
        input_id = str(selectors.get("input_automation_id", "")).strip()
        send_id = str(selectors.get("send_automation_id", "")).strip()
        if not input_id or not send_id:
            return RoomActionResult(False, "Configure the room message input and send button UIA IDs first", action)
        if os.name != "nt":
            return RoomActionResult(False, "Room actions require Windows UI Automation", action)
        if not self.controller.client_processes():
            return RoomActionResult(False, "Camfrog is not running", action)

        try:
            main_window = self.controller.find_window()
            target_pid = int(main_window.process_id())
            visible_windows = self.controller._desktop().windows(visible_only=True)
        except Exception:
            log.warning("Room action could not inspect Camfrog windows")
            return RoomActionResult(False, "Could not inspect the selected Camfrog process", action)

        matches = []
        for window in visible_windows:
            try:
                if int(window.process_id()) != target_pid:
                    continue
                title = str(window.window_text() or "")
                if room_title_matches(title, configured_room_title):
                    matches.append(window)
            except Exception:
                continue
        if len(matches) != 1:
            return RoomActionResult(False, "Room chat window is missing or ambiguous; action was not sent", action)

        window = matches[0]
        compose = self._find_exact_id(window, input_id)
        send = self._find_exact_id(window, send_id)
        if compose is None or send is None:
            return RoomActionResult(False, "Configured room input or send control was not found uniquely", action)
        invoke_pattern = getattr(send, "iface_invoke", None)
        invoke = getattr(invoke_pattern, "Invoke", None)
        setter = getattr(compose, "set_edit_text", None)
        readable, current_value = self._value(compose)
        if not callable(invoke) or not callable(setter):
            return RoomActionResult(False, "Room input and send controls do not expose the required UIA patterns", action)
        if not readable or current_value.strip():
            return RoomActionResult(False, "Room message input is unreadable or contains a draft; action was not sent", action)

        try:
            approved = bool(confirm(command))
        except Exception:
            log.warning("Room action confirmation failed (%s)", action)
            return RoomActionResult(False, "Room action confirmation failed; action was not sent", action)
        if not approved:
            return RoomActionResult(False, "Room action cancelled", action)

        # Recheck the draft after the modal confirmation, then write once and
        # invoke only the exact configured send button. Never clear/replace a draft.
        readable, current_value = self._value(compose)
        if not readable or current_value.strip():
            return RoomActionResult(False, "Room input changed during confirmation; action was not sent", action)
        try:
            setter(command)
            readable, observed = self._value(compose)
            if not readable or observed != command:
                return RoomActionResult(False, "Room command could not be verified in the input; send was skipped", action)
            invoke()
        except Exception:
            log.warning("Room action UIA submission failed (%s)", action)
            return RoomActionResult(False, "Room action submission failed; Camfrog acceptance is unknown", action)
        return RoomActionResult(
            True,
            "Confirmed room command submitted through Camfrog UI; server authorization and result are not independently confirmed",
            action,
        )
