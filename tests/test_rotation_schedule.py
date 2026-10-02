from datetime import datetime, time

from automation.schedule import in_time_window, rotation_is_allowed


def test_daily_schedule_has_inclusive_start_and_exclusive_end():
    rotation = {"schedule_enabled": True, "schedule_start": "08:00", "schedule_end": "17:00"}

    assert not rotation_is_allowed(rotation, datetime(2026, 10, 1, 7, 59))
    assert rotation_is_allowed(rotation, datetime(2026, 10, 1, 8, 0))
    assert rotation_is_allowed(rotation, datetime(2026, 10, 1, 16, 59))
    assert not rotation_is_allowed(rotation, datetime(2026, 10, 1, 17, 0))


def test_overnight_quiet_hours_block_across_midnight():
    rotation = {
        "quiet_hours_enabled": True,
        "quiet_start": "22:00",
        "quiet_end": "08:00",
    }

    assert not rotation_is_allowed(rotation, datetime(2026, 10, 1, 22, 0))
    assert not rotation_is_allowed(rotation, datetime(2026, 10, 2, 7, 59))
    assert rotation_is_allowed(rotation, datetime(2026, 10, 2, 8, 0))


def test_equal_endpoints_define_no_active_window():
    assert not in_time_window(datetime(2026, 10, 1, 12, 0).time(), time(8, 0), time(8, 0))
    assert not rotation_is_allowed(
        {"schedule_enabled": True, "schedule_start": "08:00", "schedule_end": "08:00"},
        datetime(2026, 10, 1, 12, 0),
    )


def test_disabled_windows_allow_rotation():
    assert rotation_is_allowed({}, datetime(2026, 10, 1, 3, 0))
