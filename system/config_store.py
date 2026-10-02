from __future__ import annotations

import copy
import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any

from camfrog.bad_word_catalog import DEFAULT_BAD_WORD_TERMS
from camfrog.auto_respond import normalize_reply_text
from status_catalog import DEFAULT_STANDARD_STATUS_ID, STANDARD_STATUS_IDS

DEFAULT_CONFIG = {
    "schema_version": 2,
    "camfrog": {
        "executable": "",
        "window_title_regex": ".*Camfrog Video Chat.*",
        "auto_start": False,
        "restore_window_state": True,
    },
    "target": {
        "control_type": "ComboBox",
        "automation_id": "",
        "title_regex": ".*",
        "fallback_relative_x": 0.50,
        "fallback_relative_y": 0.19,
        "background_enabled": True,
    },
    "status": {
        "presets": [],
        "editor_messages": ["", "", "", ""],
        "standard_status_id": DEFAULT_STANDARD_STATUS_ID,
        "favorite_standard_ids": [],
        "rotation": {
            "enabled": False,
            "interval_seconds": 600,
            "mode": "sequential",
            "schedule_enabled": False,
            "schedule_start": "08:00",
            "schedule_end": "23:00",
            "quiet_hours_enabled": False,
            "quiet_start": "22:00",
            "quiet_end": "08:00",
        },
        "styles": {
            "random_color": False,
            "custom_color_enabled": False,
            "custom_color": "#00C7BE",
            "marquee": False,
            "marquee_width": 28,
            "marquee_frame_interval_seconds": 10,
            "color_template": "[color={color}]{text}[/color]",
            "palette": ["#FF3B30","#FF9500","#FFCC00","#34C759","#00C7BE","#0A84FF","#5E5CE6","#BF5AF2","#FF2D55"]
        },
    },
    "auto_respond": {
        "enabled": False,
        "private_enabled": True,
        "room_enabled": True,
        "reply_text": "Thanks for your message.",
        "own_username": "",
        "cooldown_seconds": 60,
        "poll_interval_seconds": 2,
        "private": {
            "window_title_contains": "",
            "history_automation_id": "",
            "input_automation_id": "",
            "send_automation_id": "",
        },
        "room": {
            "window_title_contains": "",
            "history_automation_id": "",
            "input_automation_id": "",
            "send_automation_id": "",
        },
    },
    "room_actions": {
        "enabled": False,
        "room_title": "",
        "owner_nickname": "",
        "target_nicknames": {
            "op": "",
            "friend": "",
            "admin": "",
            "owner": "",
            "mute": "",
            "kick": "",
            "ban": "",
        },
        "command_templates": {
            "op": "",
            "friend": "",
            "admin": "",
            "owner": "",
            "mute": "",
            "kick": "",
            "ban": "",
        },
    },
    "bad_word_moderation": {
        "enabled": False,
        "auto_kick": False,
        "terms": list(DEFAULT_BAD_WORD_TERMS),
        "cooldown_seconds": 60,
    },
    "room_event_notifications": {
        "enabled": False,
        "phrases": [],
        "cooldown_seconds": 10,
    },
    "profile_links": {"nickname": ""},
    "startup": {"windows_startup": False, "start_minimized": False, "system_tray": True},
    "registry": {"import_presets_on_start": True},
    "ui": {"language": "EN"},
    "advanced": {
        "minimum_interval_seconds": 5,
        "fallback_enabled": False,
        "max_status_length": 160,
        "apply_timeout_seconds": 8,
    },
}


class ConfigStore:
    def __init__(self) -> None:
        appdata = os.getenv("APPDATA")
        base = Path(appdata) if appdata else (Path.home() / ".config")
        self.dir = base / "CamfrogStatusChanger"
        self.path = self.dir / "config.json"

    def ensure_defaults(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save(copy.deepcopy(DEFAULT_CONFIG))

    def load(self) -> dict[str, Any]:
        self.ensure_defaults()
        try:
            with self.path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                raise ValueError("config root must be an object")
            return self.validate(self._merge(DEFAULT_CONFIG, raw))
        except Exception:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            backup = self.dir / f"config.corrupt-{stamp}.json"
            try:
                shutil.copy2(self.path, backup)
            except Exception:
                pass
            clean = copy.deepcopy(DEFAULT_CONFIG)
            self.save(clean)
            return clean

    def save(self, data: dict[str, Any]) -> None:
        data = self.validate(self._merge(DEFAULT_CONFIG, data))
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)

    @staticmethod
    def validate(data: dict[str, Any]) -> dict[str, Any]:
        data["schema_version"] = 2
        adv = data.setdefault("advanced", {})
        adv["minimum_interval_seconds"] = max(5, int(adv.get("minimum_interval_seconds", 5)))
        adv["max_status_length"] = min(512, max(1, int(adv.get("max_status_length", 160))))
        adv["apply_timeout_seconds"] = min(30, max(2, int(adv.get("apply_timeout_seconds", 8))))
        adv.pop("background_only", None)
        rot = data.setdefault("status", {}).setdefault("rotation", {})
        rot["interval_seconds"] = max(adv["minimum_interval_seconds"], int(rot.get("interval_seconds", 600)))
        if rot.get("mode") not in {"sequential", "random"}:
            rot["mode"] = "sequential"
        presets = data["status"].setdefault("presets", [])
        clean = []
        seen = set()
        for item in presets:
            value = str(item).replace("\x00", "").strip()[: adv["max_status_length"]]
            key = value.casefold()
            if value and key not in seen:
                seen.add(key)
                clean.append(value)
        data["status"]["presets"] = clean
        standard_status_id = str(data["status"].get("standard_status_id", DEFAULT_STANDARD_STATUS_ID))
        data["status"]["standard_status_id"] = (
            standard_status_id if standard_status_id in STANDARD_STATUS_IDS else DEFAULT_STANDARD_STATUS_ID
        )
        favorites = data["status"].get("favorite_standard_ids", [])
        if not isinstance(favorites, list):
            favorites = []
        data["status"]["favorite_standard_ids"] = list(dict.fromkeys(
            str(status_id) for status_id in favorites if str(status_id) in STANDARD_STATUS_IDS
        ))
        # Message slots are independent statuses: one message = one apply/tick.
        messages = data["status"].get("editor_messages")
        if not isinstance(messages, list):
            legacy = data["status"].get("editor_lines", [])
            messages = legacy if isinstance(legacy, list) else [legacy]
        messages = [str(x).replace("\x00", "").strip()[: adv["max_status_length"]] for x in messages[:4]]
        messages += [""] * (4 - len(messages))
        data["status"]["editor_messages"] = messages
        data["status"].pop("editor_lines", None)
        auto = data.get("auto_respond")
        if not isinstance(auto, dict):
            auto = {}
            data["auto_respond"] = auto
        auto["enabled"] = auto.get("enabled", False) is True
        auto["private_enabled"] = auto.get("private_enabled", True) is True
        auto["room_enabled"] = auto.get("room_enabled", True) is True
        auto["reply_text"] = normalize_reply_text(auto.get("reply_text", "Thanks for your message."))
        auto["own_username"] = str(auto.get("own_username", "")).replace("\x00", "").strip()[:64]
        try:
            cooldown = int(auto.get("cooldown_seconds", 60))
        except (TypeError, ValueError):
            cooldown = 60
        try:
            poll_interval = int(auto.get("poll_interval_seconds", 2))
        except (TypeError, ValueError):
            poll_interval = 2
        auto["cooldown_seconds"] = min(86400, max(10, cooldown))
        auto["poll_interval_seconds"] = min(10, max(1, poll_interval))
        for kind in ("private", "room"):
            selectors = auto.get(kind)
            if not isinstance(selectors, dict):
                selectors = {}
            auto[kind] = {
                key: str(selectors.get(key, "")).replace("\x00", "").strip()[:128]
                for key in (
                    "window_title_contains",
                    "history_automation_id",
                    "input_automation_id",
                    "send_automation_id",
                )
            }
        room_actions = data.get("room_actions")
        if not isinstance(room_actions, dict):
            room_actions = {}
        room_actions["enabled"] = room_actions.get("enabled", False) is True
        room_title = str(room_actions.get("room_title", "")).replace("\x00", "").strip()
        room_actions["room_title"] = room_title[:128]

        def safe_nickname(value: Any) -> str:
            nickname = str(value).replace("\x00", "").strip()
            if not nickname or len(nickname) > 64 or any(
                not (character.isalnum() or character in "_.-") for character in nickname
            ):
                return ""
            return nickname

        room_actions["owner_nickname"] = safe_nickname(room_actions.get("owner_nickname", ""))
        target_nicknames = room_actions.get("target_nicknames")
        if not isinstance(target_nicknames, dict):
            target_nicknames = {}
        room_actions["target_nicknames"] = {
            action: safe_nickname(target_nicknames.get(action, ""))
            for action in ("op", "friend", "admin", "owner", "mute", "kick", "ban")
        }
        command_templates = room_actions.get("command_templates")
        if not isinstance(command_templates, dict):
            command_templates = {}
        room_actions["command_templates"] = {
            action: str(command_templates.get(action, "")).replace("\x00", "")[:256]
            for action in ("op", "friend", "admin", "owner", "mute", "kick", "ban")
        }
        data["room_actions"] = room_actions
        moderation = data.get("bad_word_moderation")
        if not isinstance(moderation, dict):
            moderation = {}
        moderation["enabled"] = moderation.get("enabled", False) is True
        moderation["auto_kick"] = moderation.get("auto_kick", False) is True
        terms = moderation.get("terms", [])
        if not isinstance(terms, list):
            terms = []
        clean_terms = []
        seen_terms = set()
        for term in terms[:300]:
            word = " ".join(str(term).replace("\x00", "").split())[:80]
            key = word.casefold()
            if len(word) >= 2 and key not in seen_terms:
                seen_terms.add(key)
                clean_terms.append(word)
        moderation["terms"] = clean_terms
        try:
            moderation_cooldown = int(moderation.get("cooldown_seconds", 60))
        except (TypeError, ValueError):
            moderation_cooldown = 60
        moderation["cooldown_seconds"] = min(3600, max(10, moderation_cooldown))
        data["bad_word_moderation"] = moderation
        room_events = data.get("room_event_notifications")
        if not isinstance(room_events, dict):
            room_events = {}
        room_events["enabled"] = room_events.get("enabled", False) is True
        phrases = room_events.get("phrases", [])
        if not isinstance(phrases, list):
            phrases = []
        clean_phrases = []
        seen_phrases = set()
        for phrase in phrases[:100]:
            value = " ".join(str(phrase).replace("\x00", "").split())[:80]
            key = value.casefold()
            if len(value) >= 2 and key not in seen_phrases:
                seen_phrases.add(key)
                clean_phrases.append(value)
        room_events["phrases"] = clean_phrases
        try:
            event_cooldown = int(room_events.get("cooldown_seconds", 10))
        except (TypeError, ValueError):
            event_cooldown = 10
        room_events["cooldown_seconds"] = min(3600, max(1, event_cooldown))
        data["room_event_notifications"] = room_events
        profile_links = data.get("profile_links")
        if not isinstance(profile_links, dict):
            profile_links = {}
        profile_links["nickname"] = str(profile_links.get("nickname", "")).replace("\x00", "").strip()[:64]
        data["profile_links"] = profile_links
        styles = data["status"].setdefault("styles", {})
        styles["random_color"] = bool(styles.get("random_color", False))
        styles["custom_color_enabled"] = bool(styles.get("custom_color_enabled", False))
        custom_color = str(styles.get("custom_color", "#00C7BE")).strip().upper()
        styles["custom_color"] = custom_color if re.fullmatch(r"#[0-9A-F]{6}", custom_color) else "#00C7BE"
        styles["marquee"] = bool(styles.get("marquee", False))
        styles["marquee_width"] = min(80, max(4, int(styles.get("marquee_width", 28))))
        try:
            marquee_interval = int(styles.get("marquee_frame_interval_seconds", 10))
        except (TypeError, ValueError):
            marquee_interval = 10
        styles["marquee_frame_interval_seconds"] = min(3600, max(adv["minimum_interval_seconds"], marquee_interval))
        styles["color_template"] = str(styles.get("color_template", "[color={color}]{text}[/color]"))[:200]
        palette = styles.get("palette", [])
        if not isinstance(palette, list):
            palette = []
        styles["palette"] = [
            str(x).strip().upper()
            for x in palette
            if re.fullmatch(r"#[0-9A-Fa-f]{6}", str(x).strip())
        ][:32]
        for key, default in (
            ("schedule_start", "08:00"),
            ("schedule_end", "23:00"),
            ("quiet_start", "22:00"),
            ("quiet_end", "08:00"),
        ):
            value = str(rot.get(key, default))
            rot[key] = value if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value) else default
        rot["schedule_enabled"] = bool(rot.get("schedule_enabled", False))
        rot["quiet_hours_enabled"] = bool(rot.get("quiet_hours_enabled", False))
        ui = data.setdefault("ui", {})
        ui["language"] = "TH" if str(ui.get("language", "EN")).upper() == "TH" else "EN"
        target = data.setdefault("target", {})
        target["background_enabled"] = target.get("background_enabled", True) is True
        for key, default in (("fallback_relative_x", .5), ("fallback_relative_y", .19)):
            try:
                target[key] = min(1.0, max(0.0, float(target.get(key, default))))
            except Exception:
                target[key] = default
        return data

    @staticmethod
    def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        out = copy.deepcopy(base)
        for k, v in override.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = ConfigStore._merge(out[k], v)
            else:
                out[k] = v
        return out
