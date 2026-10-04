import sys
from types import ModuleType, SimpleNamespace

import pytest

from camfrog.controller import (
    AmbiguousStatusControlError,
    CamfrogController,
    CamfrogInstanceAmbiguityError,
    ChangeResult,
    UnverifiedStatusControlError,
)
from camfrog.background_win32 import BackgroundResult


def config():
    return {
        "advanced": {"max_status_length": 5, "minimum_interval_seconds": 5},
        "camfrog": {"executable": ""},
        "target": {},
        "status": {"presets": []},
    }


def test_empty_status_rejected_without_touching_windows():
    r = CamfrogController(config()).set_status("  ")
    assert not r.ok
    assert "empty" in r.message.lower()


def test_oversized_status_rejected_without_touching_windows():
    r = CamfrogController(config()).set_status("123456")
    assert not r.ok
    assert "maximum" in r.message.lower()


def test_next_camfrog_send_waits_for_minimum_spacing(monkeypatch):
    controller = CamfrogController(config())
    controller._last_send_monotonic = 100.0
    clock = [102.0]
    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr("camfrog.controller.time.monotonic", lambda: clock[0])
    monkeypatch.setattr("camfrog.controller.time.sleep", fake_sleep)

    controller._wait_for_send_slot()

    assert sleeps == [3.0]
    assert controller._last_send_monotonic == 105.0


def test_status_editor_prefers_exact_camfrog_native_edit_class():
    generic_edit = SimpleNamespace(
        element_info=SimpleNamespace(class_name="Edit", control_type="Edit")
    )
    native_edit = SimpleNamespace(
        element_info=SimpleNamespace(class_name="CEdit4ComboInnerTS", control_type="Edit")
    )
    combo = SimpleNamespace(descendants=lambda: [generic_edit, native_edit])

    assert CamfrogController._find_status_editor(combo) is native_edit


def test_status_editor_refuses_multiple_generic_edit_controls():
    edits = [
        SimpleNamespace(element_info=SimpleNamespace(class_name="Edit", control_type="Edit")),
        SimpleNamespace(element_info=SimpleNamespace(class_name="Edit", control_type="Edit")),
    ]
    combo = SimpleNamespace(descendants=lambda: edits)

    with pytest.raises(AmbiguousStatusControlError, match="multiple status Edit controls"):
        CamfrogController._find_status_editor(combo)


def test_status_target_rejects_unverified_generic_combo():
    control = SimpleNamespace(
        handle=1,
        element_info=SimpleNamespace(automation_id="", class_name="Edit", control_type="ComboBox"),
        window_text=lambda: "",
    )
    window = SimpleNamespace(descendants=lambda control_type=None: [control])

    with pytest.raises(UnverifiedStatusControlError, match="generic ComboBox"):
        CamfrogController(config())._find_target(window)


def test_status_target_accepts_explicit_configured_id():
    cfg = config()
    cfg["target"]["automation_id"] = "status-combo"
    control = SimpleNamespace(
        handle=1,
        element_info=SimpleNamespace(automation_id="status-combo", class_name="Edit", control_type="ComboBox"),
        window_text=lambda: "",
    )
    window = SimpleNamespace(descendants=lambda control_type=None: [control])

    assert CamfrogController(cfg)._find_target(window) is control


def test_status_target_accepts_native_camfrog_combo():
    control = SimpleNamespace(
        handle=1,
        element_info=SimpleNamespace(automation_id="", class_name="CComboBoxTS", control_type="Custom"),
        window_text=lambda: "",
    )
    window = SimpleNamespace(descendants=lambda control_type=None: [control])

    assert CamfrogController(config())._find_target(window) is control


def test_status_target_accepts_configured_known_status_value():
    cfg = config()
    cfg["status"]["presets"] = ["Known status"]
    control = SimpleNamespace(
        handle=1,
        element_info=SimpleNamespace(automation_id="", class_name="Edit", control_type="ComboBox"),
        window_text=lambda: "Known status",
    )
    window = SimpleNamespace(descendants=lambda control_type=None: [control])

    assert CamfrogController(cfg)._find_target(window) is control


def test_status_target_refuses_equal_scoring_native_controls():
    def candidate(handle):
        return SimpleNamespace(
            handle=handle,
            element_info=SimpleNamespace(automation_id="", class_name="CComboBoxTS", control_type="ComboBox"),
            window_text=lambda: "",
        )

    controls = [candidate(1), candidate(2)]
    window = SimpleNamespace(descendants=lambda control_type=None: controls if control_type else [])

    with pytest.raises(AmbiguousStatusControlError, match="matched equally"):
        CamfrogController(config())._find_target(window)


def test_find_window_requires_one_bound_pid_without_title_fallback():
    controller = CamfrogController(config())
    controller._bound_process = lambda: SimpleNamespace(pid=42)
    controller._find_window_by_pid = lambda: None

    with pytest.raises(RuntimeError, match="PID 42"):
        controller.find_window()


def test_ambiguous_uia_status_target_stops_before_win32_fallback(monkeypatch):
    controller = CamfrogController(config())
    controller.ensure_running = lambda: ChangeResult(True, "running")
    controller._wait_for_send_slot = lambda: None
    controller.find_window = lambda: SimpleNamespace(handle=11)
    controller.native_profile_info = lambda: {"matched": False, "sha256": ""}
    controller._find_target = lambda _window: (_ for _ in ()).throw(
        AmbiguousStatusControlError("multiple status controls")
    )
    fallback_calls = []
    monkeypatch.setattr(
        "camfrog.controller.set_status_background",
        lambda *_args, **_kwargs: fallback_calls.append("background"),
    )

    result = controller.set_status("Hello")

    assert not result.ok
    assert "multiple status controls" in result.message
    assert fallback_calls == []


def test_unverified_generic_uia_combo_stops_before_win32_or_coordinate_fallback(monkeypatch):
    controller = CamfrogController(config())
    controller.ensure_running = lambda: ChangeResult(True, "running")
    controller._wait_for_send_slot = lambda: None
    generic_combo = SimpleNamespace(
        handle=22,
        element_info=SimpleNamespace(automation_id="", class_name="Edit", control_type="ComboBox"),
        window_text=lambda: "",
    )
    controller.find_window = lambda: SimpleNamespace(
        handle=11,
        descendants=lambda control_type=None: [generic_combo],
    )
    controller.native_profile_info = lambda: {"matched": False, "sha256": ""}
    fallback_calls = []
    monkeypatch.setattr(
        "camfrog.controller.set_status_background",
        lambda *_args, **_kwargs: fallback_calls.append("background"),
    )
    controller._coordinate_fallback = lambda *_args: fallback_calls.append("coordinate")

    result = controller.set_status("Hello")

    assert not result.ok
    assert "configure its exact automation ID" in result.message
    assert fallback_calls == []


def test_ambiguous_background_control_stops_before_coordinate_fallback(monkeypatch):
    cfg = config()
    cfg["advanced"]["fallback_enabled"] = True
    controller = CamfrogController(cfg)
    controller.ensure_running = lambda: ChangeResult(True, "running")
    controller._wait_for_send_slot = lambda: None
    controller.find_window = lambda: SimpleNamespace(handle=11)
    controller.native_profile_info = lambda: {"matched": False, "sha256": ""}
    controller._find_target = lambda _window: (_ for _ in ()).throw(RuntimeError("UIA unavailable"))
    coordinate_calls = []
    monkeypatch.setattr(
        "camfrog.controller.set_status_background",
        lambda *_args, **_kwargs: BackgroundResult(
            False, "multiple native status controls", ambiguous=True
        ),
    )
    controller._coordinate_fallback = lambda *_args: coordinate_calls.append("foreground")

    result = controller.set_status("Hello")

    assert not result.ok
    assert "multiple native status controls" in result.message
    assert coordinate_calls == []


def test_stage_status_text_verifies_draft_without_sending_enter(monkeypatch):
    events = []
    clipboard = ["previous clipboard"]

    class Editor:
        element_info = SimpleNamespace(class_name="CEdit4ComboInnerTS", control_type="Edit")

        def __init__(self):
            self.text = "old draft"

        def set_focus(self):
            events.append("editor-focus")

        def window_text(self):
            return self.text

    editor = Editor()

    class Combo:
        def descendants(self):
            return [editor]

    class Window:
        def restore(self):
            events.append("restore")

        def set_focus(self):
            events.append("window-focus")

    pyperclip = ModuleType("pyperclip")
    pyperclip.paste = lambda: clipboard[0]
    pyperclip.copy = lambda value: clipboard.__setitem__(0, value)

    keyboard = ModuleType("pywinauto.keyboard")

    def send_keys(keys):
        events.append(("keys", keys))
        if keys == "^a{BACKSPACE}":
            editor.text = ""
        elif keys == "^v":
            editor.text = clipboard[0]

    keyboard.send_keys = send_keys
    pywinauto = ModuleType("pywinauto")
    pywinauto.__path__ = []
    monkeypatch.setitem(sys.modules, "pyperclip", pyperclip)
    monkeypatch.setitem(sys.modules, "pywinauto", pywinauto)
    monkeypatch.setitem(sys.modules, "pywinauto.keyboard", keyboard)
    monkeypatch.setattr("camfrog.controller.time.sleep", lambda seconds: events.append(("sleep", seconds)))

    controller = CamfrogController(config())
    controller.client_processes = lambda: [SimpleNamespace(pid=123)]
    controller.find_window = lambda: Window()
    controller._find_target = lambda _window: Combo()

    result = controller.stage_status_text("Hello")

    assert result.ok
    assert "Enter was not sent" in result.message
    assert editor.text == "Hello"
    assert clipboard[0] == "previous clipboard"
    assert events == [
        "restore",
        "window-focus",
        "editor-focus",
        ("sleep", 0.15),
        ("keys", "^a{BACKSPACE}"),
        ("keys", "^v"),
        ("sleep", 0.45),
    ]


def test_uia_status_pastes_from_clipboard_verifies_then_sends_one_real_enter(monkeypatch):
    class Edit:
        handle = 33
        element_info = SimpleNamespace(class_name="CEdit4ComboInnerTS", control_type="Edit")

        def __init__(self, events):
            self.events = events
            self.text = ""
            self.direct_write_calls = 0

        def set_focus(self):
            self.events.append("edit-focus")

        def set_edit_text(self, value):
            self.direct_write_calls += 1
            raise AssertionError("status payload must use clipboard paste")

        def type_keys(self, value):
            self.events.append(("key", value))

        def window_text(self):
            return self.text

    events = []
    edit = Edit(events)
    clipboard = ["clipboard before"]
    pyperclip = ModuleType("pyperclip")
    pyperclip.paste = lambda: clipboard[0]
    pyperclip.copy = lambda value: clipboard.__setitem__(0, value)

    keyboard = ModuleType("pywinauto.keyboard")

    def send_keys(keys):
        events.append(("keys", keys))
        if keys == "^a{BACKSPACE}":
            edit.text = ""
        elif keys == "^v":
            edit.text = clipboard[0]

    keyboard.send_keys = send_keys
    pywinauto = ModuleType("pywinauto")
    pywinauto.__path__ = []
    monkeypatch.setitem(sys.modules, "pyperclip", pyperclip)
    monkeypatch.setitem(sys.modules, "pywinauto", pywinauto)
    monkeypatch.setitem(sys.modules, "pywinauto.keyboard", keyboard)

    class Combo:
        handle = 22

        def descendants(self, control_type=None):
            return [edit]

        def window_text(self):
            return edit.text

        @property
        def iface_value(self):
            raise AssertionError("ValuePattern must not write the same edit again")

    class Window:
        handle = 11

        def process_id(self):
            return 123

        def restore(self):
            events.append("restore")

        def set_focus(self):
            events.append("window-focus")

    controller = CamfrogController(config())
    controller.ensure_running = lambda: ChangeResult(True, "running")
    controller._wait_for_send_slot = lambda: None
    controller.find_window = lambda: Window()
    controller._find_target = lambda _window: Combo()
    controller.native_profile_info = lambda: {"matched": True, "name": "test-profile"}
    controller._wait_for_foreground_status = lambda _window, _edit, value: (True, value, "")
    controller._foreground_status_snapshot = lambda _window, _edit, value: (True, value, "")
    monkeypatch.setattr("camfrog.controller.time.sleep", lambda seconds: events.append(("sleep", seconds)))
    monkeypatch.setattr(
        "camfrog.controller.set_status_background",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("payload must not be written twice")),
    )

    result = controller.set_status("Hello")

    assert result.ok
    assert "one foreground Enter sent" in result.message
    assert edit.direct_write_calls == 0
    assert edit.text == "Hello"
    assert clipboard[0] == "clipboard before"
    assert events == [
        "restore",
        "window-focus",
        "edit-focus",
        ("sleep", 0.15),
        ("keys", "^a{BACKSPACE}"),
        ("keys", "^v"),
        ("sleep", 0.1),
        "edit-focus",
        ("key", "{ENTER}"),
        ("sleep", 0.25),
    ]


def test_legacy_fallback_setting_does_not_change_verified_uia_commit(monkeypatch):
    clipboard = ["clipboard before"]
    writes = []

    class Edit:
        handle = 33
        element_info = SimpleNamespace(class_name="CEdit4ComboInnerTS", control_type="Edit")

        def __init__(self, events):
            self.events = events
            self.text = ""

        def set_focus(self):
            self.events.append("focus")

        def set_edit_text(self, value):
            writes.append(value)
            raise AssertionError("status payload must use clipboard paste")

        def type_keys(self, value):
            self.events.append(("key", value))

        def window_text(self):
            return self.text

    events = []
    edit = Edit(events)

    pyperclip = ModuleType("pyperclip")
    pyperclip.paste = lambda: clipboard[0]
    pyperclip.copy = lambda value: clipboard.__setitem__(0, value)

    keyboard = ModuleType("pywinauto.keyboard")

    def send_keys(keys):
        events.append(("keys", keys))
        if keys == "^a{BACKSPACE}":
            edit.text = ""
        elif keys == "^v":
            edit.text = clipboard[0]

    keyboard.send_keys = send_keys
    pywinauto = ModuleType("pywinauto")
    pywinauto.__path__ = []
    monkeypatch.setitem(sys.modules, "pyperclip", pyperclip)
    monkeypatch.setitem(sys.modules, "pywinauto", pywinauto)
    monkeypatch.setitem(sys.modules, "pywinauto.keyboard", keyboard)

    class Combo:
        handle = 22

        def descendants(self, control_type=None):
            return [edit]

        def window_text(self):
            return edit.text

    class Window:
        handle = 11

        def process_id(self):
            return 123

        def restore(self):
            events.append("restore")

        def set_focus(self):
            events.append("window-focus")

    controller_config = config()
    controller_config["advanced"].update({"fallback_enabled": True})
    controller = CamfrogController(controller_config)
    controller.ensure_running = lambda: ChangeResult(True, "running")
    controller._wait_for_send_slot = lambda: None
    controller.find_window = lambda: Window()
    controller._find_target = lambda _window: Combo()
    controller.native_profile_info = lambda: {"matched": True, "name": "test-profile"}
    controller._wait_for_foreground_status = lambda _window, _edit, value: (True, value, "")
    controller._foreground_status_snapshot = lambda _window, _edit, value: (True, value, "")
    monkeypatch.setattr("camfrog.controller.time.sleep", lambda seconds: events.append(("sleep", seconds)))
    monkeypatch.setattr(
        "camfrog.controller.set_status_background",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("payload must not be written twice")),
    )

    result = controller.set_status("Hello")

    assert result.ok
    assert writes == []
    assert edit.text == "Hello"
    assert clipboard[0] == "clipboard before"
    assert events == [
        "restore",
        "window-focus",
        "focus",
        ("sleep", 0.15),
        ("keys", "^a{BACKSPACE}"),
        ("keys", "^v"),
        ("sleep", 0.1),
        "focus",
        ("key", "{ENTER}"),
        ("sleep", 0.25),
    ]



def test_start_or_connect_binds_single_existing_exact_process(monkeypatch):
    cfg = config()
    cfg["camfrog"]["executable"] = r"C:\Camfrog\Camfrog Video Chat.exe"
    controller = CamfrogController(cfg)
    process = SimpleNamespace(pid=321)
    monkeypatch.setattr(controller, "_bound_process", lambda: None)
    monkeypatch.setattr(controller, "available_client_processes", lambda: [process])

    result = controller.start_or_connect()

    assert result.ok
    assert controller.bound_pid == 321
    assert "321" in result.message


def test_start_or_connect_refuses_to_guess_between_existing_pids(monkeypatch):
    cfg = config()
    cfg["camfrog"]["executable"] = r"C:\Camfrog\Camfrog Video Chat.exe"
    controller = CamfrogController(cfg)
    monkeypatch.setattr(controller, "_bound_process", lambda: None)
    monkeypatch.setattr(
        controller,
        "available_client_processes",
        lambda: [SimpleNamespace(pid=101), SimpleNamespace(pid=202)],
    )

    result = controller.start_or_connect()

    assert not result.ok
    assert controller.bound_pid is None
    assert "101" in result.message and "202" in result.message


def test_client_processes_returns_only_bound_pid(monkeypatch):
    cfg = config()
    cfg["camfrog"]["executable"] = r"C:\Camfrog\Camfrog Video Chat.exe"
    controller = CamfrogController(cfg)
    selected = SimpleNamespace(pid=555)
    controller._bound_pid = 555
    monkeypatch.setattr("camfrog.controller.find_process_by_pid", lambda pid, executable_path=None: selected if pid == 555 else None)

    assert controller.client_processes() == [selected]



def test_ensure_running_never_discovers_or_launches_after_disconnect(monkeypatch):
    cfg = config()
    cfg["camfrog"]["executable"] = r"C:\Camfrog\Camfrog Video Chat.exe"
    controller = CamfrogController(cfg)
    controller._session_state = "disconnected"
    monkeypatch.setattr(
        controller,
        "available_client_processes",
        lambda: (_ for _ in ()).throw(AssertionError("ensure_running must not discover a replacement process")),
    )
    monkeypatch.setattr(
        "camfrog.controller.subprocess.Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("ensure_running must not launch Camfrog")),
    )

    result = controller.ensure_running()

    assert not result.ok
    assert controller.bound_pid is None
    assert "Start / Connect" in result.message


def test_lost_bound_pid_stays_disconnected_until_explicit_reconnect(monkeypatch):
    cfg = config()
    cfg["camfrog"]["executable"] = r"C:\Camfrog\Camfrog Video Chat.exe"
    controller = CamfrogController(cfg)
    controller._bound_pid = 777
    controller._session_state = "connected"
    monkeypatch.setattr("camfrog.controller.find_process_by_pid", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        controller,
        "available_client_processes",
        lambda: (_ for _ in ()).throw(AssertionError("lost PID must not trigger automatic discovery")),
    )

    result = controller.ensure_running()

    assert not result.ok
    assert controller.bound_pid is None
    assert controller._session_state == "lost"
    assert "PID was lost" in result.message


def test_start_or_connect_is_serialized():
    controller = CamfrogController(config())
    assert controller._runtime_lock.acquire(blocking=False)
    try:
        result = controller.start_or_connect()
    finally:
        controller._runtime_lock.release()

    assert not result.ok
    assert "already in progress" in result.message
