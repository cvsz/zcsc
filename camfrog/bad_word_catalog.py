from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from system.tray import resource_path


def load_bad_word_catalog(path: str | Path | None = None) -> dict[str, Any]:
    catalog_path = Path(path) if path is not None else resource_path("bad_word_starters.json")
    with catalog_path.open("r", encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)
    if not isinstance(catalog, dict) or catalog.get("schema_version") != 1:
        raise ValueError("Unsupported bad-word starter catalog schema")

    categories = catalog.get("categories")
    if not isinstance(categories, dict) or not categories:
        raise ValueError("Bad-word starter catalog must define categories")
    for category_id, category in categories.items():
        if not isinstance(category_id, str) or not isinstance(category, dict):
            raise ValueError("Bad-word starter category is malformed")
        terms = category.get("terms")
        if not isinstance(terms, list) or any(not isinstance(term, str) or not term.strip() for term in terms):
            raise ValueError(f"Bad-word starter category has invalid terms: {category_id}")

    patterns = catalog.get("obfuscation_patterns", [])
    if not isinstance(patterns, list):
        raise ValueError("Bad-word obfuscation patterns must be a list")
    for entry in patterns:
        if not isinstance(entry, dict) or not isinstance(entry.get("term"), str):
            raise ValueError("Bad-word obfuscation pattern is malformed")
        try:
            re.compile(str(entry.get("pattern", "")), re.IGNORECASE)
        except re.error as exc:
            raise ValueError("Bad-word obfuscation pattern is invalid") from exc

    allowlist = catalog.get("allowlist", [])
    if not isinstance(allowlist, list) or any(not isinstance(term, str) or not term.strip() for term in allowlist):
        raise ValueError("Bad-word allowlist is malformed")
    return catalog


BAD_WORD_CATALOG = load_bad_word_catalog()
DEFAULT_BAD_WORD_TERMS = tuple(dict.fromkeys(
    term.strip()
    for category in BAD_WORD_CATALOG["categories"].values()
    for term in category["terms"]
))
DEFAULT_BAD_WORD_ALLOWLIST = tuple(BAD_WORD_CATALOG["allowlist"])
DEFAULT_BAD_WORD_PATTERNS = tuple(
    (entry["term"], re.compile(entry["pattern"], re.IGNORECASE))
    for entry in BAD_WORD_CATALOG["obfuscation_patterns"]
)
