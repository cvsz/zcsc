from camfrog.controller import CamfrogController


def config():
    return {
        "advanced": {"max_status_length": 5, "minimum_interval_seconds": 5},
        "camfrog": {"executable": ""},
        "target": {},
        "status": {"presets": []},
    }


def test_empty_status_rejected_without_touching_windows():
    r = CamfrogController(config()).set_status("  ")
    assert not r.ok
    assert "empty" in r.message.lower()


def test_oversized_status_rejected_without_touching_windows():
    r = CamfrogController(config()).set_status("123456")
    assert not r.ok
    assert "maximum" in r.message.lower()
