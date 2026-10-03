from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence

from camfrog.registry_status import read_camfrog_custom_statuses
from system.config_store import ConfigStore


_EMAIL_RE = re.compile(
    r"(?<![\w.+-])[\w.!#$%&'*+/=?^`{|}~-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])",
    re.IGNORECASE,
)
_URL_RE = re.compile(r"\b(?:https?://|www\.)[^\s<>\"']+", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d().\s-]{5,}\d(?!\w)")


def _redact_text(value: str) -> str:
    value = _EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    value = _URL_RE.sub("[REDACTED_URL]", value)

    def redact_phone(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        return "[REDACTED_PHONE]" if len(digits) >= 7 else match.group(0)

    return _PHONE_RE.sub(redact_phone, value)


def _redact_dump_values(value):
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, list):
        return [_redact_dump_values(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_dump_values(item) for key, item in value.items()}
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write Camfrog status-history registry diagnostics")
    parser.add_argument(
        "--redact",
        action="store_true",
        help="redact email addresses, phone-like numbers, and URLs before writing",
    )
    args = parser.parse_args(argv)

    try:
        store = ConfigStore()
    except Exception as exc:
        print(f"Could not initialize registry dump storage ({type(exc).__name__})", file=sys.stderr)
        return 1

    try:
        result = read_camfrog_custom_statuses()
    except Exception as exc:
        print(f"Registry scan failed ({type(exc).__name__}); no dump was written", file=sys.stderr)
        return 1

    if result.scanned_keys == 0:
        print("Registry scan failed: no registry keys were scanned", file=sys.stderr)
        return 1

    payload = {
        "scanned_keys": result.scanned_keys,
        "candidate_values": result.candidate_values,
        "statuses": [
            {
                "text": item.text,
                "source": item.source,
                "value_name": item.value_name,
                "value_type": item.value_type,
            }
            for item in (result.history or [])
        ],
    }
    if args.redact:
        payload = _redact_dump_values(payload)
    try:
        path = store.dir / "camfrog-history-sources-safe.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        print(f"Could not write registry dump ({type(exc).__name__}); check local storage access", file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
