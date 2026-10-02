from pathlib import Path

import pytest

from ui.clipboard import ClipboardTextUnavailable, get_clipboard_text, set_clipboard_text


class FakeWin32Clipboard:
    def __init__(self, text=None, available=True):
        self.text = text
        self.available = available
        self.calls = []

    def OpenClipboard(self):
        self.calls.append(("open",))

    def CloseClipboard(self):
        self.calls.append(("close",))

    def IsClipboardFormatAvailable(self, format_id):
        self.calls.append(("available", format_id))
        return self.available

    def GetClipboardData(self, format_id):
        self.calls.append(("get", format_id))
        return self.text

    def EmptyClipboard(self):
        self.calls.append(("empty",))

    def SetClipboardData(self, format_id, value):
        self.calls.append(("set", format_id, value))
        self.text = value


class FakeTkClipboard:
    def __init__(self):
        self.calls = []

    def clipboard_get(self):
        self.calls.append(("get",))
        return "ANSI fallback must not be used"

    def clipboard_clear(self):
        self.calls.append(("clear",))

    def clipboard_append(self, value):
        self.calls.append(("append", value))


def test_windows_clipboard_reads_thai_and_other_unicode_from_unicode_format():
    text = "เหี้ย ภาษาไทย 🧡"
    clipboard = FakeWin32Clipboard(text)

    value = get_clipboard_text(FakeTkClipboard(), windows_api=(clipboard, 13))

    assert value == text
    assert ("get", 13) in clipboard.calls
    assert clipboard.calls[-1] == ("close",)


def test_windows_clipboard_does_not_fall_back_to_ansi_text():
    clipboard = FakeWin32Clipboard(available=False)
    root = FakeTkClipboard()

    with pytest.raises(ClipboardTextUnavailable):
        get_clipboard_text(root, windows_api=(clipboard, 13))

    assert ("get",) not in root.calls
    assert clipboard.calls[-1] == ("close",)


def test_windows_clipboard_copy_writes_unicode_format():
    text = "คัดลอกข้อความไทย"
    clipboard = FakeWin32Clipboard()

    set_clipboard_text(FakeTkClipboard(), text, windows_api=(clipboard, 13))

    assert ("set", 13, text) in clipboard.calls
    assert clipboard.calls[-1] == ("close",)


def test_clipboard_helpers_use_tk_when_windows_api_is_not_provided(monkeypatch):
    import ui.clipboard as clipboard_helpers

    monkeypatch.setattr(clipboard_helpers, "_windows_clipboard_api", lambda: None)
    root = FakeTkClipboard()

    assert get_clipboard_text(root) == "ANSI fallback must not be used"
    set_clipboard_text(root, "ข้อความ")

    assert ("clear",) in root.calls
    assert ("append", "ข้อความ") in root.calls


def test_clipboard_bindings_do_not_use_bind_all_or_virtual_paste():
    source = Path('ui/dashboard.py').read_text(encoding='utf-8')
    block = source[source.index('    def _install_clipboard_shortcuts'):source.index('    def _build', source.index('    def _install_clipboard_shortcuts'))]
    assert 'self.bind_all(' not in block
    assert 'event_generate' not in block
    assert 'bind_class' in block
    assert 'get_clipboard_text(self)' in block
    assert 'set_clipboard_text(self, selected)' in block


def test_clipboard_selection_paste_replaces_selected_range_at_its_start():
    source = Path('ui/dashboard.py').read_text(encoding='utf-8')
    block = source[source.index('    def _clipboard_action'):source.index('    def _build')]
    assert 'widget.index("sel.first")' in block
    assert 'widget.index("sel.last")' in block
    assert 'widget.mark_set("insert", first)' in block
    assert 'widget.icursor(first)' in block


def test_style_callback_has_real_preview_method():
    source = Path('ui/dashboard.py').read_text(encoding='utf-8')
    assert 'def _refresh_status_preview' in source
    assert 'self._refresh_status_preview()' in source
