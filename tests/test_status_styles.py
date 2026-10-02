from status_styles import marquee_frame, apply_styles

def test_marquee_one_frame_per_call():
    a,n = marquee_frame("HELLO",0,8)
    b,n2 = marquee_frame("HELLO",n,8)
    assert n2 == n + 1
    assert a.startswith("HELLO")
    assert b != a

def test_multiline_preserved():
    v,n = marquee_frame("A\r\nB",0,8)
    assert "\r\n" in v

def test_color_template():
    v,_,color = apply_styles("HELLO", random_color_enabled=True, color_template="<c={color}>{text}</c>", palette=["#ABCDEF"])
    assert v == "<c=#ABCDEF>HELLO</c>"
    assert color == "#ABCDEF"

def test_style_disabled_is_identity():
    v,n,color = apply_styles("HELLO", random_color_enabled=False, marquee_enabled=False)
    assert v == "HELLO"
    assert color is None
