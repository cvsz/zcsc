from status_styles import marquee_frame, apply_styles

def test_marquee_advances_without_leading_space_dependency():
    a,n=marquee_frame("ZEAZDEV",0,8)
    b,_=marquee_frame("ZEAZDEV",n,8)
    assert a != b
    assert not a.startswith(" ")

def test_color_marker_is_plain_text():
    out,_,chosen=apply_styles("HELLO",random_color_enabled=True,palette=["🔴"])
    assert chosen=="🔴"
    assert out=="🔴 HELLO"
    assert "[color=" not in out
