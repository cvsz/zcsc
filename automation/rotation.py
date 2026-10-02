from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable
from datetime import datetime

from automation.schedule import rotation_is_allowed


class RotationWorker:
    def __init__(self, apply_status: Callable[[str], None]):
        self.apply_status = apply_status
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._idx = 0
        self._generation = 0

    def start(
        self,
        presets: list[str],
        interval_seconds: int,
        mode: str,
        schedule: dict | None = None,
        *,
        marquee_enabled: bool = False,
        marquee_frame_interval_seconds: int = 10,
    ) -> None:
        self.stop()
        self._stop.clear()
        self._generation += 1
        self._idx = 0  # each Start begins at preset #1
        generation = self._generation
        snapshot = tuple(x for x in presets if x)
        schedule_snapshot = dict(schedule or {})
        interval = max(1, int(interval_seconds))
        frame_interval = max(1, int(marquee_frame_interval_seconds))
        mode = mode if mode in {"sequential", "random"} else "sequential"

        def run() -> None:
            random_queue: list[str] = []
            previous_random: str | None = None
            while generation == self._generation and not self._stop.is_set():
                if not snapshot:
                    if self._stop.wait(interval):
                        break
                    continue
                if rotation_is_allowed(schedule_snapshot, datetime.now()):
                    if mode == "random":
                        if not random_queue:
                            random_queue = list(snapshot)
                            random.shuffle(random_queue)
                            if len(random_queue) > 1 and random_queue[0] == previous_random:
                                random_queue[0], random_queue[1] = random_queue[1], random_queue[0]
                        value = random_queue.pop(0)
                        previous_random = value
                    else:
                        value = snapshot[self._idx % len(snapshot)]
                        self._idx += 1
                    try:
                        self.apply_status(value)
                    except Exception:
                        # Rotation must not die permanently because one apply failed.
                        pass
                    if marquee_enabled:
                        # Keep scrolling this same row until its normal rotation
                        # interval expires. Each frame is still a separate
                        # Camfrog status update and the controller enforces its
                        # minimum send spacing.
                        deadline = time.monotonic() + interval
                        while generation == self._generation and not self._stop.is_set():
                            remaining = deadline - time.monotonic()
                            if remaining <= 0:
                                break
                            if self._stop.wait(min(frame_interval, remaining)):
                                break
                            if deadline - time.monotonic() <= 0:
                                break
                            try:
                                self.apply_status(value)
                            except Exception:
                                pass
                        if generation != self._generation or self._stop.is_set():
                            break
                        continue
                # The first eligible row is sent immediately. Each subsequent
                # row waits the full configured delay after the previous apply.
                if self._stop.wait(interval):
                    break

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
