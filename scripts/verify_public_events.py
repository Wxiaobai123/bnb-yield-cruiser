from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.public_events import parse_hodler_detail, parse_launchpool_detail


def main() -> None:
    fixture_path = Path("data/announcement_fixtures.json")
    raw = json.loads(fixture_path.read_text())
    now = datetime(2026, 3, 10, 0, 0, tzinfo=timezone.utc)

    launchpool = parse_launchpool_detail(
        raw["launchpool"]["title"],
        raw["launchpool"]["url"],
        raw["launchpool"]["text"],
        now=now,
    )
    hodler = parse_hodler_detail(
        raw["hodler"]["title"],
        raw["hodler"]["url"],
        raw["hodler"]["text"],
        now=now,
    )

    print(launchpool.to_dict() if hasattr(launchpool, "to_dict") else launchpool)
    print(hodler.to_dict() if hasattr(hodler, "to_dict") else hodler)


if __name__ == "__main__":
    main()
