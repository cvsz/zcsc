from __future__ import annotations

import threading
from collections.abc import Callable


class MarqueeWorker:
    """Repeat one status so its generated marquee frame advances over time."""

    def __init__(self, apply_frame: Callable[[str], None]):
        self.apply_frame = apply_frame
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._generation = 0

    def start(self, text: str, interval_seconds: int) -> None:
        self.stop()
        self._stop.clear()
        self._generation += 1
        generation = self._generation
        value = str(text)
        interval = max(1, int(interval_seconds))

        def run() -> None:
            while generation == self._generation and not self._stop.is_set():
                try:
                    self.apply_frame(value)
                except Exception:
                    # A temporary Camfrog/UI error should not kill the worker.
                    pass
                if self._stop.wait(interval):
                    break

        self._thread = threading.Thread(target=run, daemon=True, name="status-marquee")
        self._thread.start()

    def stop(self) -> None:
        self._generation += 1
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._thread = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())
