from __future__ import annotations
import logging, os, subprocess, threading, time
from dataclasses import dataclass
from .detector import find_processes
from .background_win32 import set_status_background
from .foreground_fallback import apply_status_foreground
from .native_profile import identify_profile
from .window_locator import locate_camfrog_hwnd

log=logging.getLogger(__name__)

@dataclass
class ChangeResult:
    ok: bool
    message: str
    previous_value: str=""
    new_value: str=""
    stage: str=""
    publication_verified: bool=False

class CamfrogController:
    def __init__(self,config):
        self.config=config
        self._lock=threading.Lock()
        self._last=0.0
        self._cached_hwnd=0

    def ensure_running(self):
        if find_processes(): return ChangeResult(True,"Camfrog is running",stage="process")
        exe=self.config["camfrog"].get("executable","").strip()
        if not exe: return ChangeResult(False,"Camfrog executable is not configured",stage="process")
        try: subprocess.Popen([exe],shell=False)
        except Exception as exc:return ChangeResult(False,f"Failed to start Camfrog: {exc}",stage="process")
        for _ in range(30):
            if find_processes(): return ChangeResult(True,"Camfrog started",stage="process")
            time.sleep(.5)
        return ChangeResult(False,"Camfrog did not start within timeout",stage="process")

    def find_hwnd(self):
        if os.name!="nt":
            raise RuntimeError("Windows only")
        pids={int(p.pid) for p in find_processes()}
        if not pids:
            raise RuntimeError("Camfrog process is not running")
        try:
            match=locate_camfrog_hwnd(pids,self._cached_hwnd)
        except Exception:
            self._cached_hwnd=0
            raise
        self._cached_hwnd=int(match.hwnd)
        return self._cached_hwnd

    def native_profile_info(self):
        exe=self.config.get("camfrog",{}).get("executable","")
        try:
            p,d=identify_profile(exe)
            return {"matched":bool(p),"sha256":d,"name":p.name if p else "","classes":list(p.classes) if p else []}
        except Exception as exc:
            return {"matched":False,"sha256":"","name":"","error":str(exc)}

    def set_status(self,value,*,respect_rate_limit=True):
        value=str(value).replace("\x00","")
        if not value.strip(): return ChangeResult(False,"Status cannot be empty",stage="validate")
        max_len=int(self.config.get("advanced",{}).get("max_status_length",160))
        if len(value)>max_len:return ChangeResult(False,f"Status exceeds configured maximum length ({max_len})",stage="validate")
        if not self._lock.acquire(blocking=False):return ChangeResult(False,"Another status change is already in progress",stage="lock")

        try:
            if respect_rate_limit:
                minimum=max(1,int(self.config.get("advanced",{}).get("minimum_interval_seconds",5)))
                if self._last and time.monotonic()-self._last<minimum:
                    remaining=max(1,int(minimum-(time.monotonic()-self._last)+0.999))
                    return ChangeResult(False,f"Rate limited: retry in {remaining}s",stage="rate-limit")

            running=self.ensure_running()
            if not running.ok:return running

            hwnd=self.find_hwnd()
            t=self.config.get("target",{})
            advanced=self.config.get("advanced",{})

            background_message=""
            if t.get("background_enabled",True):
                r=set_status_background(
                    hwnd,
                    float(t.get("fallback_relative_x",.5)),
                    float(t.get("fallback_relative_y",.19)),
                    value,
                    known_statuses=self.config.get("status",{}).get("presets",[]),
                )
                background_message=r.message
                if r.ok and r.verified:
                    if respect_rate_limit:
                        self._last=time.monotonic()
                    return ChangeResult(
                        True,
                        r.message,
                        new_value=value,
                        stage="background-local-verified",
                        publication_verified=False,
                    )

            allow_foreground=bool(advanced.get("fallback_enabled",False)) and not bool(advanced.get("background_only",True))
            if allow_foreground:
                fg=apply_status_foreground(
                    hwnd,
                    float(t.get("fallback_relative_x",.5)),
                    float(t.get("fallback_relative_y",.19)),
                    value,
                )
                if fg.ok:
                    if respect_rate_limit:
                        self._last=time.monotonic()
                    return ChangeResult(
                        True,
                        fg.message + "; server publication still requires independent verification",
                        new_value=value,
                        stage="foreground-submitted",
                        publication_verified=False,
                    )
                detail=f"{background_message}; {fg.message}".strip("; ")
                return ChangeResult(False,detail or "Foreground fallback failed",stage="foreground-failed")

            return ChangeResult(
                False,
                background_message or "Background status commit could not be verified",
                stage="background-unverified",
            )
        except Exception as exc:
            log.exception("Status change failed")
            return ChangeResult(False,str(exc),stage="exception")
        finally:
            self._lock.release()
