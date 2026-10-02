import threading
import time
from automation.rotation import RotationWorker
from automation.marquee import marquee_delay_seconds


def test_rotation_sends_first_row_immediately_then_waits_between_rows():
    seen = []
    first_sent = threading.Event()
    second_sent = threading.Event()

    def apply(value):
        seen.append(value)
        (first_sent if len(seen) == 1 else second_sent).set()

    worker = RotationWorker(apply)
    worker.start(["one", "two", "three"], 1, "sequential")
    assert first_sent.wait(timeout=0.5)
    time.sleep(0.1)
    assert seen == ["one"]
    assert second_sent.wait(timeout=1.5)
    worker.stop()
    assert seen[:2] == ["one", "two"]


def test_rotation_restart_resets_to_first_preset():
    seen = []
    first = threading.Event()

    def apply(value):
        seen.append(value)
        first.set()

    worker = RotationWorker(apply)
    worker.start(["one", "two"], 1, "sequential")
    assert first.wait(timeout=0.5)
    worker.stop()
    first.clear()
    worker.start(["one", "two"], 1, "sequential")
    assert first.wait(timeout=0.5)
    worker.stop()
    assert seen == ["one", "one"]


def test_rotation_marquee_reapplies_same_row_between_rotation_ticks():
    seen = []
    first_frame = threading.Event()
    second_frame = threading.Event()

    def apply(value):
        seen.append(value)
        (first_frame if len(seen) == 1 else second_frame).set()

    worker = RotationWorker(apply)
    worker.start(
        ["one", "two"],
        2,
        "sequential",
        marquee_enabled=True,
        marquee_frame_interval_seconds=1,
    )
    assert first_frame.wait(timeout=0.5)
    assert second_frame.wait(timeout=1.5)
    worker.stop()

    assert seen == ["one", "one"]


def test_random_rotation_sends_one_nonempty_row_per_tick(monkeypatch):
    seen = []
    three_rows_sent = threading.Event()

    def apply_one(value):
        seen.append(value)
        if len(seen) == 3:
            three_rows_sent.set()

    monkeypatch.setattr("automation.rotation.random.shuffle", lambda values: values.reverse())
    worker = RotationWorker(apply_one)
    worker.start(["row 1", "", "row 3", "row 4"], 1, "random")
    completed = three_rows_sent.wait(timeout=5)
    worker.stop()

    assert completed
    assert seen == ["row 4", "row 3", "row 1"]


def test_progressive_marquee_delay_matches_five_character_flow():
    assert [
        marquee_delay_seconds(index, 5, minimum_interval_seconds=5, progressive=True)
        for index in range(5)
    ] == [5, 10, 15, 20, 25]


def test_marquee_delay_schedule_repeats_after_five_characters():
    assert marquee_delay_seconds(5, 5, minimum_interval_seconds=5, progressive=True) == 5


def test_marquee_delay_never_goes_below_the_send_guard():
    assert marquee_delay_seconds(0, 0, minimum_interval_seconds=5, progressive=True) == 5
