from __future__ import annotations

import os
import ntpath
from pathlib import Path
import psutil

PREFERRED_PATH = Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Camfrog Video Chat\Camfrog Video Chat.exe"))

KNOWN_PATHS = [
    PREFERRED_PATH,
    Path(r"C:\Program Files\Camfrog\Camfrog Video Chat\Camfrog.exe"),
    Path(r"C:\Program Files (x86)\Camfrog\Camfrog Video Chat\Camfrog.exe"),
]

# Match client executables by exact identity. A substring test also catches the
# manager itself (CamfrogStatusChanger.exe), which can make an offline client
# appear online.
CLIENT_EXECUTABLE_NAMES = frozenset({
    "camfrog.exe",
    "camfrog video chat.exe",
})
CLIENT_EXECUTABLE_STEMS = frozenset({"camfrog", "camfrog video chat"})


def _normalized_path(path: str | os.PathLike[str]) -> str:
    expanded = os.path.expandvars(ntpath.expandvars(os.fspath(path)))
    return ntpath.normcase(ntpath.normpath(expanded)).casefold()


def _process_executable(process) -> str:
    info = getattr(process, "info", {}) or {}
    executable = info.get("exe")
    if executable:
        return str(executable)
    try:
        return str(process.exe() or "")
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
        return ""


def _is_client_executable_name(name: str) -> bool:
    basename = ntpath.basename(name).casefold()
    stem = ntpath.splitext(basename)[0]
    return basename in CLIENT_EXECUTABLE_NAMES or stem in CLIENT_EXECUTABLE_STEMS


def find_processes(executable_path: str | os.PathLike[str] | None = None) -> list[psutil.Process]:
    """Return Camfrog client processes, excluding similarly named companion apps.

    When a configured executable is supplied, require an exact normalized path
    match. Otherwise use an allowlist of known client executable names.
    """
    found = []
    expected_path = _normalized_path(executable_path) if executable_path else ""
    for p in psutil.process_iter(["pid", "name", "exe"]):
        try:
            name = ntpath.basename(str(p.info.get("name") or "")).casefold()
            executable = _process_executable(p)
            if expected_path:
                matches = bool(executable) and _normalized_path(executable) == expected_path
            else:
                identity = ntpath.basename(executable) if executable else name
                matches = _is_client_executable_name(identity)
            if matches:
                found.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError, TypeError, ValueError):
            pass
    return found


def find_process_by_pid(
    pid: int,
    executable_path: str | os.PathLike[str] | None = None,
) -> psutil.Process | None:
    """Return one verified Camfrog client process for an exact PID."""
    try:
        process = psutil.Process(int(pid))
        executable = _process_executable(process)
        expected_path = _normalized_path(executable_path) if executable_path else ""
        if expected_path:
            if not executable or _normalized_path(executable) != expected_path:
                return None
        else:
            identity = executable or process.name()
            if not _is_client_executable_name(identity):
                return None
        if not process.is_running():
            return None
        return process
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError, TypeError, ValueError):
        return None


def discover_executable() -> str:
    # Prefer the current per-user Camfrog installation used by this build.
    if PREFERRED_PATH.exists():
        return str(PREFERRED_PATH)

    process_paths = {
        _normalized_path(executable): executable
        for p in find_processes()
        if (executable := _process_executable(p))
    }
    if len(process_paths) == 1:
        return next(iter(process_paths.values()))
    if len(process_paths) > 1:
        return ""
    for path in KNOWN_PATHS:
        if path.exists():
            return str(path)
    return ""
