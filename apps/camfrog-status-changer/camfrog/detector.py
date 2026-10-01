from __future__ import annotations

import os
from pathlib import Path
import psutil

PREFERRED_PATH = Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Camfrog Video Chat\Camfrog Video Chat.exe"))
KNOWN_PATHS = [
    PREFERRED_PATH,
    Path(r"C:\Program Files\Camfrog\Camfrog Video Chat\Camfrog Video Chat.exe"),
    Path(r"C:\Program Files (x86)\Camfrog\Camfrog Video Chat\Camfrog Video Chat.exe"),
    Path(r"C:\Program Files\Camfrog\Camfrog Video Chat\Camfrog.exe"),
    Path(r"C:\Program Files (x86)\Camfrog\Camfrog Video Chat\Camfrog.exe"),
]
KNOWN_PROCESS_NAMES = {"camfrog video chat.exe", "camfrog.exe"}


def _is_camfrog_process_info(info: dict, current_pid: int | None = None) -> bool:
    pid = int(info.get("pid") or 0)
    if current_pid is not None and pid == int(current_pid):
        return False
    name = str(info.get("name") or "").casefold()
    if name in KNOWN_PROCESS_NAMES:
        return True
    exe = str(info.get("exe") or "")
    if exe:
        return Path(exe).name.casefold() in KNOWN_PROCESS_NAMES
    return False


def find_processes() -> list[psutil.Process]:
    found = []
    current_pid = os.getpid()
    for process in psutil.process_iter(["pid", "name", "exe"]):
        try:
            if _is_camfrog_process_info(process.info, current_pid):
                found.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, TypeError):
            pass
    return found


def discover_executable() -> str:
    if PREFERRED_PATH.exists():
        return str(PREFERRED_PATH)
    for process in find_processes():
        try:
            executable = process.exe()
            if executable:
                return executable
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    for path in KNOWN_PATHS:
        if path.exists():
            return str(path)
    return ""
