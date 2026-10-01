from __future__ import annotations


def normalize_newlines(value: str) -> str:
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def compose_two_lines(lines) -> str:
    values = [normalize_newlines(str(x).replace("\x00", "")).replace("\n", " ") for x in list(lines)[:2]]
    values += [""] * (2 - len(values))
    while values and not values[-1]:
        values.pop()
    return "\r\n".join(values)


def comparable_status(value: str) -> str:
    return normalize_newlines(value).strip()
