#!/usr/bin/env python3
"""Print a privacy-minimized process classification for ZCSC Camfrog PID targeting."""

from __future__ import annotations

import json
import ntpath
import os
import re
import sys
from pathlib import Path

import psutil

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from camfrog.detector import CLIENT_EXECUTABLE_NAMES, _normalized_path, _process_executable  # noqa: E402
from system.config_store import ConfigStore  # noqa: E402


def read_config_path(path: Path) -> tuple[str, str]:
    """Read only the configured executable; never create, migrate, or repair config."""
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "missing", ""
    except (OSError, UnicodeError, json.JSONDecodeError):
        return "invalid", ""

    if not isinstance(config, dict):
        return "invalid", ""
    camfrog = config.get("camfrog", {})
    if not isinstance(camfrog, dict):
        return "invalid", ""
    configured = camfrog.get("executable", "")
    if not isinstance(configured, str):
        return "invalid", ""
    configured = configured.strip()
    return ("configured" if configured else "missing_executable"), configured


def redact_user_profile(path: str) -> str:
    """Redact per-user path components before diagnostic output is shared."""
    return re.sub(
        r"(?i)([\\/](?:Users|home|Documents and Settings)[\\/])[^\\/]+",
        lambda match: f"{match.group(1)}<USER>",
        path,
    )


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
    elif basename == "camfrog_cef.exe":
        role = "camfrog-cef-helper"
        eligible = False
        reason = "CEF helper process is never a client target"
    elif basename == "camfrogstatuschanger.exe":
        role = "zcsc"
        eligible = False
        reason = "ZCSC executable is never a Camfrog target"
    elif basename in CLIENT_EXECUTABLE_NAMES:
        role = "camfrog-client"
        if configured_path and not configured_match:
            eligible = False
            reason = "known client name but path differs from configured executable"
        else:
            eligible = True
            reason = (
                "exact configured Camfrog executable path"
                if configured_match
                else "known exact Camfrog client executable name"
            )
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
    config_status, configured_path = read_config_path(store.path)

    rows = []
    for process in psutil.process_iter(["pid", "name", "exe"]):
        row = classify_process(process, configured_path)
        if row is not None:
            rows.append(row)
    rows.sort(key=lambda item: (not bool(item["eligible"]), str(item["role"]), int(item["pid"])))

    output = {
        "config_status": config_status,
        "configured_executable": redact_user_profile(configured_path),
        "eligible_pids": [row["pid"] for row in rows if row["eligible"]],
        "processes": rows,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
