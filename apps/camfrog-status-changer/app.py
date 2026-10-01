from __future__ import annotations

import logging
from tkinter import messagebox

from system.config_store import ConfigStore
from system.logging_setup import configure_logging
from system.single_instance import SingleInstance
from ui.dashboard import AppUI
from version import APP_NAME, VERSION


def main() -> int:
    configure_logging()
    log = logging.getLogger("camfrog_status")
    store = ConfigStore()
    store.ensure_defaults()
    startup_config = store.load()
    th = startup_config.get("ui", {}).get("language") == "TH"
    instance = SingleInstance()
    if not instance.acquire():
        try:
            messagebox.showinfo(APP_NAME, "Camfrog Status Changer กำลังทำงานอยู่แล้ว กรุณาตรวจ System Tray" if th else "Camfrog Status Changer is already running. Check the system tray.")
        except Exception:
            pass
        return 2
    try:
        app = AppUI(store=store)
        localized_name = "ตัวเปลี่ยนสถานะ Camfrog" if app.language_var.get() == "TH" else APP_NAME
        app.title(f"{localized_name} {VERSION}")
        app.mainloop()
        return 0
    except Exception:
        log.exception("Fatal application error")
        try:
            messagebox.showerror(APP_NAME, "โปรแกรมเกิดข้อผิดพลาดร้ายแรง กรุณาดู app.log ในโฟลเดอร์ config" if th else "The application encountered a fatal error. See app.log in the config folder.")
        except Exception:
            pass
        return 1
    finally:
        instance.release()


if __name__ == "__main__":
    raise SystemExit(main())
