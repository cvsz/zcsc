from status_text import compose_two_lines, comparable_status


def test_two_lines_basic():
    assert compose_two_lines(["text1", "text2"]) == "text1\r\ntext2"


def test_one_line_when_second_empty():
    assert compose_two_lines(["text1", ""]) == "text1"


def test_preserves_blank_first_line_when_second_present():
    assert compose_two_lines(["", "text2"]) == "\r\ntext2"


def test_embedded_newline_inside_field_is_flattened():
    assert compose_two_lines(["a\nb", "c"]) == "a b\r\nc"


def test_comparison_normalizes_crlf_and_lf():
    assert comparable_status("a\r\nb") == comparable_status("a\nb")
