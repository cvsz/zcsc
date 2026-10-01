from __future__ import annotations

import os
import re
import string
from dataclasses import dataclass

SENSITIVE = ("password", "token", "session", "cookie", "credential", "auth", "secret")

@dataclass(frozen=True)
class HistoryValue:
    text: str
    source: str
    value_name: str


def _valid(value: str) -> bool:
    value = value.strip().replace("\x00", "")
    if not value or value.isdigit() or "@" in value or len(value) > 160:
        return False
    if re.fullmatch(r"[0-9A-Fa-f]{24,}", value):
        return False
    if any(ord(char) < 32 and char not in "\t" for char in value):
        return False
    printable = sum(char in string.printable or ord(char) > 127 for char in value)
    return printable / max(1, len(value)) > 0.9


def _extract(value):
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return re.split(r"[\r\n|;]+", value)
    if isinstance(value, (bytes, bytearray)):
        output = []
        raw = bytes(value)
        for encoding in ("utf-16le", "utf-8", "latin1"):
            try:
                decoded = raw.decode(encoding, errors="ignore")
                output += re.split(r"[\r\n|;\x00]+", decoded)
            except Exception:
                pass
        return output
    return []


def read_camfrog_custom_statuses():
    if os.name != "nt":
        return []
    import winreg
    found = []
    seen = set()
    roots = [r"Software\Camfrog"]
    views = [winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY]

    def walk(hive, path, view):
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ | view)
        except OSError:
            return
        try:
            index = 0
            while True:
                try:
                    name, value, _value_type = winreg.EnumValue(key, index)
                    index += 1
                except OSError:
                    break
                combined = (path + "\\" + name).casefold()
                if any(term in combined for term in SENSITIVE):
                    continue
                if "status" not in combined and "custom" not in combined:
                    continue
                for candidate in _extract(value):
                    text = str(candidate).strip()
                    folded = text.casefold()
                    if _valid(text) and folded not in seen:
                        seen.add(folded)
                        found.append(HistoryValue(text, path, name))
            child_index = 0
            while True:
                try:
                    child = winreg.EnumKey(key, child_index)
                    child_index += 1
                except OSError:
                    break
                walk(hive, path + "\\" + child, view)
        finally:
            winreg.CloseKey(key)

    for view in views:
        for root in roots:
            walk(winreg.HKEY_CURRENT_USER, root, view)
    return found


def merge_presets(existing, history):
    output = []
    seen = set()
    values = list(existing) + [item.text if hasattr(item, "text") else str(item) for item in history]
    for item in values:
        value = str(item).strip()
        folded = value.casefold()
        if value and folded not in seen:
            seen.add(folded)
            output.append(value)
    return output
