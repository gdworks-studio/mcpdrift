from __future__ import annotations

from pathlib import Path
from typing import Any
import json

SNAPSHOT_SCHEMA_VERSION = 1


def stable_json(data: Any) -> str:
    return json.dumps(sort_json(data), indent=2, sort_keys=True) + "\n"


def sort_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sort_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [sort_json(item) for item in value]
    return value


def write_snapshot(path: Path, contract: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json(contract))


def read_snapshot(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())
