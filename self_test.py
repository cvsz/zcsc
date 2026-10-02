from __future__ import annotations

import json
import os
import platform
import sys

from system.config_store import ConfigStore
from version import VERSION


def main() -> int:
    store = ConfigStore()
    cfg = store.load()
    checks = {
        "version": VERSION,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "config_path": str(store.path),
        "config_load": isinstance(cfg, dict),
        "windows": os.name == "nt",
        "camfrog_executable_configured": bool(cfg.get("camfrog", {}).get("executable")),
        "status_commit_focuses_camfrog": True,
        "coordinate_fallback_enabled": bool(cfg.get("advanced", {}).get("fallback_enabled", False)),
        "rotation_enabled": bool(cfg.get("status", {}).get("rotation", {}).get("enabled", False)),
    }
    if os.name == "nt":
        from camfrog.detector import discover_executable, find_processes
        detected = discover_executable()
        checks["camfrog_detected"] = bool(detected)
        checks["camfrog_running"] = bool(find_processes(executable_path=cfg.get("camfrog", {}).get("executable") or None))
        checks["detected_path"] = detected
    out = store.dir / "self-test.json"
    out.write_text(json.dumps(checks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(checks, indent=2, ensure_ascii=False))
    print(f"Saved: {out}")
    return 0 if checks["config_load"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
