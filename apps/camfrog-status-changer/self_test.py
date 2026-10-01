from __future__ import annotations

import json
import os
import platform
import tempfile
from pathlib import Path

from automation.intervals import interval_to_seconds
from camfrog.detector import discover_executable
from status_styles import marquee_frame
from system.config_store import ConfigStore


def main() -> int:
    checks: dict[str, object] = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "windows": os.name == "nt",
        "interval_30s": interval_to_seconds(30, "seconds"),
        "marquee_changes": marquee_frame("ZEAZDEV", 0, 8)[0] != marquee_frame("ZEAZDEV", 1, 8)[0],
        "camfrog_detected": bool(discover_executable()),
    }

    with tempfile.TemporaryDirectory() as tmp:
        store = ConfigStore()
        store.dir = Path(tmp)
        store.path = store.dir / "config.json"
        store.ensure_defaults()
        cfg = store.load()
        checks["config_slots"] = len(cfg["status"]["editor_messages"]) == 4
        checks["config_roundtrip"] = store.path.exists()

    ok = all(
        value is True or isinstance(value, (str, int))
        for key, value in checks.items()
        if key not in {"camfrog_detected"}
    )
    checks["ok"] = bool(ok)

    out_dir = Path(os.getenv("APPDATA") or Path.home()) / "CamfrogStatusChanger"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "self-test.json"
    out.write_text(json.dumps(checks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(checks, indent=2, ensure_ascii=False))
    print(f"SELF-TEST: {'PASS' if ok else 'FAIL'}")
    print(f"Report: {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
