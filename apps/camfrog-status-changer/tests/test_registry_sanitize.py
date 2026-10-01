from camfrog.registry_status import _clean_status


def test_accept_human_statuses():
    assert _clean_status("Sea THAIFIGHT") == "Sea THAIFIGHT"
    assert _clean_status("ZEAZDEV COMPANY LIMITED") == "ZEAZDEV COMPANY LIMITED"
    assert _clean_status("Busy") == "Busy"
    assert _clean_status("Available") == "Available"


def test_reject_metadata_and_sensitive_looking_values():
    bad = [
        "1050", "0", "1366", "1790823392",
        "6ED6A81CF36BA876C4F7085389A5E7C5",
        "seaza@msn.com", "X*\\x1e1+u!4y$$T~", 'p)e6`yϞc~ykGн',
    ]
    for value in bad:
        assert _clean_status(value) is None
