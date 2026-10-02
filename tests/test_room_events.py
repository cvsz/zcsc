from types import SimpleNamespace

import camfrog.room_events as room_events
from camfrog.room_events import CamfrogRoomEventMonitor


class FakeElement:
    def __init__(self, automation_id=""):
        self.element_info = SimpleNamespace(automation_id=automation_id)


class FakeWindow:
    def __init__(self, history):
        self.handle = 22
        self.history = history

    def process_id(self):
        return 11

    def window_text(self):
        return "Example room"

    def descendants(self):
        return [self.history]


class FakeController:
    def __init__(self, window):
        self.window = window

    def find_window(self):
        return SimpleNamespace(process_id=lambda: 11)

    def client_processes(self):
        return [object()]

    def _desktop(self):
        return SimpleNamespace(windows=lambda **_kwargs: [self.window])


def config():
    return {
        "room_event_notifications": {
            "enabled": True,
            "phrases": ["was granted op", "was kicked"],
            "cooldown_seconds": 10,
        },
        "room_actions": {"room_title": "Example room"},
        "auto_respond": {
            "room": {
                "window_title_contains": "Example room",
                "history_automation_id": "room-history",
            },
        },
    }


def test_room_event_monitor_uses_baseline_and_matches_only_new_lines(monkeypatch):
    lines = [("older room history",)]
    history = FakeElement("room-history")
    window = FakeWindow(history)
    monitor = CamfrogRoomEventMonitor(FakeController(window))
    monkeypatch.setattr(room_events.os, "name", "nt")
    monkeypatch.setattr(room_events, "_history_lines", lambda _control: lines[0])

    events, state = monitor.poll_once(config())
    assert events == ()
    assert state == "Room event monitor is watching configured room history"

    lines[0] = ("older room history", "A member was granted op")
    events, state = monitor.poll_once(config())
    assert [(event.room_title, event.trigger_phrase) for event in events] == [
        ("Example room", "was granted op")
    ]
    assert state == "New configured room event detected"

    events, _state = monitor.poll_once(config())
    assert events == ()


def test_room_event_monitor_requires_visible_room_selectors(monkeypatch):
    monitor = CamfrogRoomEventMonitor(FakeController(FakeWindow(FakeElement("room-history"))))
    monkeypatch.setattr(room_events.os, "name", "nt")
    invalid = config()
    invalid["auto_respond"]["room"]["history_automation_id"] = ""

    events, state = monitor.poll_once(invalid)

    assert events == ()
    assert state == "Configure the room title and history UIA ID first"
