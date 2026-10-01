from camfrog.registry_status import RELEVANT_TERMS


def test_profile_is_not_a_status_source_term():
    assert "profile" not in RELEVANT_TERMS
    assert "status" in RELEVANT_TERMS
    assert "custom" in RELEVANT_TERMS
