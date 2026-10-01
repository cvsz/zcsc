from __future__ import annotations
import logging, os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def configure_logging():
    base=Path(os.getenv("APPDATA") or (Path.home()/".config"))/"CamfrogStatusChanger"
    base.mkdir(parents=True,exist_ok=True)
    root=logging.getLogger()
    if root.handlers:
        return
    root.setLevel(logging.INFO)
    h=RotatingFileHandler(base/"app.log",maxBytes=2*1024*1024,backupCount=5,encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(h)
