from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Iterable, Sequence

log = logging.getLogger(__name__)

ROOT_KEYS = (r"Software\Camfrog",)
RELEVANT_TERMS = ("status", "custom")
SENSITIVE_TERMS = (
    "password", "passwd", "token", "session", "cookie", "secret",
    "credential", "auth", "oauth", "license", "serial",
)

@dataclass(frozen=True)
class RegistryHistoryItem:
    text: str
    source: str
    value_name: str
    value_type: int | None = None

@dataclass(frozen=True)
class RegistryStatusResult:
    statuses: list[str]
    sources: list[str]
    scanned_keys: int = 0
    candidate_values: int = 0
    history: list[RegistryHistoryItem] | None = None

def _clean_status(value: str) -> str | None:
    value = value.replace("\x00", "").strip()
    if not value or len(value) > 160:
        return None
    if value.casefold() in {
        "items", "statevalue", "custom status list", "custom_status_list",
        "status", "custom status", "profile", "default",
    }:
        return None
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value):
        return None
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        return None
    if re.fullmatch(r"[0-9A-Fa-f]{24,}", value):
        return None
    if any((ord(ch) < 32 and ch not in "\t") for ch in value):
        return None
    if re.search(r"\\x[0-9A-Fa-f]{2}", value):
        return None
    printable = sum(ch.isprintable() for ch in value)
    if printable / max(1, len(value)) < 0.98:
        return None
    alnum_space = sum(ch.isalnum() or ch.isspace() for ch in value)
    punctuation = sum(not (ch.isalnum() or ch.isspace()) for ch in value)
    if len(value) >= 8 and alnum_space / len(value) < 0.55:
        return None
    if len(value) >= 12 and not any(ch.isspace() for ch in value) and punctuation >= 3:
        return None
    if len(value) < 3:
        return None
    if len(value) <= 6 and not any(ch.isspace() for ch in value):
        letters = sum(ch.isalpha() for ch in value)
        if punctuation > 0 or letters < max(2, len(value) - 1):
            return None
    if not any(ch.isalpha() for ch in value):
        return None
    return value

def _carve_utf16_strings(data: bytes) -> list[str]:
    out: list[str] = []
    for offset in (0, 1):
        chunk = data[offset:]
        for m in re.finditer(rb"(?:[\x20-\x7e]\x00){3,160}", chunk):
            cleaned = _clean_status(m.group(0).decode("utf-16-le", errors="ignore"))
            if cleaned:
                out.append(cleaned)
        usable = chunk[: len(chunk) - (len(chunk) % 2)]
        text = usable.decode("utf-16-le", errors="ignore")
        for part in re.split(r"[\x00-\x1f]+", text):
            cleaned = _clean_status(part)
            if cleaned:
                out.append(cleaned)
    return out

def _carve_ascii_strings(data: bytes) -> list[str]:
    out: list[str] = []
    for m in re.finditer(rb"[\x20-\x7e]{3,160}", data):
        try:
            text = m.group(0).decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            continue
        cleaned = _clean_status(text)
        if cleaned:
            out.append(cleaned)
    return out

def _strings_from_binary(data: bytes) -> list[str]:
    values = [*_carve_utf16_strings(data), *_carve_ascii_strings(data)]
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            out.append(value)
    return out

def extract_status_strings(value, value_type: int | None = None) -> list[str]:
    values: list[str] = []
    if isinstance(value, (list, tuple)):
        values.extend(str(x) for x in value)
    elif isinstance(value, bytes):
        values.extend(_strings_from_binary(value))
    elif isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    values.extend(str(x) for x in parsed)
                else:
                    values.append(text)
            except Exception:
                values.extend(re.split(r"[\r\n|;]+", text))
        else:
            values.extend(re.split(r"[\r\n|;]+", text))
    elif value is not None:
        values.append(str(value))
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        cleaned = _clean_status(item)
        if cleaned and cleaned.casefold() not in seen:
            seen.add(cleaned.casefold())
            result.append(cleaned)
    return result

def merge_presets(existing: Sequence[str], imported: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in [*existing, *list(imported)]:
        cleaned = _clean_status(str(value))
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out

def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    folded = text.casefold()
    return any(term in folded for term in terms)

def read_camfrog_custom_statuses(max_depth: int = 12) -> RegistryStatusResult:
    if os.name != "nt":
        return RegistryStatusResult([], [], 0, 0, [])
    import winreg
    found: list[str] = []
    sources: list[str] = []
    history: list[RegistryHistoryItem] = []
    seen_status: set[str] = set()
    visited: set[tuple[str, int]] = set()
    scanned_keys = 0
    candidate_values = 0
    views = [0]
    for flag_name in ("KEY_WOW64_64KEY", "KEY_WOW64_32KEY"):
        flag = getattr(winreg, flag_name, 0)
        if flag and flag not in views:
            views.append(flag)
    def walk(path: str, view_flag: int, depth: int) -> None:
        nonlocal scanned_keys, candidate_values
        if depth > max_depth:
            return
        token = (path.casefold(), view_flag)
        if token in visited:
            return
        visited.add(token)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ | view_flag) as key:
                scanned_keys += 1
                path_relevant = _contains_any(path, RELEVANT_TERMS)
                subkey_count, value_count, _ = winreg.QueryInfoKey(key)
                for i in range(value_count):
                    try:
                        name, value, value_type = winreg.EnumValue(key, i)
                    except OSError:
                        continue
                    name_text = name or "(Default)"
                    if _contains_any(name_text, SENSITIVE_TERMS):
                        continue
                    if not (path_relevant or _contains_any(name_text, RELEVANT_TERMS)):
                        continue
                    candidate_values += 1
                    source = f"HKCU\\{path} [{name_text}]"
                    for status in extract_status_strings(value, value_type):
                        marker = status.casefold()
                        if marker in seen_status:
                            continue
                        seen_status.add(marker)
                        found.append(status)
                        sources.append(source)
                        history.append(RegistryHistoryItem(status, source, name_text, value_type))
                for i in range(subkey_count):
                    try:
                        child = winreg.EnumKey(key, i)
                    except OSError:
                        continue
                    walk(path + "\\" + child, view_flag, depth + 1)
        except (FileNotFoundError, PermissionError, OSError):
            return
    for view in views:
        for root in ROOT_KEYS:
            walk(root, view, 0)
    log.info("Camfrog registry scan: keys=%d candidates=%d statuses=%d", scanned_keys, candidate_values, len(found))
    return RegistryStatusResult(found, sources, scanned_keys, candidate_values, history)
