import sys
from types import ModuleType, SimpleNamespace

import system.single_instance as single_instance


def install_fake_windows(monkeypatch, handle, last_error):
    closed = []
    api = ModuleType("win32api")
    api.GetLastError = lambda: last_error
    api.CloseHandle = lambda value: closed.append(value)
    event = ModuleType("win32event")
    event.CreateMutex = lambda _security, _initial_owner, _name: handle
    errors = ModuleType("winerror")
    errors.ERROR_ALREADY_EXISTS = 183
    errors.ERROR_SUCCESS = 0
    monkeypatch.setattr(single_instance, "os", SimpleNamespace(name="nt"))
    monkeypatch.setitem(sys.modules, "win32api", api)
    monkeypatch.setitem(sys.modules, "win32event", event)
    monkeypatch.setitem(sys.modules, "winerror", errors)
    return closed


def test_active_named_mutex_is_detected_and_duplicate_handle_closed(monkeypatch):
    handle = object()
    closed = install_fake_windows(monkeypatch, handle, 183)
    instance = single_instance.SingleInstance()

    assert instance.acquire() is False
    assert instance._handle is None
    assert closed == [handle]


def test_create_mutex_failure_does_not_allow_an_unprotected_second_instance(monkeypatch):
    install_fake_windows(monkeypatch, None, 5)
    instance = single_instance.SingleInstance()

    try:
        instance.acquire()
    except OSError as exc:
        assert exc.errno == 5
    else:
        raise AssertionError("failed mutex creation must fail closed")


def test_new_kernel_mutex_can_be_acquired_after_prior_process_exit(monkeypatch):
    handle = object()
    closed = install_fake_windows(monkeypatch, handle, 0)
    instance = single_instance.SingleInstance()

    assert instance.acquire() is True
    assert instance._handle is handle
    instance.release()
    assert closed == [handle]


def test_successful_mutex_handle_is_accepted_despite_unrelated_stale_last_error(monkeypatch):
    handle = object()
    install_fake_windows(monkeypatch, handle, 5)
    instance = single_instance.SingleInstance()

    assert instance.acquire() is True
    assert instance._handle is handle


def test_non_windows_runtime_keeps_platform_guard(monkeypatch):
    monkeypatch.setattr(single_instance, "os", SimpleNamespace(name="posix"))

    assert single_instance.SingleInstance().acquire() is True
