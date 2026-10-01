from __future__ import annotations

import copy
import json
import os
import shutil
import time
from pathlib import Path

DEFAULT_CONFIG = {
    "schema_version": 2,
    "camfrog": {"executable": "", "window_title_regex": ".*Camfrog Video Chat.*", "auto_start": False},
    "target": {"control_type": "ComboBox", "automation_id": "", "title_regex": ".*", "fallback_relative_x": 0.5, "fallback_relative_y": 0.19, "background_enabled": True},
    "status": {
        "presets": ["Sea THAIFIGHT", "ZEAZDEV COMPANY LIMITED", "Busy", "Available"],
        "editor_messages": ["Sea THAIFIGHT", "ZEAZDEV COMPANY LIMITED", "Busy", "Available"],
        "rotation": {"enabled": False, "interval_seconds": 600, "mode": "sequential"},
        "styles": {"random_color": False, "marquee": False, "marquee_width": 28, "palette": ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚪"]},
    },
    "startup": {"windows_startup": False, "start_minimized": False, "system_tray": True},
    "registry": {"import_presets_on_start": False},
    "ui": {"language": "EN"},
    "advanced": {"minimum_interval_seconds": 5, "fallback_enabled": False, "background_only": True, "max_status_length": 160},
}


class ConfigStore:
    def __init__(self):
        base = Path(os.getenv("APPDATA") or (Path.home() / ".config"))
        self.dir = base / "CamfrogStatusChanger"
        self.path = self.dir / "config.json"

    def ensure_defaults(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save(copy.deepcopy(DEFAULT_CONFIG))

    def load(self):
        self.ensure_defaults()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("config root must be an object")
            return self.validate(self._merge(DEFAULT_CONFIG, raw))
        except Exception:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            try:
                shutil.copy2(self.path, self.dir / f"config.corrupt-{stamp}.json")
            except Exception:
                pass
            clean = copy.deepcopy(DEFAULT_CONFIG)
            self.save(clean)
            return clean

    def save(self, data):
        data = self.validate(self._merge(DEFAULT_CONFIG, data))
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, self.path)

    @staticmethod
    def validate(data):
        adv = data.setdefault("advanced", {})
        adv["minimum_interval_seconds"] = max(5, int(adv.get("minimum_interval_seconds", 5)))
        adv["max_status_length"] = min(512, max(1, int(adv.get("max_status_length", 160))))
        adv["apply_timeout_seconds"] = min(30, max(1, int(adv.get("apply_timeout_seconds", 10))))
        status = data.setdefault("status", {})
        rot = status.setdefault("rotation", {})
        rot["interval_seconds"] = max(adv["minimum_interval_seconds"], int(rot.get("interval_seconds", 600)))
        rot["mode"] = rot.get("mode") if rot.get("mode") in {"sequential", "random"} else "sequential"
        msgs = status.get("editor_messages")
        if msgs is None and "editor_lines" in status:
            msgs = status.get("editor_lines", [])
        if msgs is None:
            msgs = []
        if not isinstance(msgs, list):
            msgs = [str(msgs)]
        msgs = [str(value).replace("\x00", "").strip()[: adv["max_status_length"]] for value in msgs[:4]]
        status["editor_messages"] = msgs + [""] * (4 - len(msgs))
        presets = []
        seen = set()
        for item in status.get("presets", []):
            value = str(item).replace("\x00", "").strip()[: adv["max_status_length"]]
            key = value.casefold()
            if value and key not in seen:
                presets.append(value)
                seen.add(key)
        status["presets"] = presets
        target = data.setdefault("target", {})
        target["fallback_relative_x"] = min(1.0, max(0.0, float(target.get("fallback_relative_x", 0.5))))
        target["fallback_relative_y"] = min(1.0, max(0.0, float(target.get("fallback_relative_y", 0.19))))
        styles = status.setdefault("styles", {})
        styles["random_color"] = bool(styles.get("random_color", False))
        styles["marquee"] = bool(styles.get("marquee", False))
        styles["marquee_width"] = min(80, max(4, int(styles.get("marquee_width", 28))))
        ui = data.setdefault("ui", {})
        ui["language"] = "TH" if str(ui.get("language", "EN")).upper() == "TH" else "EN"
        background_only = bool(adv.get("background_only", True))
        adv["background_only"] = background_only
        if background_only:
            adv["fallback_enabled"] = False
        return data

    @staticmethod
    def _merge(base, override):
        out = copy.deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(out.get(key), dict):
                out[key] = ConfigStore._merge(out[key], value)
            else:
                out[key] = value
        return out
