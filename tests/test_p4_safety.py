from __future__ import annotations

import sys
import threading
import time
from datetime import datetime, timedelta, tzinfo
from types import ModuleType, SimpleNamespace

import pytest

from automation.schedule import rotation_is_allowed
from camfrog.controller import CamfrogController, ChangeResult


class FakeClock:
    def __init__(self, initial: float = 100.0):
        self.value = initial
        self.sleeps: list[float] = []
        self._lock = threading.Lock()

    def monotonic(self) -> float:
        with self._lock:
            return self.value

    def sleep(self, seconds: float) -> None:
        with self._lock:
            self.sleeps.append(seconds)
            self.value += seconds

    def now_local(self) -> datetime:
        return datetime.now().astimezone()


class FakeEasternTime(tzinfo):
    """Small deterministic DST fixture, independent of the host tz database."""

    def utcoffset(self, value):
        if value is None:
            return timedelta(hours=-5)
        if value.month == 3 and value.day == 8 and value.hour >= 3:
            return timedelta(hours=-4)
        if value.month == 11 and value.day == 1 and value.hour == 1 and value.fold == 0:
            return timedelta(hours=-4)
        return timedelta(hours=-5)

    def dst(self, value):
        return self.utcoffset(value) - timedelta(hours=-5)


def _config() -> dict:
    return {
        "camfrog": {"executable": ""},
        "target": {"background_enabled": False, "fallback_enabled": False},
        "status": {"presets": []},
        "advanced": {"max_status_length": 160, "minimum_interval_seconds": 5},
    }


def _install_uia_controller(
    monkeypatch,
    *,
    foreground_pid=123,
    mutate_on_commit_focus=False,
    block_first_enter=None,
    clock=None,
    foreground_ready_after_check=None,
    foreground_switch_on_check=None,
):
    events = []
    clipboard = ["clipboard before"]
    foreground = [foreground_pid]
    foreground_checks = [0]
    edit = None

    class Edit:
        handle = 33
        element_info = SimpleNamespace(class_name="CEdit4ComboInnerTS", control_type="Edit")

        def __init__(self):
            self.text = "old draft"
            self.focus_count = 0

        def set_focus(self):
            self.focus_count += 1
            events.append("edit-focus")
            if mutate_on_commit_focus and self.focus_count == 2:
                self.text = "changed after verification"

        def window_text(self):
            return self.text

        def type_keys(self, keys):
            timestamp = clock.monotonic() if clock is not None else None
            events.append(("key", keys, self.text, timestamp))
            if keys == "{ENTER}" and block_first_enter is not None and self.text == "first":
                block_first_enter[0].set()
                block_first_enter[1].wait(timeout=3)
                if clock is not None:
                    clock.sleep(3.0)

    edit = Edit()

    class Combo:
        handle = 22

        def descendants(self):
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
    def process_id_for(hwnd):
        if hwnd in {11, 22, 33}:
            return (1, 123)
        return (1, foreground[0])

    def get_foreground():
        foreground_checks[0] += 1
        if foreground_ready_after_check and foreground_checks[0] >= foreground_ready_after_check:
            foreground[0] = 123
        if foreground_switch_on_check and foreground_checks[0] >= foreground_switch_on_check:
            foreground[0] = 999
        return 99

    monkeypatch.setitem(
        sys.modules,
        "win32gui",
        SimpleNamespace(
            GetForegroundWindow=get_foreground,
            GetWindowThreadProcessId=process_id_for,
            IsWindow=lambda _hwnd: True,
        ),
    )

    controller = CamfrogController(_config())
    controller.clock = clock
    controller.ensure_running = lambda: ChangeResult(True, "running")
    controller.find_window = lambda: Window()
    controller._find_target = lambda _window: Combo()
    controller.native_profile_info = lambda: {"matched": True, "name": "fake"}
    return controller, edit, events, clipboard, foreground


def test_foreground_uia_send_aborts_if_another_process_owns_foreground(monkeypatch):
    clock = FakeClock()
    controller, _edit, events, _clipboard, _foreground = _install_uia_controller(
        monkeypatch, foreground_pid=999, clock=clock
    )

    result = controller.set_status("new status")

    assert not result.ok
    assert "Enter was not sent" in result.message
    assert not any(event[0] == "key" and event[1] == "{ENTER}" for event in events)
    assert clock.value <= 101.0


def test_foreground_uia_send_rechecks_edit_text_immediately_before_enter(monkeypatch):
    controller, edit, events, _clipboard, _foreground = _install_uia_controller(
        monkeypatch, mutate_on_commit_focus=True, clock=FakeClock()
    )

    result = controller.set_status("new status")

    assert not result.ok
    assert "Enter was not sent" in result.message
    assert edit.text == "changed after verification"
    assert not any(event[0] == "key" and event[1] == "{ENTER}" for event in events)


def test_foreground_uia_send_polls_until_camfrog_owns_foreground(monkeypatch):
    clock = FakeClock()
    controller, _edit, events, _clipboard, _foreground = _install_uia_controller(
        monkeypatch,
        foreground_pid=999,
        foreground_ready_after_check=2,
        clock=clock,
    )

    result = controller.set_status("new status")

    assert result.ok
    assert clock.value == 100.025
    assert [event[1] for event in events if event[0] == "key"] == ["{ENTER}"]


def test_foreground_uia_send_aborts_if_foreground_changes_after_poll(monkeypatch):
    controller, _edit, events, _clipboard, _foreground = _install_uia_controller(
        monkeypatch,
        foreground_switch_on_check=2,
        clock=FakeClock(),
    )

    result = controller.set_status("new status")

    assert not result.ok
    assert "Enter was not sent" in result.message
    assert not any(event[0] == "key" and event[1] == "{ENTER}" for event in events)


def test_foreground_uia_commit_requires_a_uniquely_identified_edit(monkeypatch):
    controller, _edit, events, _clipboard, _foreground = _install_uia_controller(
        monkeypatch, clock=FakeClock()
    )
    combo = controller._find_target(None)
    combo.descendants = lambda: []
    combo.set_focus = lambda: events.append("combo-focus")
    controller._find_target = lambda _window: combo
    controller.config["target"]["background_enabled"] = False

    result = controller.set_status("new status")

    assert not result.ok
    assert "Edit" in result.message
    assert not any(event[0] == "keys" for event in events)
    assert not any(event[0] == "key" and event[1] == "{ENTER}" for event in events)


def test_concurrent_status_requests_queue_and_send_once_each(monkeypatch):
    release_first = threading.Event()
    first_entered = threading.Event()
    # Use a deterministic clock so the 5-second guard does not slow the stress test.
    clock = FakeClock()
    controller, _edit, events, _clipboard, _foreground = _install_uia_controller(
        monkeypatch,
        block_first_enter=(first_entered, release_first),
        clock=clock,
    )
    results = {}
    requests = ["first"] + [f"status-{index}" for index in range(1, 8)]
    workers = [
        threading.Thread(target=lambda value=value: results.setdefault(value, controller.set_status(value)))
        for value in requests
    ]
    workers[0].start()
    assert first_entered.wait(timeout=1)
    for worker in workers[1:]:
        worker.start()
    time.sleep(0.03)
    assert list(results) == []
    release_first.set()
    for worker in workers:
        worker.join(timeout=3)

    assert not any(worker.is_alive() for worker in workers)
    assert set(results) == set(requests)
    assert all(result.ok for result in results.values())
    enters = [event for event in events if event[0] == "key" and event[1] == "{ENTER}"]
    assert len(enters) == len(requests)
    assert {event[2] for event in enters} == set(requests)
    assert all(right[3] - left[3] >= 5.0 for left, right in zip(enters, enters[1:]))


def test_rotation_window_accepts_timezone_aware_spring_forward_times():
    eastern = FakeEasternTime()
    rotation = {"schedule_enabled": True, "schedule_start": "01:30", "schedule_end": "03:30"}

    assert rotation_is_allowed(rotation, datetime(2026, 3, 8, 1, 59, tzinfo=eastern))
    assert rotation_is_allowed(rotation, datetime(2026, 3, 8, 3, 0, tzinfo=eastern))
    assert not rotation_is_allowed(rotation, datetime(2026, 3, 8, 3, 30, tzinfo=eastern))


def test_rotation_window_accepts_both_fall_back_folds_and_midnight_wrap():
    eastern = FakeEasternTime()
    rotation = {"schedule_enabled": True, "schedule_start": "01:15", "schedule_end": "01:45"}
    first_fold = datetime(2026, 11, 1, 1, 30, tzinfo=eastern, fold=0)
    second_fold = datetime(2026, 11, 1, 1, 30, tzinfo=eastern, fold=1)
    overnight = {"quiet_hours_enabled": True, "quiet_start": "22:00", "quiet_end": "06:00"}

    assert rotation_is_allowed(rotation, first_fold)
    assert rotation_is_allowed(rotation, second_fold)
    assert not rotation_is_allowed(overnight, datetime(2026, 11, 2, 0, 30, tzinfo=eastern))
    assert rotation_is_allowed(overnight, datetime(2026, 11, 2, 6, 0, tzinfo=eastern))


def test_rotation_worker_passes_a_timezone_aware_local_datetime(monkeypatch):
    from automation import rotation

    checked = threading.Event()
    observed = []

    def capture(_schedule, now):
        observed.append(now)
        checked.set()
        return False

    monkeypatch.setattr(rotation, "rotation_is_allowed", capture)
    worker = rotation.RotationWorker(lambda _value: None, clock=FakeClock())
    worker.start(["one"], 60, "sequential", schedule={"schedule_enabled": True})
    try:
        assert checked.wait(timeout=1)
    finally:
        worker.stop()

    assert observed[0].tzinfo is not None


def test_dpi_awareness_uses_per_monitor_v2_and_checks_existing_context(monkeypatch):
    from system import dpi_awareness

    monkeypatch.setattr(dpi_awareness, "_PER_MONITOR_V2_READY", None)

    class Api:
        def __init__(self, set_result, current_context):
            self.set_result = set_result
            self.current_context = current_context
            self.requested_contexts = []

        def set_process_dpi_awareness_context(self, context):
            self.requested_contexts.append(context)
            return self.set_result

        def get_thread_dpi_awareness_context(self):
            return self.current_context

        def are_dpi_awareness_contexts_equal(self, actual, expected):
            return actual == expected

    api = Api(False, dpi_awareness.DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)

    assert dpi_awareness.configure_process_dpi_awareness(api=api)
    assert api.requested_contexts == [dpi_awareness.DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2]
    assert dpi_awareness.per_monitor_v2_ready()


def test_dpi_awareness_rejects_an_existing_non_v2_context(monkeypatch):
    from system import dpi_awareness

    monkeypatch.setattr(dpi_awareness, "_PER_MONITOR_V2_READY", None)

    class Api:
        def set_process_dpi_awareness_context(self, _context):
            return False

        def get_thread_dpi_awareness_context(self):
            return -3

        def are_dpi_awareness_contexts_equal(self, actual, expected):
            return actual == expected

    assert not dpi_awareness.configure_process_dpi_awareness(api=Api())
    assert not dpi_awareness.per_monitor_v2_ready()


def test_coordinate_fallback_is_blocked_without_verified_per_monitor_v2(monkeypatch):
    from system import dpi_awareness

    monkeypatch.setattr(dpi_awareness, "_PER_MONITOR_V2_READY", False)
    controller = CamfrogController(_config())

    with pytest.raises(RuntimeError, match="per-monitor v2 DPI awareness"):
        controller._coordinate_fallback(SimpleNamespace(handle=11), "status")


def test_send_slot_uses_monotonic_clock_and_waits_only_the_remaining_interval(monkeypatch):
    clock = FakeClock(initial=200.0)
    controller = CamfrogController(_config(), clock=clock)
    controller._last_send_monotonic = 197.0

    controller._wait_for_send_slot()

    assert clock.sleeps == [2.0]
    assert controller._last_send_monotonic == 202.0
    controller._record_send_time()
    assert controller._last_send_monotonic == 202.0


def test_startup_sets_dpi_awareness_before_dashboard_import(monkeypatch):
    import app
    import system.config_store as config_store
    import system.logging_setup as logging_setup
    import system.single_instance as single_instance

    events = []

    class Store:
        def ensure_defaults(self):
            events.append("defaults")

        def load(self):
            return {"ui": {"language": "EN"}}

    class Instance:
        def acquire(self):
            return True

        def release(self):
            events.append("release")

    class App:
        def __init__(self, store):
            events.append("dashboard")

        def title(self, _value):
            pass

        def mainloop(self):
            events.append("mainloop")

    dashboard = ModuleType("ui.dashboard")
    dashboard.AppUI = App
    monkeypatch.setitem(sys.modules, "ui.dashboard", dashboard)
    monkeypatch.setattr(logging_setup, "configure_logging", lambda: None)
    monkeypatch.setattr(config_store, "ConfigStore", Store)
    monkeypatch.setattr(single_instance, "SingleInstance", Instance)
    monkeypatch.setattr(app, "configure_process_dpi_awareness", lambda: events.append("dpi") or True, raising=False)

    assert app.main() == 0
    assert events.index("dpi") < events.index("dashboard")
