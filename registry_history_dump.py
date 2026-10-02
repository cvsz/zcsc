from __future__ import annotations

import json

from camfrog.registry_status import read_camfrog_custom_statuses
from system.config_store import ConfigStore


def main() -> int:
    store = ConfigStore()
    result = read_camfrog_custom_statuses()
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
    path = store.dir / "camfrog-history-sources-safe.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
