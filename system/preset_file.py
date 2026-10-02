from __future__ import annotations

import json
from typing import Any


def parse_preset_file_text(text: str) -> list[str]:
    """Parse versioned JSON presets or a plain one-preset-per-line text file."""
    source = str(text or "").strip()
    if not source:
        return []
    if source.startswith(("{", "[")):
        try:
            payload: Any = json.loads(source)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON preset file: {exc.msg}") from exc
        if isinstance(payload, dict):
            version = payload.get("version", 1)
            if version != 1:
                raise ValueError(f"Unsupported preset file version: {version}")
            payload = payload.get("presets")
        if not isinstance(payload, list):
            raise ValueError("Preset file must contain a list of strings")
        if any(not isinstance(item, str) for item in payload):
            raise ValueError("Every preset must be a string")
        return payload
    return source.splitlines()


def format_preset_file_text(presets: list[str], text_only: bool = False) -> str:
    clean = [str(value).strip() for value in presets if str(value).strip()]
    if text_only:
        return "\n".join(clean) + ("\n" if clean else "")
    return json.dumps({"version": 1, "presets": clean}, indent=2, ensure_ascii=False) + "\n"
