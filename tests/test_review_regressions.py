from __future__ import annotations

import sys
import threading
from types import ModuleType, SimpleNamespace

import pytest

from automation.rotation import RotationWorker
from camfrog import background_win32
from camfrog.controller import CamfrogController, ChangeResult


def test_native_combo_notifications_load_win32_constants(monkeypatch):
    events = []
    constants = SimpleNamespace(CBN_EDITUPDATE=6, CBN_EDITCHANGE=5, WM_COMMAND=0x0111)
    monkeypatch.setitem(sys.modules, "win32con", constants)
    monkeypatch.setitem(sys.modules, "win32gui", SimpleNamespace(GetDlgCtrlID=lambda _hwnd: 42))
    monkeypatch.setattr(background_win32, "_parent_chain", lambda _hwnd: [31])
    monkeypatch.setattr(
        background_win32,
        "_send_timeout",
        lambda *args, **kwargs: events.append((args, kwargs)),
    )

    background_win32._notify_combo_parent(11, 22)

    assert len(events) == 4
    assert {call[0][0] for call in events} == {31, 11}
    assert all(call[0][1] == constants.WM_COMMAND for call in events)


def test_coordinate_fallback_restores_clipboard_when_commit_aborts(monkeypatch):
    clipboard = ["clipboard before"]
    events = []
    pyperclip = ModuleType("pyperclip")
    pyperclip.paste = lambda: clipboard[0]
    pyperclip.copy = lambda value: clipboard.__setitem__(0, value)
    keyboard = ModuleType("pywinauto.keyboard")
    keyboard.send_keys = lambda value: events.append(("keys", value))
    mouse = SimpleNamespace(click=lambda **kwargs: events.append(("click", kwargs)))
    pywinauto = ModuleType("pywinauto")
    pywinauto.__path__ = []
    pywinauto.mouse = mouse
    monkeypatch.setitem(sys.modules, "pyperclip", pyperclip)
    monkeypatch.setitem(sys.modules, "pywinauto", pywinauto)
    monkeypatch.setitem(sys.modules, "pywinauto.keyboard", keyboard)

    controller = CamfrogController(
        {
            "camfrog": {"executable": ""},
            "target": {"fallback_relative_x": 0.5, "fallback_relative_y": 0.5},
            "advanced": {"max_status_length": 160},
        }
    )
    editor = SimpleNamespace(handle=33)
    combo = SimpleNamespace(handle=22)
    controller._find_target = lambda _window: combo
    controller._find_status_editor = lambda _combo: editor
    controller._wait_for_foreground_status = lambda *_args: (False, "new", "foreground changed")
    window = SimpleNamespace(
        restore=lambda: events.append(("restore",)),
        set_focus=lambda: events.append(("focus",)),
        rectangle=lambda: SimpleNamespace(
            left=0,
            top=0,
            width=lambda: 100,
            height=lambda: 100,
        ),
    )
    monkeypatch.setattr("camfrog.controller.per_monitor_v2_ready", lambda: True)
    monkeypatch.setattr("camfrog.controller.time.sleep", lambda _seconds: None)

    with pytest.raises(RuntimeError, match="Enter was not sent"):
        controller._coordinate_fallback(window, "new")

    assert clipboard[0] == "clipboard before"


def test_stopped_rotation_does_not_send_after_waiting_for_status_lock(monkeypatch):
    events = []
    clipboard = ["clipboard before"]
    pyperclip = ModuleType("pyperclip")
    pyperclip.paste = lambda: clipboard[0]
    pyperclip.copy = lambda value: clipboard.__setitem__(0, value)
    keyboard = ModuleType("pywinauto.keyboard")

    def send_keys(value):
        events.append(("paste-key", value))
        if value == "^a{BACKSPACE}":
            editor.text = ""
        elif value == "^v":
            editor.text = clipboard[0]

    keyboard.send_keys = send_keys
    pywinauto = ModuleType("pywinauto")
    pywinauto.__path__ = []
    monkeypatch.setitem(sys.modules, "pyperclip", pyperclip)
    monkeypatch.setitem(sys.modules, "pywinauto", pywinauto)
    monkeypatch.setitem(sys.modules, "pywinauto.keyboard", keyboard)
    monkeypatch.setattr("camfrog.controller.time.sleep", lambda _seconds: None)

    class Edit:
        handle = 33
        element_info = SimpleNamespace(class_name="CEdit4ComboInnerTS", control_type="Edit")
        text = "old"

        def set_focus(self):
            return None

        def window_text(self):
            return self.text

        def type_keys(self, value):
            events.append(("enter", value))

    editor = Edit()
    combo = SimpleNamespace(
        handle=22,
        descendants=lambda: [editor],
        window_text=lambda: editor.text,
    )
    window = SimpleNamespace(
        handle=11,
        process_id=lambda: 123,
        restore=lambda: None,
        set_focus=lambda: None,
    )
    controller = CamfrogController(
        {
            "camfrog": {"executable": ""},
            "target": {"background_enabled": False},
            "status": {"presets": []},
            "advanced": {"max_status_length": 160, "minimum_interval_seconds": 5},
        }
    )
    controller.ensure_running = lambda: events.append(("ensure",)) or ChangeResult(True, "running")
    controller.find_window = lambda: window
    controller._find_target = lambda _window: combo
    controller.native_profile_info = lambda: {"matched": True, "name": "test"}
    controller._wait_for_foreground_status = lambda _window, _edit, value: (True, value, "")
    controller._foreground_status_snapshot = lambda _window, _edit, value: (True, value, "")

    real_lock = threading.Lock()
    real_lock.acquire()
    lock_attempted = threading.Event()

    class TrackedLock:
        def acquire(self, blocking=True, timeout=-1):
            lock_attempted.set()
            return real_lock.acquire(blocking, timeout)

        def release(self):
            real_lock.release()

    controller._apply_lock = TrackedLock()
    worker = RotationWorker(controller.set_status)
    worker.start(["stale status"], 60, "sequential")
    assert lock_attempted.wait(timeout=1)

    stopped = threading.Thread(target=worker.stop)
    stopped.start()
    assert worker._stop.wait(timeout=1)
    real_lock.release()
    stopped.join(timeout=2)

    assert not stopped.is_alive()
    assert not any(event == ("enter", "{ENTER}") for event in events)
    assert not any(event == ("ensure",) for event in events)


def test_cancelled_status_result_does_not_report_requested_text_as_previous():
    controller = CamfrogController({"advanced": {"max_status_length": 160}})
    controller.ensure_running = lambda: pytest.fail("cancelled requests must not start Camfrog")

    result = controller.set_status("stale status", cancelled=lambda: True)

    assert not result.ok
    assert result.previous_value == ""
    assert result.new_value == "stale status"
