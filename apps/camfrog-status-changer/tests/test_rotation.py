import time
from automation.rotation import RotationWorker


def test_rotation_waits_before_first_change():
    seen = []
    w = RotationWorker(seen.append)
    w.start(["A"], 1, "sequential")
    time.sleep(0.05)
    assert seen == []
    time.sleep(1.05)
    w.stop()
    assert seen and seen[0] == "A"
