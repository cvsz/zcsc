from camfrog.background_win32 import _commit_candidate_score


def test_only_exact_status_button_class_is_clickable():
    assert _commit_candidate_score("CButtonStatusTS") == 1000
    assert _commit_candidate_score("CButtonTS") == 0
    assert _commit_candidate_score("Button", "Open web") == 0
    assert _commit_candidate_score("CButtonTS", "Change Status") == 0
