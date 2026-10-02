import pytest
from automation.intervals import interval_to_seconds, seconds_to_interval, format_interval


def test_seconds_minutes_hours_conversion():
    assert interval_to_seconds(30, "seconds", minimum_seconds=5) == 30
    assert interval_to_seconds(2, "minutes", minimum_seconds=5) == 120
    assert interval_to_seconds(3, "hours", minimum_seconds=5) == 10800


def test_seconds_minimum_guard():
    assert interval_to_seconds(1, "seconds", minimum_seconds=5) == 5


def test_roundtrip_display_units():
    assert seconds_to_interval(45) == (45, "seconds")
    assert seconds_to_interval(120) == (2, "minutes")
    assert seconds_to_interval(7200) == (2, "hours")
    assert format_interval(45) == "45 seconds"


def test_invalid_unit():
    with pytest.raises(ValueError):
        interval_to_seconds(1, "days")
