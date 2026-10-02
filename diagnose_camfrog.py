from __future__ import annotations

import json
from datetime import datetime, timezone

from system.config_store import ConfigStore
from camfrog.controller import CamfrogController
from camfrog.background_win32 import enumerate_native_controls
from camfrog.native_profile import identify_profile


def safe_text(item: dict) -> str:
    cls = str(item.get("class_name", "")).lower()
    text = str(item.get("text", ""))
    if "combo" in cls or "button" in cls or "edit4combo" in cls:
        return text[:120]
    return ""


def main() -> None:
    store = ConfigStore()
    config = store.load()
    ctrl = CamfrogController(config)
    win = ctrl.find_window()
    rows = enumerate_native_controls(int(win.handle))
    safe = []
    classes_seen: set[str] = set()
    for row in rows:
        cls = str(row.get("class_name", ""))
        if cls:
            classes_seen.add(cls)
        safe.append({
            "hwnd": row.get("hwnd"),
            "control_id": row.get("control_id"),
            "class_name": cls,
            "text": safe_text(row),
            "visible": row.get("visible"),
            "enabled": row.get("enabled"),
            "rect": row.get("rect"),
        })

    exe = config.get("camfrog", {}).get("executable", "")
    profile, digest = identify_profile(exe)
    profile_dict = profile.to_dict() if profile else None
    expected_classes = list(profile.classes) if profile else []
    matched_classes = sorted(set(expected_classes) & classes_seen)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "camfrog_executable": exe,
        "camfrog_sha256": digest,
        "known_native_profile_matched": bool(profile),
        "native_profile": profile_dict,
        "native_profile_class_matches": matched_classes,
        "note": (
            "RVA anchors are static-analysis diagnostics only. This tool does not invoke internal Camfrog functions."
        ),
        "controls": safe,
    }
    out = store.dir / "camfrog-native-diagnostic-safe.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
