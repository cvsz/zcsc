from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "CamfrogStatusChanger"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def launch_command() -> str:
    exe = Path(sys.executable).resolve()
    if getattr(sys, "frozen", False):
        return f'"{exe}"'

    # In development use pythonw.exe when available so startup has no console window.
    pythonw = exe.with_name("pythonw.exe")
    launcher = pythonw if pythonw.exists() else exe
    script = Path(__file__).resolve().parents[1] / "app.py"
    return f'"{launcher}" "{script}"'


def set_start_with_windows(enabled: bool) -> None:
    if os.name != "nt":
        return
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
