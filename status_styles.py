from __future__ import annotations
import random
import re
import unicodedata
from dataclasses import dataclass

DEFAULT_PALETTE = ["#FF3B30","#FF9500","#FFCC00","#34C759","#00C7BE","#0A84FF","#5E5CE6","#BF5AF2","#FF2D55"]
DEFAULT_MARQUEE_WIDTH = 28


def _validated_palette(palette: list[str] | None = None) -> list[str]:
    """Return valid six-digit colors, falling back to the built-in palette."""
    try:
        source = DEFAULT_PALETTE if palette is None else palette
        candidates = list(source)
    except (TypeError, ValueError):
        candidates = []
    colors = [
        str(value).strip().upper()
        for value in candidates
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", str(value).strip())
    ]
    return colors or list(DEFAULT_PALETTE)


def _safe_width(width: object) -> int:
    try:
        value = int(width)
    except (TypeError, ValueError, OverflowError):
        value = DEFAULT_MARQUEE_WIDTH
    return min(80, max(4, value))


def _grapheme_clusters(text: str) -> list[str]:
    """Group combining marks, emoji modifiers, flags, and ZWJ sequences."""
    clusters: list[str] = []
    regional_indicator_count = 0
    for char in text:
        codepoint = ord(char)
        category = unicodedata.category(char)
        is_mark = category.startswith("M")
        is_emoji_modifier = 0x1F3FB <= codepoint <= 0x1F3FF
        is_emoji_tag = 0xE0020 <= codepoint <= 0xE007F
        is_regional_indicator = 0x1F1E6 <= codepoint <= 0x1F1FF

        if not clusters:
            clusters.append(char)
            regional_indicator_count = 1 if is_regional_indicator else 0
        elif is_mark or is_emoji_modifier or is_emoji_tag or char == "\u200d" or clusters[-1].endswith("\u200d"):
            clusters[-1] += char
            regional_indicator_count = 0
        elif is_regional_indicator:
            if regional_indicator_count % 2 == 1:
                clusters[-1] += char
                regional_indicator_count += 1
            else:
                clusters.append(char)
                regional_indicator_count = 1
        else:
            clusters.append(char)
            regional_indicator_count = 0
    return clusters


def color_template_error(template: object) -> str | None:
    """Validate the small, non-executable color-template placeholder syntax."""
    if not isinstance(template, str):
        return "template must be text"

    counts = {"text": 0, "color": 0}
    index = 0
    while index < len(template):
        char = template[index]
        if char == "}":
            return "unmatched closing brace"
        if char != "{":
            index += 1
            continue

        closing = template.find("}", index + 1)
        if closing < 0:
            return "unmatched opening brace"
        field = template[index + 1 : closing]
        if field not in counts:
            return "unsupported placeholder"
        counts[field] += 1
        if counts[field] > 1:
            return f"placeholder {field} may appear only once"
        index = closing + 1

    if counts["text"] != 1:
        return "template must contain exactly one {text} placeholder"
    return None


def _render_color_template(template: str, text: str, color: str) -> str:
    """Render validated placeholders without rescanning substituted values."""
    rendered: list[str] = []
    index = 0
    while index < len(template):
        opening = template.find("{", index)
        if opening < 0:
            rendered.append(template[index:])
            break
        rendered.append(template[index:opening])
        closing = template.index("}", opening + 1)
        field = template[opening + 1 : closing]
        rendered.append(text if field == "text" else color)
        index = closing + 1
    return "".join(rendered)

@dataclass
class StyleState:
    marquee_offset: int = 0

def random_color(palette: list[str] | None = None) -> str:
    return random.choice(_validated_palette(palette))

def marquee_frame(text: str, offset: int, width: int = 28) -> tuple[str, int]:
    """Return one deterministic marquee frame and next offset.
    Newlines are preserved by animating each non-empty line independently.
    """
    width = _safe_width(width)
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    clusters_by_line: list[list[str]] = []
    for line in lines:
        clusters_by_line.append(_grapheme_clusters(line))

    def render(frame_offset: int) -> str:
        out = []
        for clusters in clusters_by_line:
            if not clusters:
                out.append("")
                continue
            padded = ([" "] * width) + clusters + ([" "] * width)
            cycle = len(clusters) + width
            # Offset zero shows the status immediately; the rest of the cycle
            # lets the complete grapheme sequence enter and leave the window.
            pos = (frame_offset + width) % max(1, cycle)
            window = (padded + padded)[pos : pos + width]
            out.append("".join(window).rstrip())
        return "\r\n".join(out)

    frame = render(offset)
    if any(line.strip() for line in lines):
        # A short status can be entirely outside the viewport for several
        # offsets. Skip those frames so callers never send an empty status.
        for skipped in range(width + 1):
            frame = render(offset + skipped)
            if frame.strip():
                return frame, offset + skipped + 1
    return frame, offset + 1


def marquee_character_frame(text: str, offset: int) -> tuple[str, int]:
    """Return one visible Unicode base character with its combining marks."""
    units: list[str] = []
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    for cluster in _grapheme_clusters(normalized):
        if cluster.isspace():
            continue
        units.append(cluster)
    if not units:
        return "", offset + 1
    return units[offset % len(units)], offset + 1

def apply_styles(
    text: str,
    *,
    random_color_enabled: bool = False,
    custom_color_enabled: bool = False,
    custom_color: str = "#00C7BE",
    marquee_enabled: bool = False,
    marquee_offset: int = 0,
    marquee_width: int = 28,
    marquee_single_character: bool = False,
    color_template: str = "[color={color}]{text}[/color]",
    palette: list[str] | None = None,
) -> tuple[str, int, str | None]:
    value = text
    next_offset = marquee_offset
    if marquee_enabled:
        if marquee_single_character:
            value, next_offset = marquee_character_frame(value, marquee_offset)
        else:
            value, next_offset = marquee_frame(value, marquee_offset, marquee_width)
    chosen = None
    if custom_color_enabled or random_color_enabled:
        if custom_color_enabled:
            candidate = str(custom_color).strip().upper()
            chosen = candidate if re.fullmatch(r"#[0-9A-F]{6}", candidate) else "#00C7BE"
        else:
            chosen = random_color(palette)
        if color_template_error(color_template):
            chosen = None
        else:
            # Replace only the validated literal tokens; never evaluate a
            # Python format field supplied by the user.
            value = _render_color_template(color_template, value, chosen or "")
    return value, next_offset, chosen
