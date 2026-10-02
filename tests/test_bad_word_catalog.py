from camfrog.bad_word_catalog import (
    BAD_WORD_CATALOG,
    DEFAULT_BAD_WORD_TERMS,
    load_bad_word_catalog,
)


def test_starter_catalog_is_categorized_and_bilingual():
    categories = BAD_WORD_CATALOG["categories"]

    assert set(categories) == {
        "direct_profanity_anatomy",
        "bypass_phonetics_leet",
        "hate_speech_discrimination",
        "spam_gambling_substances",
    }
    assert all(category["title_en"] and category["title_th"] for category in categories.values())
    assert "เหี้ย" in DEFAULT_BAD_WORD_TERMS
    assert "fuck" in DEFAULT_BAD_WORD_TERMS
    assert len(DEFAULT_BAD_WORD_TERMS) >= 100


def test_catalog_loader_rejects_invalid_regex(tmp_path):
    path = tmp_path / "bad-word-catalog.json"
    path.write_text(
        '{"schema_version":1,"categories":{"test":{"terms":["term"]}},'
        '"obfuscation_patterns":[{"term":"term","pattern":"("}],"allowlist":[]}',
        encoding="utf-8",
    )

    try:
        load_bad_word_catalog(path)
    except ValueError as exc:
        assert "pattern" in str(exc)
    else:
        raise AssertionError("invalid regular expression was accepted")
