from camfrog.registry_status import RegistryStatusResult, extract_status_strings, merge_presets


def test_extract_multiline_and_dedupe():
    assert extract_status_strings("Sea THAIFIGHT\nBusy\nsea thaifight") == ["Sea THAIFIGHT", "Busy"]


def test_extract_json_list():
    assert extract_status_strings('["One", "Two", "One"]') == ["One", "Two"]


def test_merge_preserves_existing_order():
    assert merge_presets(["Busy", "Available"], ["busy", "Sea THAIFIGHT"]) == [
        "Busy", "Available", "Sea THAIFIGHT"
    ]


def test_result_has_diagnostics_defaults():
    r = RegistryStatusResult([], [])
    assert r.scanned_keys == 0
    assert r.candidate_values == 0
