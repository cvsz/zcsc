from __future__ import annotations
import os, sys

def set_start_with_windows(enabled: bool):
    if os.name!="nt":
        return
    import winreg
    key=winreg.CreateKey(winreg.HKEY_CURRENT_USER,r"Software\Microsoft\Windows\CurrentVersion\Run")
    try:
        if enabled:
            cmd=f'"{sys.executable}"' if getattr(sys,"frozen",False) else f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
            winreg.SetValueEx(key,"CamfrogStatusChanger",0,winreg.REG_SZ,cmd)
        else:
            try: winreg.DeleteValue(key,"CamfrogStatusChanger")
            except FileNotFoundError: pass
    finally:
        winreg.CloseKey(key)
