from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .snapshot import stable_json


def status_payload(breaking_count: int, non_breaking_count: int) -> dict[str, Any]:
    ok = breaking_count == 0
    return {
        "schemaVersion": 1,
        "label": "MCP contract",
        "message": "verified" if ok else "drift detected",
        "color": "brightgreen" if ok else "red",
        "breaking": breaking_count,
        "non_breaking": non_breaking_count,
    }


def write_status(path: Path, breaking_count: int, non_breaking_count: int) -> dict[str, Any]:
    payload = status_payload(breaking_count, non_breaking_count)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json(payload))
    return payload


def read_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return status_payload(0, 0)
    return json.loads(path.read_text())
