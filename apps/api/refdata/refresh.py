"""Rafraichit le snapshot refdata depuis ByMykel/CSGO-API.

Usage : python -m refdata.refresh
"""

import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

REPO = "ByMykel/CSGO-API"
BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/public/api/en"
API_COMMIT_URL = f"https://api.github.com/repos/{REPO}/commits/{BRANCH}"

SNAPSHOT_DIR = Path(__file__).parent / "snapshot"
FILES = ["skins.json", "collections.json"]


def _fetch_json(url: str) -> dict | list:
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def refresh() -> None:
    SNAPSHOT_DIR.mkdir(exist_ok=True)

    for filename in FILES:
        data = _fetch_json(f"{RAW_BASE}/{filename}")
        (SNAPSHOT_DIR / filename).write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )

    commit = _fetch_json(API_COMMIT_URL)
    metadata = {
        "source": f"https://github.com/{REPO}",
        "branch": BRANCH,
        "commit_sha": commit["sha"],
        "commit_date": commit["commit"]["author"]["date"],
        "fetched_at": datetime.now(UTC).isoformat(),
        "files": FILES,
    }
    (SNAPSHOT_DIR / "SNAPSHOT_METADATA.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    refresh()
