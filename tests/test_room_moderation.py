from __future__ import annotations

from types import SimpleNamespace

import camfrog.bad_word_moderation as bad_word_moderation
import camfrog.auto_respond as auto_respond
import camfrog.room_actions as room_actions
from camfrog.bad_word_moderation import (
    BadWordMatch,
    CamfrogBadWordMonitor,
    find_bad_word_term,
    submit_bad_word_kick,
)
from camfrog.room_actions import CamfrogRoomActionController, build_room_command, room_title_matches


class FakeControl:
    def __init__(self, control_type, automation_id="", text=""):
        self.element_info = SimpleNamespace(control_type=control_type, automation_id=automation_id)
        self.text = text
        self.children = []

    def is_visible(self):
        return True

    def descendants(self):
        return list(self.children)

    def get_value(self):
        return self.text

    def window_text(self):
        return self.text

    def set_edit_text(self, value):
        self.text = value


class FakeButton(FakeControl):
    def __init__(self, automation_id):
        super().__init__("Button", automation_id)
        self.invocations = 0
        self.iface_invoke = SimpleNamespace(Invoke=self.invoke)

    def invoke(self):
        self.invocations += 1


class FakeWindow:
    def __init__(self, title="Welcome Room"):
        self.handle = 123
        self.title = title
        self.history = FakeControl("Document", "room-history")
        self.compose = FakeControl("Edit", "room-input")
        self.send = FakeButton("room-send")

    def process_id(self):
        return 77

    def window_text(self):
        return self.title

    def descendants(self):
        return [self.history, *self.history.children, self.compose, self.send]


class FakeDesktop:
    def __init__(self, windows):
        self._windows = windows

    def windows(self, visible_only=True):
        assert visible_only is True
        return self._windows


class FakeController:
    def __init__(self, window, windows=None):
        self.window = window
        self.windows = windows if windows is not None else [window]

    def find_window(self):
        return self.window

    def client_processes(self):
        return [object()]

    def _desktop(self):
        return FakeDesktop(self.windows)


def _moderation_config():
    return {
        "auto_respond": {
            "own_username": "MyNick",
            "poll_interval_seconds": 1,
            "room": {
                "window_title_contains": "Room",
                "history_automation_id": "room-history",
                "input_automation_id": "room-input",
                "send_automation_id": "room-send",
            },
        },
        "room_actions": {
            "enabled": True,
            "room_title": "Welcome Room",
            "owner_nickname": "RoomOwner",
            "target_nicknames": {"friend": "FriendNick"},
            "command_templates": {"kick": "/kick {username}"},
        },
        "bad_word_moderation": {
            "enabled": True,
            "auto_kick": False,
            "terms": ["badword"],
            "cooldown_seconds": 60,
        },
    }


def _set_history(window, *lines):
    window.history.children = [FakeControl("Text", text=line) for line in lines]


def test_room_command_requires_safe_single_nickname_and_configured_template():
    assert build_room_command("kick", "Alice_7", "/kick {username}") == ("/kick Alice_7", "")
    assert build_room_command("kick", "Alice Bob", "/kick {username}")[0] is None
    assert build_room_command("kick", "Alice;/ban", "/kick {username}")[0] is None
    assert build_room_command("kick", "Alice", "")[0] is None
    assert build_room_command("unknown", "Alice", "/kick {username}")[0] is None


def test_room_title_matches_only_exact_name_or_camfrog_room_suffix():
    assert room_title_matches("FixtureRoom", "FixtureRoom")
    assert room_title_matches("FixtureRoom: Video Chat Room", "FixtureRoom")
    assert not room_title_matches("FixtureRoom Extra: Video Chat Room", "FixtureRoom")
    assert not room_title_matches("Other FixtureRoom: Video Chat Room", "FixtureRoom")


def test_duplicate_history_ids_require_one_message_shaped_control():
    with_messages = FakeControl("Pane", "room-history")
    with_messages.children = [FakeControl("Text", text="Alice: hello")]
    empty = FakeControl("Pane", "room-history")
    window = SimpleNamespace(descendants=lambda: [empty, with_messages])

    assert auto_respond._find_history_control(window, "room-history") is with_messages

    another_messages = FakeControl("Pane", "room-history")
    another_messages.children = [FakeControl("Text", text="Bob: hi")]
    ambiguous = SimpleNamespace(descendants=lambda: [with_messages, another_messages])
    assert auto_respond._find_history_control(ambiguous, "room-history") is None


def test_bad_word_filter_detects_spaced_leet_and_masked_terms_without_common_word_matches():
    assert find_bad_word_term("Stop f u c k now", ("fuck",)) == "fuck"
    assert find_bad_word_term("you b1tch", ("bitch",)) == "bitch"
    assert find_bad_word_term("ค-ว-ย", ("ควย",)) == "ควย"
    assert find_bad_word_term("assassin and class", ("ass",)) is None


def test_bad_word_filter_honors_safe_word_allowlist():
    assert find_bad_word_term("ฟักทองกับกล้วย", ("ฟัก", "กล้วย")) is None


def test_room_action_requires_confirmation_and_exact_room(monkeypatch):
    window = FakeWindow()
    controller = CamfrogRoomActionController(FakeController(window))
    config = _moderation_config()
    monkeypatch.setattr(room_actions, "os", SimpleNamespace(name="nt"))

    rejected = controller.send_action(config, "kick", "Alice", lambda _command: False)
    assert not rejected.ok
    assert window.send.invocations == 0

    accepted = controller.send_action(
        config,
        "kick",
        "Alice",
        lambda command: command == "/kick Alice",
        expected_room_title="Welcome Room",
    )
    assert accepted.ok
    assert window.compose.text == "/kick Alice"
    assert window.send.invocations == 1
    mismatch = controller.send_action(
        config,
        "kick",
        "Bob",
        lambda _command: True,
        expected_room_title="Different Room",
    )
    assert not mismatch.ok
    assert window.send.invocations == 1


def test_room_action_accepts_camfrog_room_suffix_but_cancels_before_send(monkeypatch):
    window = FakeWindow(title="Welcome Room: Video Chat Room")
    controller = CamfrogRoomActionController(FakeController(window))
    monkeypatch.setattr(room_actions, "os", SimpleNamespace(name="nt"))

    result = controller.send_action(
        _moderation_config(),
        "kick",
        "Alice",
        lambda _command: False,
        expected_room_title="Welcome Room",
    )

    assert not result.ok
    assert result.message == "Room action cancelled"
    assert window.send.invocations == 0


def test_room_action_never_replaces_an_existing_draft(monkeypatch):
    window = FakeWindow()
    window.compose.text = "my unsent draft"
    controller = CamfrogRoomActionController(FakeController(window))
    monkeypatch.setattr(room_actions, "os", SimpleNamespace(name="nt"))

    result = controller.send_action(_moderation_config(), "kick", "Alice", lambda _command: True)

    assert not result.ok
    assert window.compose.text == "my unsent draft"
    assert window.send.invocations == 0


def test_room_action_requires_exact_room_configuration(monkeypatch):
    window = FakeWindow()
    controller = CamfrogRoomActionController(FakeController(window))
    config = _moderation_config()
    config["room_actions"]["room_title"] = "Another Room"
    monkeypatch.setattr(room_actions, "os", SimpleNamespace(name="nt"))

    result = controller.send_action(config, "kick", "Alice", lambda _command: True)

    assert not result.ok
    assert window.send.invocations == 0


def test_bad_word_auto_kick_setting_submits_once_without_prompt(monkeypatch):
    window = FakeWindow()
    controller = CamfrogRoomActionController(FakeController(window))
    config = _moderation_config()
    config["bad_word_moderation"]["auto_kick"] = True
    match = BadWordMatch("Welcome Room", "Alice_7", "new badword message", "badword")
    monkeypatch.setattr(room_actions, "os", SimpleNamespace(name="nt"))

    result = submit_bad_word_kick(
        config,
        match,
        controller,
        confirm=lambda _command: (_ for _ in ()).throw(AssertionError("confirmation should be skipped")),
    )

    assert result is not None and result.ok
    assert window.compose.text == "/kick Alice_7"
    assert window.send.invocations == 1


def test_bad_word_auto_kick_rechecks_current_term_configuration():
    config = _moderation_config()
    config["bad_word_moderation"]["auto_kick"] = True
    config["bad_word_moderation"]["terms"] = ["different"]
    match = BadWordMatch("Welcome Room", "Alice_7", "badword", "badword")
    calls = []

    result = submit_bad_word_kick(
        config,
        match,
        SimpleNamespace(send_action=lambda *args, **kwargs: calls.append((args, kwargs))),
        confirm=lambda _command: True,
    )

    assert result is None
    assert calls == []


def test_bad_word_monitor_only_reports_new_messages_and_skips_own_account(monkeypatch):
    window = FakeWindow(title="Welcome Room: Video Chat Room")
    monitor = CamfrogBadWordMonitor(FakeController(window))
    config = _moderation_config()
    monkeypatch.setattr(bad_word_moderation, "os", SimpleNamespace(name="nt"))

    _set_history(window, "Alice: old badword")
    matches, state = monitor.poll_once(config)
    assert matches == ()
    assert "watching" in state

    _set_history(window, "Alice: old badword", "Bob: new BADWORD here")
    matches, state = monitor.poll_once(config)
    assert len(matches) == 1
    assert matches[0].sender == "Bob"
    assert matches[0].term == "badword"
    assert matches[0].body == "new BADWORD here"
    assert "confirmation" in state

    _set_history(window, "Alice: old badword", "Bob: new BADWORD here", "MyNick: badword")
    matches, _state = monitor.poll_once(config)
    assert matches == ()


def test_bad_word_monitor_rejects_nonmatching_room_title(monkeypatch):
    window = FakeWindow(title="Another Room")
    _set_history(window, "Alice: old badword")
    monitor = CamfrogBadWordMonitor(FakeController(window))
    monkeypatch.setattr(bad_word_moderation, "os", SimpleNamespace(name="nt"))

    matches, state = monitor.poll_once(_moderation_config())

    assert matches == ()
    assert state == "Waiting for the configured room chat window"
