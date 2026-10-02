from types import SimpleNamespace
import sys

import pytest

from camfrog import background_win32


def test_status_input_settle_is_reduced_by_0_3_seconds():
    assert background_win32.STATUS_INPUT_SETTLE_SECONDS == 0.45


def test_background_scan_marks_equal_status_control_candidates_ambiguous(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "win32gui",
        SimpleNamespace(GetWindowRect=lambda _hwnd: (0, 0, 1000, 800)),
    )
    monkeypatch.setattr(background_win32, "_children", lambda _hwnd: [21, 22])
    monkeypatch.setattr(background_win32, "_class_name", lambda _hwnd: "CComboBoxTS")
    monkeypatch.setattr(background_win32, "_read_text", lambda _hwnd: "")

    with pytest.raises(background_win32.AmbiguousNativeControlError, match="Multiple Camfrog status controls"):
        background_win32._find_camfrog_status_combo(11)


def test_background_api_preserves_ambiguity_as_a_fail_closed_result(monkeypatch):
    monkeypatch.setattr(background_win32, "_require_windows", lambda: None)
    monkeypatch.setitem(sys.modules, "win32con", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "win32gui", SimpleNamespace(IsWindow=lambda _hwnd: True))
    monkeypatch.setattr(
        background_win32,
        "_find_camfrog_status_combo",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            background_win32.AmbiguousNativeControlError("multiple status controls")
        ),
    )

    result = background_win32.set_status_background(11, 0.5, 0.19, "hello")

    assert not result.ok
    assert result.ambiguous
    assert "multiple status controls" in result.message


def _install_background_send_mocks(monkeypatch, events, verify_results):
    constants = SimpleNamespace(
        WM_SETTEXT=0x000C,
        WM_PASTE=0x0302,
        VK_BACK=0x0008,
        VK_RETURN=0x000D,
    )
    monkeypatch.setitem(sys.modules, "win32con", constants)
    monkeypatch.setattr(background_win32, "_find_edit_candidate", lambda _combo: 22)
    monkeypatch.setattr(
        background_win32,
        "_send_timeout",
        lambda hwnd, msg, wparam=0, lparam=0, **kwargs: events.append(("send", hwnd, msg, wparam)),
    )
    monkeypatch.setattr(background_win32, "_notify_edit_parent", lambda hwnd: events.append(("edit-notify", hwnd)))
    monkeypatch.setattr(
        background_win32,
        "_notify_combo_parent",
        lambda parent, combo, **kwargs: events.append(("parent-notify", parent, combo, kwargs)),
    )
    monkeypatch.setattr(
        background_win32,
        "_send_key",
        lambda hwnd, key, **kwargs: events.append(("key", hwnd, key)),
    )
    monkeypatch.setattr(
        background_win32,
        "_paste_text",
        lambda hwnd, value: events.append(("paste", hwnd, value)),
    )
    def verify(*_args):
        result = next(verify_results)
        events.append(("verify", *result))
        return result

    monkeypatch.setattr(background_win32, "_verify_combo_value", verify)
    monkeypatch.setattr(background_win32.time, "sleep", lambda seconds: events.append(("sleep", seconds)))


def test_native_status_waits_for_input_before_enter(monkeypatch):
    events = []
    _install_background_send_mocks(monkeypatch, events, iter([(True, "hello"), (True, "hello")]))

    result = background_win32._set_native_combo_text(11, 22, "hello")

    assert result.ok
    text_set = next(i for i, event in enumerate(events) if event[:3] == ("send", 22, 0x000C))
    field_verified = next(i for i, event in enumerate(events) if event == ("verify", True, "hello"))
    input_settle = events.index(("sleep", background_win32.STATUS_INPUT_SETTLE_SECONDS))
    enter = next(i for i, event in enumerate(events) if event == ("key", 22, 0x000D))
    assert text_set < field_verified < input_settle < enter


def test_native_status_uses_clipboard_paste_fallback_before_enter(monkeypatch):
    events = []
    _install_background_send_mocks(monkeypatch, events, iter([(False, "old"), (True, "ab")]))

    result = background_win32._set_native_combo_text(11, 22, "ab")

    assert result.ok
    paste_index = events.index(("paste", 22, "ab"))
    field_verified = events.index(("verify", True, "ab"))
    enter = events.index(("key", 22, 0x000D))
    assert events.index(("verify", False, "old")) < paste_index < field_verified < enter
    assert not any(event[0] == "send" and event[2] == 0x0102 for event in events)


def test_paste_helper_restores_clipboard_and_uses_wm_paste(monkeypatch):
    events = []
    clipboard = ["clipboard before"]
    pyperclip = SimpleNamespace(
        paste=lambda: clipboard[0],
        copy=lambda value: clipboard.__setitem__(0, value),
    )
    constants = SimpleNamespace(WM_PASTE=0x0302, VK_BACK=0x0008)
    monkeypatch.setitem(sys.modules, "pyperclip", pyperclip)
    monkeypatch.setitem(sys.modules, "win32con", constants)
    monkeypatch.setattr(
        background_win32,
        "_send_key",
        lambda hwnd, key, **kwargs: events.append(("key", hwnd, key, kwargs.get("ctrl", False))),
    )
    monkeypatch.setattr(
        background_win32,
        "_send_timeout",
        lambda hwnd, msg, wparam=0, lparam=0, **kwargs: events.append(("send", hwnd, msg, wparam, lparam)),
    )

    background_win32._paste_text(22, "new text")

    assert events == [
        ("key", 22, ord("A"), True),
        ("key", 22, constants.VK_BACK, False),
        ("send", 22, constants.WM_PASTE, 0, 0),
    ]
    assert clipboard[0] == "clipboard before"


def test_native_status_skips_commit_if_field_rejects_text(monkeypatch):
    events = []
    _install_background_send_mocks(monkeypatch, events, iter([(False, "old"), (False, "old")]))

    result = background_win32._set_native_combo_text(11, 22, "new")

    assert not result.ok
    assert result.observed_value == "old"
    assert not any(event[0] == "key" and event[2] == 0x000D for event in events)
    assert not any(event[0] == "click" for event in events)


def test_native_status_does_not_retype_when_enter_consumes_the_editor_value(monkeypatch):
    events = []
    _install_background_send_mocks(monkeypatch, events, iter([(True, "hello"), (False, "")]))

    result = background_win32._set_native_combo_text(11, 22, "hello")

    assert result.ok
    assert result.verified
    assert result.observed_value == "hello"
    enter_events = [event for event in events if event[0] == "key" and event[2] == 0x000D]
    assert enter_events == [("key", 22, 0x000D)]
    assert not any(event[:3] == ("send", 22, 0x0102) for event in events)
    assert not any(event[0] == "key" and event[2] == 0x0008 for event in events)


def test_background_edit_fallback_does_not_click_or_retype_after_enter(monkeypatch):
    events = []
    constants = SimpleNamespace(
        VK_RETURN=0x000D,
        WM_SETTEXT=0x000C,
    )
    win32gui = SimpleNamespace(
        IsWindow=lambda hwnd: hwnd == 11,
        GetWindowPlacement=lambda _hwnd: (0, 0, 0, 0, (0, 0, 100, 100)),
        ScreenToClient=lambda *_args: (_ for _ in ()).throw(AssertionError("fallback click must not run")),
    )
    monkeypatch.setitem(sys.modules, "win32con", constants)
    monkeypatch.setitem(sys.modules, "win32gui", win32gui)
    monkeypatch.setattr(background_win32, "_require_windows", lambda: None)
    monkeypatch.setattr(background_win32, "_find_camfrog_status_combo", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(background_win32, "_smallest_child_at_point", lambda *_args: 22)
    monkeypatch.setattr(background_win32, "_find_edit_candidate", lambda _hwnd: 33)
    monkeypatch.setattr(
        background_win32,
        "_send_timeout",
        lambda hwnd, message, *_args, **_kwargs: events.append(("send", hwnd, message)),
    )
    monkeypatch.setattr(background_win32, "_read_text", lambda hwnd: events.append(("read", hwnd)) or "hello")
    monkeypatch.setattr(background_win32, "_send_key", lambda hwnd, key, **_kwargs: events.append(("key", hwnd, key)))
    monkeypatch.setattr(background_win32.time, "sleep", lambda _seconds: None)

    result = background_win32.set_status_background(11, 0.5, 0.19, "hello")

    assert result.ok and result.verified
    assert events == [
        ("send", 33, constants.WM_SETTEXT),
        ("read", 33),
        ("key", 33, constants.VK_RETURN),
    ]


def test_verified_uia_commit_sends_one_enter_without_rewriting_or_extra_commit(monkeypatch):
    events = []
    monkeypatch.setattr(background_win32, "_require_windows", lambda: None)
    monkeypatch.setitem(sys.modules, "win32con", SimpleNamespace(VK_RETURN=0x000D))
    monkeypatch.setitem(sys.modules, "win32gui", SimpleNamespace(IsWindow=lambda hwnd: hwnd in {11, 22, 33}))
    monkeypatch.setattr(background_win32, "_send_key", lambda hwnd, key: events.append(("key", hwnd, key)))
    monkeypatch.setattr(background_win32, "_send_timeout", lambda *_args, **_kwargs: events.append(("write",)))
    monkeypatch.setattr(background_win32, "_notify_combo_parent", lambda *_args, **_kwargs: events.append(("notify",)))
    monkeypatch.setattr(background_win32.time, "sleep", lambda _seconds: None)

    result = background_win32.commit_verified_ui_status_background(11, 22, 33, "hello")

    assert result.ok
    assert events == [("key", 33, 0x000D)]
    assert "not independently confirmed" in result.message
