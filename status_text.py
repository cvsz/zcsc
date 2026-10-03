from __future__ import annotations

import unicodedata


def normalize_newlines(value: str) -> str:
    """Normalize all newline spellings to LF for comparisons/storage."""
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def compose_two_lines(lines) -> str:
    """Deprecated legacy helper; preserve every supplied message row."""
    values = [normalize_newlines(str(x).replace("\x00", "")).replace("\n", " ") for x in list(lines)]
    while values and not values[-1]:
        values.pop()
    return "\r\n".join(values)


def comparable_status(value: str) -> str:
    """Canonical form for read-back verification across Win32/UIA newline styles."""
    without_nuls = normalize_newlines(value).replace("\x00", "")
    return unicodedata.normalize("NFC", without_nuls).strip()
