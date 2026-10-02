import sys
from types import SimpleNamespace

from camfrog import background_win32


def test_commit_status_sends_exactly_one_enter_to_the_target_edit(monkeypatch):
    events = []
    monkeypatch.setitem(sys.modules, "win32con", SimpleNamespace(VK_RETURN=0x000D))
    monkeypatch.setattr(background_win32, "_send_key", lambda hwnd, key: events.append((hwnd, key)))
    monkeypatch.setattr(background_win32.time, "sleep", lambda _seconds: None)

    background_win32._commit_status_input(33)

    assert events == [(33, 0x000D)]
