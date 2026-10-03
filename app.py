from __future__ import annotations

import logging
import os
import tempfile
import traceback
from pathlib import Path

from system.dpi_awareness import configure_process_dpi_awareness
from version import APP_NAME, VERSION


def _startup_language(config: object) -> str:
    if not isinstance(config, dict):
        return "EN"
    ui = config.get("ui")
    if not isinstance(ui, dict):
        return "EN"
    language = ui.get("language")
    return "TH" if isinstance(language, str) and language.upper() == "TH" else "EN"


def _startup_log_paths() -> list[Path]:
    candidates = []
    try:
        appdata = os.getenv("APPDATA")
        base = Path(appdata) if appdata else Path.home() / ".config"
        candidates.append(base / "CamfrogStatusChanger" / "logs" / "app.log")
    except Exception:
        pass
    try:
        candidates.append(Path(tempfile.gettempdir()) / "CamfrogStatusChanger" / "logs" / "app.log")
    except Exception:
        pass
    return list(dict.fromkeys(candidates))


def _write_emergency_log(details: str) -> Path | None:
    for path in _startup_log_paths():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as log_file:
                log_file.write("Fatal application startup failure\n")
                log_file.write(details)
                if not details.endswith("\n"):
                    log_file.write("\n")
            return path
        except OSError:
            continue
    return None


def _show_startup_dialog(kind: str, title: str, message: str) -> None:
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    try:
        root.withdraw()
        getattr(messagebox, kind)(title, message, parent=root)
    finally:
        root.destroy()


def main() -> int:
    logger = logging.getLogger("camfrog_status")
    logging_ready = False
    language = "EN"
    instance = None
    dpi_ready = False

    try:
        dpi_ready = configure_process_dpi_awareness()
        from system.logging_setup import configure_logging

        configure_logging()
        logging_ready = True
        if not dpi_ready:
            logger.warning(
                "Per-monitor-v2 DPI awareness could not be confirmed; coordinate fallbacks will stay disabled"
            )

        from system.config_store import ConfigStore

        store = ConfigStore()
        store.ensure_defaults()
        startup_config = store.load()
        language = _startup_language(startup_config)

        from system.single_instance import SingleInstance

        instance = SingleInstance()
        if not instance.acquire():
            message = (
                "Camfrog Status Changer กำลังทำงานอยู่แล้ว กรุณาตรวจ System Tray"
                if language == "TH"
                else "Camfrog Status Changer is already running. Check the system tray."
            )
            try:
                _show_startup_dialog("showinfo", APP_NAME, message)
            except Exception:
                logger.warning("Could not show the duplicate-instance dialog", exc_info=True)
            return 2

        from ui.dashboard import AppUI

        app = AppUI(store=store)
        app.title(f"{APP_NAME} {VERSION}")
        app.mainloop()
        return 0
    except Exception as exc:
        details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        if logging_ready:
            logger.exception("Fatal application startup failure")
        else:
            _write_emergency_log(details)
        message = (
            "เกิดข้อผิดพลาดระหว่างเริ่มโปรแกรม กรุณาตรวจ app.log ในโฟลเดอร์ config"
            if language == "TH"
            else "The application could not start. See app.log in the config folder or temporary directory."
        )
        try:
            _show_startup_dialog("showerror", APP_NAME, message)
        except Exception:
            if logging_ready:
                logger.warning("Could not show the startup error dialog", exc_info=True)
            else:
                _write_emergency_log("Could not show the startup error dialog.\n")
        return 1
    finally:
        if instance is not None:
            try:
                instance.release()
            except Exception:
                logger.warning("Could not release the single-instance mutex", exc_info=True)


if __name__ == "__main__":
    raise SystemExit(main())
