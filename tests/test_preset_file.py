import json

import pytest

from system.preset_file import format_preset_file_text, parse_preset_file_text


def test_versioned_json_import_and_export_round_trip_unicode():
    presets = ["Hello", "ยินดีต้อนรับ"]

    exported = format_preset_file_text(presets)

    assert json.loads(exported) == {"version": 1, "presets": presets}
    assert parse_preset_file_text(exported) == presets


def test_plain_text_is_one_preset_per_line():
    assert parse_preset_file_text("Hello\nสวัสดี\n") == ["Hello", "สวัสดี"]
    assert format_preset_file_text([" Hello ", ""], text_only=True) == "Hello\n"


def test_json_import_rejects_unknown_versions_and_non_string_values():
    with pytest.raises(ValueError, match="version"):
        parse_preset_file_text('{"version": 2, "presets": []}')
    with pytest.raises(ValueError, match="string"):
        parse_preset_file_text('{"version": 1, "presets": ["ok", 7]}')


def test_json_like_invalid_text_is_not_imported_as_a_preset():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_preset_file_text('{"presets":')


def test_json_root_must_contain_preset_list():
    with pytest.raises(ValueError, match="list of strings"):
        parse_preset_file_text('{"version": 1, "presets": null}')
