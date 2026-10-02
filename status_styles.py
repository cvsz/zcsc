from __future__ import annotations
import random
import re
from dataclasses import dataclass

DEFAULT_PALETTE = ["#FF3B30","#FF9500","#FFCC00","#34C759","#00C7BE","#0A84FF","#5E5CE6","#BF5AF2","#FF2D55"]

@dataclass
class StyleState:
    marquee_offset: int = 0

def random_color(palette: list[str] | None = None) -> str:
    values = [x.strip() for x in (palette or DEFAULT_PALETTE) if str(x).strip()]
    return random.choice(values or DEFAULT_PALETTE)

def marquee_frame(text: str, offset: int, width: int = 28) -> tuple[str, int]:
    """Return one deterministic marquee frame and next offset.
    Newlines are preserved by animating each non-empty line independently.
    """
    width = max(4, int(width))
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out = []
    for line in lines:
        if not line:
            out.append("")
            continue
        padded = (" " * width) + line + (" " * width)
        cycle = len(line) + width
        # Offset zero should show the start of the user's text immediately,
        # not a blank padding frame. The full cycle still leaves space for the
        # text to enter/leave before it loops back around.
        pos = (offset + width) % max(1, cycle)
        window = (padded + padded)[pos:pos+width]
        out.append(window.rstrip())
    return "\r\n".join(out), offset + 1

def apply_styles(
    text: str,
    *,
    random_color_enabled: bool = False,
    custom_color_enabled: bool = False,
    custom_color: str = "#00C7BE",
    marquee_enabled: bool = False,
    marquee_offset: int = 0,
    marquee_width: int = 28,
    color_template: str = "[color={color}]{text}[/color]",
    palette: list[str] | None = None,
) -> tuple[str, int, str | None]:
    value = text
    next_offset = marquee_offset
    if marquee_enabled:
        value, next_offset = marquee_frame(value, marquee_offset, marquee_width)
    chosen = None
    if custom_color_enabled or random_color_enabled:
        if custom_color_enabled:
            candidate = str(custom_color).strip().upper()
            chosen = candidate if re.fullmatch(r"#[0-9A-F]{6}", candidate) else "#00C7BE"
        else:
            colors = [str(x).strip().upper() for x in (palette or DEFAULT_PALETTE)]
            colors = [x for x in colors if re.fullmatch(r"#[0-9A-F]{6}", x)]
            chosen = random.choice(colors or DEFAULT_PALETTE)
        # User-configurable template; malformed templates fail closed to plain text.
        try:
            value = color_template.format(color=chosen, text=value)
        except Exception:
            pass
    return value, next_offset, chosen
