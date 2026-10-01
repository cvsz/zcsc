from __future__ import annotations

import json
import os
from pathlib import Path

from camfrog.detector import discover_executable, find_processes
from camfrog.native_profile import identify_profile


def main() -> int:
    exe = discover_executable()
    profile = None
    digest = ""
    if exe:
        profile, digest = identify_profile(exe)

    processes = []
    for process in find_processes():
        try:
            processes.append(
                {
                    "pid": process.pid,
                    "name": process.name(),
                    "exe": process.exe(),
                }
            )
        except Exception:
            pass

    report = {
        "executable": exe,
        "sha256": digest,
        "profile_matched": bool(profile),
        "profile_name": profile.name if profile else "",
        "classes": list(profile.classes) if profile else [],
        "anchors": profile.anchors if profile else {},
        "processes": processes,
        "note": "Diagnostic-only. No credentials, tokens, cookies or session data are collected.",
    }

    out_dir = Path(os.getenv("APPDATA") or Path.home()) / "CamfrogStatusChanger"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "camfrog-native-diagnostic-safe.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
