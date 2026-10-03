import unicodedata

import pytest

from status_styles import DEFAULT_PALETTE, marquee_frame, marquee_character_frame, apply_styles, random_color

def test_marquee_one_frame_per_call():
    a,n = marquee_frame("HELLO",0,8)
    b,n2 = marquee_frame("HELLO",n,8)
    assert n2 == n + 1
    assert a.startswith("HELLO")
    assert b != a

def test_multiline_preserved():
    v,n = marquee_frame("A\r\nB",0,8)
    assert "\r\n" in v

def test_marquee_character_frame_advances_one_visible_character():
    frames = []
    offset = 0
    for _ in range(5):
        frame, offset = marquee_character_frame("ABCDE", offset)
        frames.append(frame)
    assert frames == ["A", "B", "C", "D", "E"]

def test_marquee_character_frame_keeps_combining_marks_with_base():
    frame, next_offset = marquee_character_frame("e\u0301x", 0)
    assert frame == "e\u0301"
    assert next_offset == 1

def test_single_character_marquee_style_returns_one_character():
    value, next_offset, _ = apply_styles(
        "ABCDE", marquee_enabled=True, marquee_offset=2, marquee_single_character=True
    )
    assert value == "C"
    assert next_offset == 3

def test_color_template():
    v,_,color = apply_styles("HELLO", random_color_enabled=True, color_template="<c={color}>{text}</c>", palette=["#ABCDEF"])
    assert v == "<c=#ABCDEF>HELLO</c>"
    assert color == "#ABCDEF"

def test_style_disabled_is_identity():
    v,n,color = apply_styles("HELLO", random_color_enabled=False, marquee_enabled=False)
    assert v == "HELLO"
    assert color is None


@pytest.mark.parametrize(
    "template",
    [
        "[color={color}][/color]",  # Drops the status text.
        "{text}{text}",
        "{text.__class__}",
        "{text!r}",
        "{text:>10}",
        "{unknown}{text}",
        "{text",
        "text}",
        "{text}{color}{color}",
    ],
)
def test_invalid_color_template_falls_back_to_plain_text(template):
    value, _next_offset, color = apply_styles(
        "HELLO", random_color_enabled=True, color_template=template, palette=["#ABCDEF"]
    )

    assert value == "HELLO"
    assert color is None


def test_color_template_can_omit_optional_color_placeholder():
    value, _next_offset, color = apply_styles(
        "HELLO", random_color_enabled=True, color_template="<{text}>", palette=["#ABCDEF"]
    )

    assert value == "<HELLO>"
    assert color == "#ABCDEF"


def test_color_template_does_not_reinterpret_braces_in_status_text():
    value, _next_offset, color = apply_styles(
        "{color}", random_color_enabled=True, color_template="{text}", palette=["#ABCDEF"]
    )

    assert value == "{color}"
    assert color == "#ABCDEF"


@pytest.mark.parametrize("text", ["A", "กิข์", "ภาษาไทย", "A\nB", "👩\u200d💻", "👍🏽X", "🇹🇭X"])
@pytest.mark.parametrize("width", [4, 5, 28, 80])
def test_marquee_never_emits_blank_frame_for_nonblank_status(text, width):
    for offset in range(2 * (width + len(text))):
        frame, _next_offset = marquee_frame(text, offset, width=width)
        assert frame.strip()


@pytest.mark.parametrize("text", ["", "   ", "\n", "\r\n"])
def test_marquee_keeps_empty_and_whitespace_only_inputs_blank(text):
    frame, _next_offset = marquee_frame(text, 0, width=4)

    assert not frame.strip()


@pytest.mark.parametrize("text", ["กิข์", "ภาษาไทย", "👩\u200d💻X", "👍🏽X", "🇹🇭X"])
def test_marquee_keeps_unicode_grapheme_components_together(text):
    for offset in range(24):
        frame, _next_offset = marquee_frame(text, offset, width=4)
        visible = frame.strip()
        if not visible:
            continue
        first = visible[0]
        assert not unicodedata.category(first).startswith("M")
        assert first != "\u200d"
        if "\u200d" in visible:
            assert "👩\u200d💻" in visible
        if "🏽" in visible:
            assert "👍🏽" in visible


def test_random_color_rejects_invalid_palette_entries():
    assert random_color(["not-a-color", "#ABC", "red"]) in DEFAULT_PALETTE


def test_marquee_width_uses_safe_default_for_invalid_config_value():
    frame, _next_offset = marquee_frame("HELLO", 0, width="not-an-integer")

    assert frame.startswith("HELLO")


@pytest.mark.parametrize("width", [4, 5, 28, 80])
def test_marquee_supports_configured_width_bounds(width):
    frame, _next_offset = marquee_frame("HELLO", 0, width=width)

    assert len(frame) <= width
