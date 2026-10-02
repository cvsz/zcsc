from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def app_data_dir() -> Path:
    appdata = os.getenv("APPDATA")
    base = Path(appdata) if appdata else (Path.home() / ".config")
    return base / "CamfrogStatusChanger"


def configure_logging() -> Path:
    log_dir = app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "app.log"
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler = RotatingFileHandler(log_path, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)
    # Frozen/windowed builds intentionally avoid a console handler.
    if not getattr(__import__("sys"), "frozen", False):
        stream = logging.StreamHandler()
        stream.setFormatter(fmt)
        root.addHandler(stream)
    return log_path
