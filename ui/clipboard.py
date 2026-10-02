"""Clipboard helpers that preserve Unicode text across Tk editors."""

from __future__ import annotations

from typing import Any


class ClipboardTextUnavailable(RuntimeError):
    """Raised when the clipboard has no Unicode text representation."""


def _windows_clipboard_api() -> tuple[Any, int] | None:
    """Return Win32 clipboard APIs on Windows and None elsewhere."""
    import sys

    if sys.platform != "win32":
        return None

    import win32clipboard
    from win32con import CF_UNICODETEXT

    return win32clipboard, CF_UNICODETEXT


def get_clipboard_text(root, *, windows_api: tuple[Any, int] | None = None) -> str:
    """Read clipboard text without passing Windows text through an ANSI code page."""
    api = windows_api if windows_api is not None else _windows_clipboard_api()
    if api is None:
        return root.clipboard_get()

    clipboard, unicode_text_format = api
    clipboard.OpenClipboard()
    try:
        if not clipboard.IsClipboardFormatAvailable(unicode_text_format):
            raise ClipboardTextUnavailable("Clipboard does not contain Unicode text")
        value = clipboard.GetClipboardData(unicode_text_format)
        if isinstance(value, bytes):
            value = value.decode("utf-16-le").rstrip("\x00")
        if not isinstance(value, str):
            raise ClipboardTextUnavailable("Clipboard Unicode text has an unsupported type")
        return value
    finally:
        clipboard.CloseClipboard()


def set_clipboard_text(root, value: str, *, windows_api: tuple[Any, int] | None = None) -> None:
    """Write clipboard text as Unicode on Windows and through Tk elsewhere."""
    if not isinstance(value, str):
        raise TypeError("Clipboard text must be a string")

    api = windows_api if windows_api is not None else _windows_clipboard_api()
    if api is None:
        root.clipboard_clear()
        root.clipboard_append(value)
        return

    clipboard, unicode_text_format = api
    clipboard.OpenClipboard()
    try:
        clipboard.EmptyClipboard()
        clipboard.SetClipboardData(unicode_text_format, value)
    finally:
        clipboard.CloseClipboard()
