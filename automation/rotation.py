from __future__ import annotations

import inspect
import random
import threading
import time
from collections.abc import Callable
from datetime import datetime

from automation.schedule import rotation_is_allowed
from automation.marquee import marquee_delay_seconds


class RotationWorker:
    def __init__(self, apply_status: Callable[..., None], *, clock=None):
        self.apply_status = apply_status
        self.clock = clock
        try:
            self._accepts_cancellation = "cancelled" in inspect.signature(apply_status).parameters
        except (TypeError, ValueError):
            self._accepts_cancellation = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._idx = 0
        self._generation = 0

    def _monotonic(self) -> float:
        if self.clock is not None:
            return float(self.clock.monotonic())
        return time.monotonic()

    def _local_now(self) -> datetime:
        if self.clock is not None and hasattr(self.clock, "now_local"):
            return self.clock.now_local()
        return datetime.now().astimezone()

    def _wait_until(self, deadline: float) -> bool:
        """Wait against a monotonic deadline; return whether Stop was requested."""
        while not self._stop.is_set():
            remaining = deadline - self._monotonic()
            if remaining <= 0:
                return False
            if self._stop.wait(remaining):
                return True
        return True

    def start(
        self,
        presets: list[str],
        interval_seconds: int,
        mode: str,
        schedule: dict | None = None,
        *,
        marquee_enabled: bool = False,
        marquee_frame_interval_seconds: int = 10,
        marquee_progressive_delays: bool = False,
        minimum_interval_seconds: int = 1,
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

        def apply(value: str) -> None:
            if self._accepts_cancellation:
                cancelled = lambda: generation != self._generation or self._stop.is_set()
                self.apply_status(value, cancelled=cancelled)
            else:
                self.apply_status(value)

        def run() -> None:
            random_queue: list[str] = []
            previous_random: str | None = None
            while generation == self._generation and not self._stop.is_set():
                if not snapshot:
                    if self._wait_until(self._monotonic() + interval):
                        break
                    continue
                if rotation_is_allowed(schedule_snapshot, self._local_now()):
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
                        apply(value)
                    except Exception:
                        # Rotation must not die permanently because one apply failed.
                        pass
                    if marquee_enabled:
                        # Keep scrolling this same row until its normal rotation
                        # interval expires. Each frame is still a separate
                        # Camfrog status update and the controller enforces its
                        # minimum send spacing.
                        deadline = self._monotonic() + interval
                        frame_index = 0
                        while generation == self._generation and not self._stop.is_set():
                            remaining = deadline - self._monotonic()
                            if remaining <= 0:
                                break
                            delay = marquee_delay_seconds(
                                frame_index,
                                frame_interval,
                                minimum_interval_seconds=minimum_interval_seconds,
                                progressive=marquee_progressive_delays,
                            )
                            if self._stop.wait(min(delay, remaining)):
                                break
                            if deadline - self._monotonic() <= 0:
                                break
                            try:
                                apply(value)
                            except Exception:
                                pass
                            frame_index += 1
                        if generation != self._generation or self._stop.is_set():
                            break
                        continue
                # The first eligible row is sent immediately. Each subsequent
                # row waits the full configured delay after the previous apply.
                if self._wait_until(self._monotonic() + interval):
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
