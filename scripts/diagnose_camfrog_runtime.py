#!/usr/bin/env python3
"""Print a privacy-minimized process classification for ZCSC Camfrog PID targeting."""

from __future__ import annotations

import json
import ntpath
import os
from pathlib import Path

import psutil

from camfrog.detector import CLIENT_EXECUTABLE_NAMES, _normalized_path, _process_executable
from system.config_store import ConfigStore


def classify_process(process, configured_path: str) -> dict[str, object] | None:
    try:
        pid = int(process.pid)
        name = ntpath.basename(str(process.info.get("name") or process.name() or ""))
        executable = _process_executable(process)
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError, TypeError, ValueError):
        return None

    basename = ntpath.basename(executable or name).casefold()
    configured_match = bool(
        configured_path
        and executable
        and _normalized_path(executable) == _normalized_path(configured_path)
    )

    if pid == os.getpid():
        role = "zcsc-current-process"
        eligible = False
        reason = "current ZCSC process is never a Camfrog target"
    elif configured_match:
        role = "camfrog-client"
        eligible = True
        reason = "exact configured Camfrog executable path"
    elif basename in CLIENT_EXECUTABLE_NAMES:
        role = "camfrog-client"
        eligible = not configured_path
        reason = (
            "known exact Camfrog client executable name"
            if not configured_path
            else "known client name but path differs from configured executable"
        )
    elif basename == "camfrog_cef.exe":
        role = "camfrog-cef-helper"
        eligible = False
        reason = "CEF helper process is never a client target"
    elif basename == "camfrogstatuschanger.exe":
        role = "zcsc"
        eligible = False
        reason = "ZCSC executable is never a Camfrog target"
    elif basename.startswith("camfrog"):
        role = "camfrog-related-other"
        eligible = False
        reason = "Camfrog-prefixed process is not in the exact client allowlist"
    else:
        return None

    return {
        "pid": pid,
        "process_name": name,
        "role": role,
        "eligible": eligible,
        "reason": reason,
    }


def main() -> int:
    store = ConfigStore()
    config = store.load()
    configured_path = str(config.get("camfrog", {}).get("executable", "") or "").strip()

    rows = []
    for process in psutil.process_iter(["pid", "name", "exe"]):
        row = classify_process(process, configured_path)
        if row is not None:
            rows.append(row)
    rows.sort(key=lambda item: (not bool(item["eligible"]), str(item["role"]), int(item["pid"])))

    output = {
        "configured_executable": configured_path,
        "eligible_pids": [row["pid"] for row in rows if row["eligible"]],
        "processes": rows,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
