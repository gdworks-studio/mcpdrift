from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Severity = Literal["BREAKING", "NON-BREAKING"]

DOC_KEYS = {"description", "title", "examples", "default"}
STRICTNESS_KEYS = {
    "const",
    "enum",
    "exclusiveMaximum",
    "exclusiveMinimum",
    "format",
    "maxItems",
    "maxLength",
    "maxProperties",
    "maximum",
    "minItems",
    "minLength",
    "minProperties",
    "minimum",
    "pattern",
    "uniqueItems",
}


@dataclass(frozen=True)
class Change:
    severity: Severity
    message: str


@dataclass(frozen=True)
class DiffResult:
    changes: list[Change]

    @property
    def has_breaking(self) -> bool:
        return any(change.severity == "BREAKING" for change in self.changes)

    @property
    def breaking_count(self) -> int:
        return sum(1 for change in self.changes if change.severity == "BREAKING")

    @property
    def non_breaking_count(self) -> int:
        return sum(1 for change in self.changes if change.severity == "NON-BREAKING")


def compare_contracts(before: dict[str, Any], after: dict[str, Any]) -> DiffResult:
    changes: list[Change] = []
    changes.extend(_compare_tools(_by_name(before.get("tools", [])), _by_name(after.get("tools", []))))
    changes.extend(
        _compare_named_contracts(
            "resource",
            _by_key(before.get("resources", []), "uri"),
            _by_key(after.get("resources", []), "uri"),
            breaking_fields=("name",),
        )
    )
    changes.extend(
        _compare_named_contracts(
            "prompt",
            _by_name(before.get("prompts", [])),
            _by_name(after.get("prompts", [])),
            breaking_fields=("arguments",),
        )
    )
    return DiffResult(changes)


def format_diff(result: DiffResult) -> str:
    if not result.changes:
        return "MCP contract verified: no drift detected.\nSummary: 0 breaking, 0 non-breaking changes."

    lines: list[str] = []
    breaking = [change for change in result.changes if change.severity == "BREAKING"]
    non_breaking = [change for change in result.changes if change.severity == "NON-BREAKING"]
    lines.append("BREAKING")
    if breaking:
        lines.extend(f"- {change.message}" for change in breaking)
    else:
        lines.append("- none")

    lines.append("")
    lines.append("NON-BREAKING")
    if non_breaking:
        lines.extend(f"- {change.message}" for change in non_breaking)
    else:
        lines.append("- none")

    lines.append("")
    lines.append(f"Summary: {len(breaking)} breaking, {len(non_breaking)} non-breaking changes.")
    return "\n".join(lines)


def _compare_tools(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> list[Change]:
    changes: list[Change] = []
    removed = set(before) - set(after)
    added = set(after) - set(before)

    renamed = _detect_tool_renames(before, after, removed, added)
    for old_name, new_name in renamed:
        changes.append(Change("BREAKING", f"tool renamed: {old_name} -> {new_name}"))
        removed.remove(old_name)
        added.remove(new_name)

    changes.extend(Change("BREAKING", f"tool removed: {name}") for name in sorted(removed))
    changes.extend(Change("NON-BREAKING", f"tool added: {name}") for name in sorted(added))

    for name in sorted(set(before) & set(after)):
        previous = before[name]
        current = after[name]
        if previous.get("description") != current.get("description"):
            changes.append(Change("NON-BREAKING", f"description changed on {name}"))
        changes.extend(_compare_input_schema(name, previous.get("inputSchema", {}), current.get("inputSchema", {})))
        if _schema_shape(previous.get("outputSchema")) != _schema_shape(current.get("outputSchema")):
            changes.append(Change("BREAKING", f"output schema changed on {name}"))

    return changes


def _compare_input_schema(tool_name: str, before: dict[str, Any], after: dict[str, Any]) -> list[Change]:
    changes: list[Change] = []
    before_required = set(before.get("required", []))
    after_required = set(after.get("required", []))
    before_props = before.get("properties", {}) or {}
    after_props = after.get("properties", {}) or {}

    for name in sorted(after_required - before_required):
        changes.append(Change("BREAKING", f"required input added on {tool_name}: {name}"))
    for name in sorted(before_required - after_required):
        changes.append(Change("BREAKING", f"required input removed on {tool_name}: {name}"))

    for name in sorted(set(after_props) - set(before_props)):
        if name not in after_required:
            changes.append(Change("NON-BREAKING", f"optional input added on {tool_name}: {name}"))

    for name in sorted(set(before_props) - set(after_props)):
        if name in before_required:
            continue
        changes.append(Change("BREAKING", f"input removed on {tool_name}: {name}"))

    for name in sorted(set(before_props) & set(after_props)):
        old_schema = before_props[name]
        new_schema = after_props[name]
        old_type = old_schema.get("type")
        new_type = new_schema.get("type")
        if old_type != new_type:
            prefix = "required" if name in before_required or name in after_required else "optional"
            changes.append(Change("BREAKING", f"{prefix} input retyped on {tool_name}.{name}: {old_type} -> {new_type}"))
            continue
        changes.extend(_strictness_changes(tool_name, name, old_schema, new_schema))

    if _became_closed_object(before, after):
        changes.append(Change("BREAKING", f"input schema stricter on {tool_name}: additionalProperties set to false"))

    return changes


def _strictness_changes(tool_name: str, prop_name: str, before: dict[str, Any], after: dict[str, Any]) -> list[Change]:
    changes: list[Change] = []
    for key in sorted(STRICTNESS_KEYS):
        if key not in before and key in after:
            changes.append(Change("BREAKING", f"input schema stricter on {tool_name}.{prop_name}: {key} added as {after[key]}"))
        elif key in before and key in after and _is_stricter(key, before[key], after[key]):
            changes.append(Change("BREAKING", f"input schema stricter on {tool_name}.{prop_name}: {key} {before[key]} -> {after[key]}"))
    return changes


def _is_stricter(key: str, before: Any, after: Any) -> bool:
    if key in {"minimum", "exclusiveMinimum", "minItems", "minLength", "minProperties"}:
        return _numeric(after) is not None and _numeric(before) is not None and after > before
    if key in {"maximum", "exclusiveMaximum", "maxItems", "maxLength", "maxProperties"}:
        return _numeric(after) is not None and _numeric(before) is not None and after < before
    if key == "enum" and isinstance(before, list) and isinstance(after, list):
        before_set = set(map(str, before))
        after_set = set(map(str, after))
        return after_set < before_set
    return before != after


def _numeric(value: Any) -> float | None:
    return value if isinstance(value, int | float) else None


def _became_closed_object(before: dict[str, Any], after: dict[str, Any]) -> bool:
    return before.get("additionalProperties", True) is not False and after.get("additionalProperties") is False


def _detect_tool_renames(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    removed: set[str],
    added: set[str],
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    available_added = set(added)
    for old_name in sorted(removed):
        old_signature = _tool_signature(before[old_name])
        for new_name in sorted(available_added):
            if old_signature == _tool_signature(after[new_name]):
                pairs.append((old_name, new_name))
                available_added.remove(new_name)
                break
    return pairs


def _tool_signature(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "description": tool.get("description"),
        "inputSchema": _schema_shape(tool.get("inputSchema")),
        "outputSchema": _schema_shape(tool.get("outputSchema")),
    }


def _compare_named_contracts(
    label: str,
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    breaking_fields: tuple[str, ...],
) -> list[Change]:
    changes: list[Change] = []
    for name in sorted(set(before) - set(after)):
        changes.append(Change("BREAKING", f"{label} removed: {name}"))
    for name in sorted(set(after) - set(before)):
        changes.append(Change("NON-BREAKING", f"{label} added: {name}"))
    for name in sorted(set(before) & set(after)):
        if before[name].get("description") != after[name].get("description"):
            changes.append(Change("NON-BREAKING", f"{label} description changed on {name}"))
        for field in breaking_fields:
            if before[name].get(field) != after[name].get(field):
                changes.append(Change("BREAKING", f"{label} {field} changed on {name}"))
    return changes


def _schema_shape(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _schema_shape(val) for key, val in sorted(value.items()) if key not in DOC_KEYS}
    if isinstance(value, list):
        return [_schema_shape(item) for item in value]
    return value


def _by_name(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return _by_key(items, "name")


def _by_key(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(item[key]): item for item in items}
