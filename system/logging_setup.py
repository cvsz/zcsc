from __future__ import annotations

import logging
import os
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path


def app_data_dir() -> Path:
    appdata = os.getenv("APPDATA")
    base = Path(appdata) if appdata else (Path.home() / ".config")
    return base / "CamfrogStatusChanger"


def configure_logging() -> Path:
    candidates = []
    last_error = None
    try:
        candidates.append(app_data_dir() / "logs" / "app.log")
    except Exception as exc:
        last_error = exc
    try:
        candidates.append(Path(tempfile.gettempdir()) / "CamfrogStatusChanger" / "logs" / "app.log")
    except Exception as exc:
        last_error = last_error or exc
    candidates = list(dict.fromkeys(candidates))
    root = logging.getLogger()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler = None
    log_path = None
    for candidate in candidates:
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                candidate, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
            )
            log_path = candidate
            break
        except OSError as exc:
            last_error = exc
            if file_handler is not None:
                file_handler.close()
                file_handler = None
    if file_handler is None or log_path is None:
        raise OSError("Could not open app.log in the application data or temporary directory") from last_error

    root.setLevel(logging.INFO)
    root.handlers.clear()
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)
    # Frozen/windowed builds intentionally avoid a console handler.
    if not getattr(__import__("sys"), "frozen", False):
        stream = logging.StreamHandler()
        stream.setFormatter(fmt)
        root.addHandler(stream)
    return log_path
