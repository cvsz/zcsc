from __future__ import annotations

import os
from pathlib import Path
import psutil

PREFERRED_PATH = Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Camfrog Video Chat\Camfrog Video Chat.exe"))

KNOWN_PATHS = [
    PREFERRED_PATH,
    Path(r"C:\Program Files\Camfrog\Camfrog Video Chat\Camfrog.exe"),
    Path(r"C:\Program Files (x86)\Camfrog\Camfrog Video Chat\Camfrog.exe"),
]


def find_processes() -> list[psutil.Process]:
    found = []
    for p in psutil.process_iter(["pid", "name", "exe"]):
        try:
            if "camfrog" in (p.info.get("name") or "").lower():
                found.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return found


def discover_executable() -> str:
    if PREFERRED_PATH.exists():
        return str(PREFERRED_PATH)
    for p in find_processes():
        try:
            exe = p.exe()
            if exe:
                return exe
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    for path in KNOWN_PATHS:
        if path.exists():
            return str(path)
    return ""
