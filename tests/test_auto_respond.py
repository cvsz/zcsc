from __future__ import annotations

from types import SimpleNamespace

import camfrog.auto_respond as auto_respond
from camfrog.auto_respond import CamfrogAutoResponder, _new_lines, _parse_message, normalize_reply_text


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
    def __init__(self):
        self.handle = 123
        self.title = "Private chat - Alice"
        self.history = FakeControl("Document", "private-history")
        self.compose = FakeControl("Edit", "private-input")
        self.send = FakeButton("private-send")
        self.history.children = []

    def process_id(self):
        return 77

    def window_text(self):
        return self.title

    def descendants(self):
        return [self.history, *self.history.children, self.compose, self.send]


class FakeDesktop:
    def __init__(self, window):
        self.window = window

    def windows(self, visible_only=True):
        assert visible_only is True
        return [self.window]


class FakeController:
    def __init__(self, window):
        self.window = window

    def find_window(self):
        return self.window

    def client_processes(self):
        return [object()]

    def _desktop(self):
        return FakeDesktop(self.window)


def _config():
    return {
        "auto_respond": {
            "enabled": True,
            "private_enabled": True,
            "room_enabled": False,
            "reply_text": "Thanks for your message.",
            "own_username": "MyNick",
            "cooldown_seconds": 60,
            "private": {
                "window_title_contains": "Private chat",
                "history_automation_id": "private-history",
                "input_automation_id": "private-input",
                "send_automation_id": "private-send",
            },
            "room": {},
        }
    }


def _set_history(window, *lines):
    window.history.children = [FakeControl("Text", text=line) for line in lines]


def test_auto_respond_uses_only_new_incoming_messages(monkeypatch):
    window = FakeWindow()
    controller = FakeController(window)
    responder = CamfrogAutoResponder(controller)
    config = _config()
    monkeypatch.setattr(auto_respond, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(auto_respond, "time", SimpleNamespace(monotonic=lambda: 1.0))

    _set_history(window, "Alice: Existing message")
    assert responder.poll_once(config) == "Auto respond is monitoring configured chat controls"
    assert window.send.invocations == 0

    _set_history(window, "Alice: Existing message", "Alice: New message")
    assert responder.poll_once(config) == "Auto reply submitted (private chat)"
    assert window.send.invocations == 1

    assert responder.poll_once(config) == "Auto respond is monitoring configured chat controls"
    _set_history(window, "Alice: Existing message", "Alice: New message", "MyNick: Thanks for your message.")
    assert responder.poll_once(config) == "Auto respond is monitoring configured chat controls"
    assert window.send.invocations == 1


def test_auto_respond_supports_room_chat_mapping(monkeypatch):
    window = FakeWindow()
    window.title = "Welcome Room"
    window.history.element_info.automation_id = "room-history"
    window.compose.element_info.automation_id = "room-input"
    window.send.element_info.automation_id = "room-send"
    config = _config()
    config["auto_respond"]["private_enabled"] = False
    config["auto_respond"]["room_enabled"] = True
    config["auto_respond"]["room"] = {
        "window_title_contains": "Room",
        "history_automation_id": "room-history",
        "input_automation_id": "room-input",
        "send_automation_id": "room-send",
    }
    responder = CamfrogAutoResponder(FakeController(window))
    monkeypatch.setattr(auto_respond, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(auto_respond, "time", SimpleNamespace(monotonic=lambda: 1.0))

    _set_history(window, "Alice: Existing room message")
    responder.poll_once(config)
    _set_history(window, "Alice: Existing room message", "Bob: New room message")
    assert responder.poll_once(config) == "Auto reply submitted (room chat)"
    assert window.send.invocations == 1


def test_message_deltas_and_sender_parser_are_conservative():
    assert _new_lines(("Alice: first",), ("Alice: first", "Bob: second")) == ("Bob: second",)
    assert _new_lines(("Alice: same",), ("Alice: same", "Alice: same")) == ()
    assert _parse_message("[12:34:56] Alice: hello") == ("Alice", "hello")
    assert _parse_message("Camfrog system notification") is None


def test_reply_normalization_preserves_user_entered_lines():
    assert normalize_reply_text("  Hello   there\r\n\r\n  How are you?  ") == "Hello there\n\nHow are you?"


def test_auto_respond_submits_multiline_reply_as_one_message(monkeypatch):
    window = FakeWindow()
    controller = FakeController(window)
    responder = CamfrogAutoResponder(controller)
    config = _config()
    config["auto_respond"]["reply_text"] = "First line\nSecond line"
    monkeypatch.setattr(auto_respond, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(auto_respond, "time", SimpleNamespace(monotonic=lambda: 1.0))

    _set_history(window, "Alice: Existing message")
    responder.poll_once(config)
    _set_history(window, "Alice: Existing message", "Alice: New message")

    assert responder.poll_once(config) == "Auto reply submitted (private chat)"
    assert window.compose.text == "First line\nSecond line"
    assert window.send.invocations == 1
