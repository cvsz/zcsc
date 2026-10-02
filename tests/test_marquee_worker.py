import threading

from automation.marquee import MarqueeWorker


def test_marquee_worker_reapplies_one_message_until_stopped():
    frames = []
    first = threading.Event()
    second = threading.Event()

    def apply(value):
        frames.append(value)
        (first if len(frames) == 1 else second).set()

    worker = MarqueeWorker(apply)
    worker.start("same status", 1)
    assert first.wait(timeout=0.5)
    assert second.wait(timeout=1.5)
    worker.stop()

    assert frames == ["same status", "same status"]
    assert worker.running is False
