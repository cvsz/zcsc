from __future__ import annotations
import random
from dataclasses import dataclass

DEFAULT_COLOR_MARKERS = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚪"]

@dataclass
class StyleState:
    marquee_offset: int = 0


def random_color(palette: list[str] | None = None) -> str:
    values = [x.strip() for x in (palette or DEFAULT_COLOR_MARKERS) if str(x).strip()]
    values = [x for x in values if not (x.startswith("#") and len(x) in {4, 7, 9})]
    return random.choice(values or DEFAULT_COLOR_MARKERS)


def marquee_frame(text: str, offset: int, width: int = 28) -> tuple[str, int]:
    width = max(4, int(width))
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    for line in lines:
        if not line:
            out.append("")
            continue
        if len(line) == 1:
            out.append(line)
            continue
        sep = " • "
        cycle = line + sep
        pos = int(offset) % len(cycle)
        rotated = cycle[pos:] + cycle[:pos]
        frame_len = min(width, max(len(line), 4))
        repeated = (rotated * ((frame_len // len(rotated)) + 2))[:frame_len]
        out.append(repeated)
    return "\r\n".join(out), int(offset) + 1


def apply_styles(text: str, *, random_color_enabled: bool = False, marquee_enabled: bool = False, marquee_offset: int = 0, marquee_width: int = 28, color_template: str | None = None, palette: list[str] | None = None) -> tuple[str, int, str | None]:
    value = text
    next_offset = marquee_offset
    if marquee_enabled:
        value, next_offset = marquee_frame(value, marquee_offset, marquee_width)
    chosen = None
    if random_color_enabled:
        chosen = random_color(palette)
        value = f"{chosen} {value}"
    return value, next_offset, chosen
