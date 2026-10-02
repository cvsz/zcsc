import time
from automation.rotation import RotationWorker


def test_rotation_sends_first_change_immediately_then_waits():
    seen = []
    w = RotationWorker(seen.append)
    w.start(["A"], 1, "sequential")
    time.sleep(0.05)
    assert seen == ["A"]
    time.sleep(1.05)
    w.stop()
    assert seen == ["A", "A"]
