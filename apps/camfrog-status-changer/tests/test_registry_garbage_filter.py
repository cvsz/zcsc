from camfrog.registry_status import extract_status_strings


def test_binary_like_registry_dump_does_not_import_garbage():
    values = [
        "Sea THAIFIGHT", "ZEAZDEV COMPANY LIMITED", "Busy", "Available",
        "1050", "0", "1366", "639", "1790823392",
        "6ED6A81CF36BA876C4F7085389A5E7C5", "seaza@msn.com",
        "X*\\x1e1+u!4y$$T~", "=}W", "5X.g",
    ]
    result = []
    for value in values:
        result.extend(extract_status_strings(value))
    assert "Sea THAIFIGHT" in result
    assert "ZEAZDEV COMPANY LIMITED" in result
    assert "Busy" in result
    assert "Available" in result
    assert "1050" not in result
    assert "seaza@msn.com" not in result
    assert "6ED6A81CF36BA876C4F7085389A5E7C5" not in result
