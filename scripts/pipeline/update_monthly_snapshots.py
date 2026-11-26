#!/usr/bin/env python3
"""Validate and normalise the curated monthly snapshot layer.

Process
-------
1. Read each official publication listed in a snapshot's ``source.url``.
2. Transcribe only published figures into that snapshot's ``metrics[].values``.
3. Set ``last_updated`` to the month/day the source was checked.
4. Run ``python scripts/pipeline/update_monthly_snapshots.py``.
5. Regenerate the site with ``python scripts/pipeline/page_generator.py``.

The script stamps a shared schema version, derives latest values and YoY
changes, validates required source/period/value fields, and refuses to write
any file containing mock, demo, random or placeholder values.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from monthly_snapshots import BADGE_TEXT, ROOT, SNAPSHOT_DIR, load_all, normalise, validate

FORBIDDEN = ("mock", "demo", "placeholder", "random", "indicative", "sample data")


def main() -> int:
    snapshots = load_all()
    if not snapshots:
        print(f"No monthly snapshots found in {SNAPSHOT_DIR.relative_to(ROOT)}")
        return 1

    failures = []
    for dataset_id, snapshot in snapshots.items():
        path = ROOT / snapshot["_path"]
        raw = path.read_text(encoding="utf-8")
        lowered = raw.lower()
        banned = [word for word in FORBIDDEN if word in lowered]
        if banned:
            failures.append(f"{dataset_id}: forbidden value language {banned}")
            continue

        errors = validate(snapshot)
        if errors:
            failures.append(f"{dataset_id}: {'; '.join(errors)}")
            continue

        normalised = normalise(snapshot)
        normalised.pop("_path", None)
        path.write_text(json.dumps(normalised, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print(f"[OK] {dataset_id}: {len(normalised['metrics'])} metrics, last updated {normalised['last_updated']}")

    if failures:
        print("\nSnapshot validation failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(f"\n[SUCCESS] {len(snapshots)} monthly snapshots validated. Badge: {BADGE_TEXT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
