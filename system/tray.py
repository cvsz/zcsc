from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

log = logging.getLogger(__name__)


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / name


class TrayController:
    def __init__(self, app):
        self.app = app
        self._icon = None
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> bool:
        if self.running:
            return True
        try:
            import pystray
            from PIL import Image

            icon_path = resource_path("app.ico")
            if not icon_path.exists():
                log.warning("Tray icon not found: %s", icon_path)
                return False

            image = Image.open(icon_path)
            menu = pystray.Menu(
                pystray.MenuItem("Show", lambda _icon, _item: self.app.after(0, self.show)),
                pystray.MenuItem("Quit", lambda _icon, _item: self.app.after(0, self.quit)),
            )
            self._icon = pystray.Icon("CamfrogStatusChanger", image, "Camfrog Status Changer", menu)
            self._thread = threading.Thread(target=self._icon.run, daemon=True, name="camfrog-tray")
            self._thread.start()
            return True
        except Exception:
            log.exception("Failed to start system tray")
            self._icon = None
            self._thread = None
            return False

    def show(self) -> None:
        try:
            self.app.deiconify()
            self.app.lift()
            self.app.focus_force()
        except Exception:
            log.exception("Failed to restore app from tray")

    def hide(self) -> None:
        if self.start():
            self.app.withdraw()

    def quit(self) -> None:
        try:
            if self._icon:
                self._icon.stop()
        finally:
            self._icon = None
            self.app.destroy()
