from __future__ import annotations

UNIT_SECONDS = {"seconds": 1, "minutes": 60, "hours": 3600}


def interval_to_seconds(amount: int | str, unit: str, minimum_seconds: int = 5) -> int:
    try:
        value = int(str(amount).strip())
    except (TypeError, ValueError):
        raise ValueError("Interval must be a whole number")
    if value < 1:
        raise ValueError("Interval must be at least 1")
    if unit not in UNIT_SECONDS:
        raise ValueError(f"Unsupported interval unit: {unit}")
    return max(minimum_seconds, value * UNIT_SECONDS[unit])


def seconds_to_interval(seconds: int) -> tuple[int, str]:
    seconds = max(1, int(seconds))
    if seconds >= 3600 and seconds % 3600 == 0:
        return seconds // 3600, "hours"
    if seconds >= 60 and seconds % 60 == 0:
        return seconds // 60, "minutes"
    return seconds, "seconds"


def format_interval(seconds: int) -> str:
    amount, unit = seconds_to_interval(seconds)
    return f"{amount} {unit}"
