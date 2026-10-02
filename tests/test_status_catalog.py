from status_catalog import (
    DEFAULT_STANDARD_STATUS_ID,
    STANDARD_STATUSES,
    find_standard_status_by_label,
    get_standard_status,
    filter_standard_statuses,
    STANDARD_STATUS_CATEGORY_BY_ID,
    standard_status_dropdown_values,
)


def test_catalog_has_50_complete_bilingual_unique_statuses():
    assert len(STANDARD_STATUSES) == 50
    assert len({status.id for status in STANDARD_STATUSES}) == 50
    assert len({status.en for status in STANDARD_STATUSES}) == 50
    assert len({status.th for status in STANDARD_STATUSES}) == 50
    assert len(standard_status_dropdown_values("EN")) == 50
    assert len(standard_status_dropdown_values("TH")) == 50
    assert all(status.en.strip() and status.th.strip() for status in STANDARD_STATUSES)
    assert all(len(status.en) <= 160 and len(status.th) <= 160 for status in STANDARD_STATUSES)
    assert set(STANDARD_STATUS_CATEGORY_BY_ID) == {status.id for status in STANDARD_STATUSES}


def test_catalog_selects_expected_language_and_resolves_dropdown_label():
    status = get_standard_status("welcome")
    assert status is not None
    assert status.text_for("EN") == "Welcome everyone"
    assert status.text_for("TH") == "ยินดีต้อนรับทุกคน"
    assert status.dropdown_label("EN") == "Welcome everyone"
    assert status.dropdown_label("TH") == "ยินดีต้อนรับทุกคน"
    assert find_standard_status_by_label(status.dropdown_label("EN"), "EN") == status
    assert find_standard_status_by_label(status.dropdown_label("TH"), "TH") == status


def test_unknown_catalog_id_is_not_resolved():
    assert get_standard_status("not-a-standard-status") is None
    assert get_standard_status(DEFAULT_STANDARD_STATUS_ID).en == "Available"


def test_catalog_search_categories_and_favorites_filter_results():
    assert [status.id for status in filter_standard_statuses("welcome", "all")] == ["welcome"]
    assert all(status.id in STANDARD_STATUS_CATEGORY_BY_ID for status in filter_standard_statuses(category="work_study"))
    assert [status.id for status in filter_standard_statuses(category="favorites", favorite_ids=["welcome", "unknown"])] == ["welcome"]
