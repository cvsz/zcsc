from __future__ import annotations

from datetime import datetime, time


def parse_hhmm(value: str, default: str) -> time:
    try:
        hour_text, minute_text = str(value).split(":", 1)
        hour, minute = int(hour_text), int(minute_text)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour, minute)
    except (TypeError, ValueError):
        pass
    hour, minute = (int(part) for part in default.split(":"))
    return time(hour, minute)


def in_time_window(now: time, start: time, end: time) -> bool:
    """Check a local daily window; end is exclusive and overnight spans midnight."""
    if start == end:
        return False
    if start < end:
        return start <= now < end
    return now >= start or now < end


def rotation_is_allowed(rotation: dict, now: datetime | None = None) -> bool:
    current = (now or datetime.now()).time().replace(second=0, microsecond=0)
    if rotation.get("schedule_enabled"):
        start = parse_hhmm(rotation.get("schedule_start", "08:00"), "08:00")
        end = parse_hhmm(rotation.get("schedule_end", "23:00"), "23:00")
        if not in_time_window(current, start, end):
            return False
    if rotation.get("quiet_hours_enabled"):
        start = parse_hhmm(rotation.get("quiet_start", "22:00"), "22:00")
        end = parse_hhmm(rotation.get("quiet_end", "08:00"), "08:00")
        if in_time_window(current, start, end):
            return False
    return True
