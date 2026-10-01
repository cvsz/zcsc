from __future__ import annotations

import random
import threading
import logging
from collections.abc import Callable

log = logging.getLogger(__name__)


class RotationWorker:
    def __init__(self, apply_status: Callable[[str], None]):
        self.apply_status = apply_status
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._idx = 0
        self._generation = 0

    def start(self, presets: list[str], interval_seconds: int, mode: str) -> None:
        self.stop()
        self._stop.clear()
        self._generation += 1
        self._idx = 0
        generation = self._generation
        snapshot = tuple(x for x in presets if x)
        interval = max(1, int(interval_seconds))
        mode = mode if mode in {"sequential", "random"} else "sequential"

        def run() -> None:
            while generation == self._generation and not self._stop.wait(interval):
                if not snapshot:
                    continue
                if mode == "random":
                    value = random.choice(snapshot)
                else:
                    value = snapshot[self._idx % len(snapshot)]
                    self._idx += 1
                try:
                    self.apply_status(value)
                except Exception:
                    log.exception("Rotation apply failed")

        self._thread = threading.Thread(target=run, daemon=True, name="status-rotation")
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
