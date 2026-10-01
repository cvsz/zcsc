import time
from automation.rotation import RotationWorker

def test_one_message_per_tick():
    seen=[]
    w=RotationWorker(seen.append)
    w.start(["one","two","three"],1,"sequential")
    time.sleep(1.15)
    w.stop()
    assert seen == ["one"]
