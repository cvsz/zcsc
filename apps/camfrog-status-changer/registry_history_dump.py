from __future__ import annotations

import json
import os
from pathlib import Path

from camfrog.registry_status import read_camfrog_custom_statuses


def main() -> int:
    values = read_camfrog_custom_statuses()
    report = [
        {
            "text": item.text,
            "source": item.source,
            "value_name": item.value_name,
        }
        for item in values
    ]

    out_dir = Path(os.getenv("APPDATA") or Path.home()) / "CamfrogStatusChanger"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "camfrog-history-sources-safe.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Found {len(report)} status values")
    print(f"Report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
