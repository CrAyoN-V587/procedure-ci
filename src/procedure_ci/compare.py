from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .models import EntityChange
from .oas_index import OasIndex


@dataclass
class CompareResult:
    changes: list[EntityChange] = field(default_factory=list)

    def by_key(self) -> dict[str, EntityChange]:
        return {change.entity.key(): change for change in self.changes}


def compare_oas(base: OasIndex, head: OasIndex) -> CompareResult:
    changes: list[EntityChange] = []
    all_keys = sorted(set(base.entities) | set(head.entities))
    for key in all_keys:
        before = base.entity(key)
        after = head.entity(key)
        if before is None and after is not None:
            changes.append(
                EntityChange(
                    entity=after.ref,
                    status="added",
                    changed_paths=("/",),
                    change_class="behavior",
                    after=after.value,
                )
            )
            continue
        if after is None and before is not None:
            changes.append(
                EntityChange(
                    entity=before.ref,
                    status="removed",
                    changed_paths=("/",),
                    change_class="behavior",
                    before=before.value,
                )
            )
            continue
        if before is None or after is None:
            continue
        compare_field = "security" if before.ref.kind == "security" else None
        before_value = _normalize_for_compare(before.value, field=compare_field)
        after_value = _normalize_for_compare(after.value, field=compare_field)
        paths = tuple(_diff_paths(before_value, after_value))
        if not paths:
            continue
        change_class = _classify_change(paths)
        changes.append(
            EntityChange(
                entity=after.ref,
                status="modified",
                changed_paths=paths,
                change_class=change_class,
                before=before_value,
                after=after_value,
            )
        )
    return CompareResult(changes=changes)


def _diff_paths(before: Any, after: Any, pointer: str = "") -> list[str]:
    if type(before) is not type(after):
        return [pointer or "/"]
    if isinstance(before, dict):
        paths: list[str] = []
        for key in sorted(set(before) | set(after), key=str):
            child = f"{pointer}/{_escape(str(key))}"
            if key not in before or key not in after:
                paths.append(child)
            else:
                paths.extend(_diff_paths(before[key], after[key], child))
        return paths
    if isinstance(before, list):
        if before == after:
            return []
        # Arrays are semantic in OpenAPI (required, enum, security alternatives,
        # examples), so preserve their order and identify the containing field.
        return [pointer or "/"]
    if before != after:
        return [pointer or "/"]
    return []


def _classify_change(paths: tuple[str, ...]) -> str:
    leaves = {path.rsplit("/", 1)[-1].replace("~1", "/").replace("~0", "~") for path in paths}
    if leaves and leaves <= {"description", "summary", "externalDocs", "title"}:
        return "documentation"
    if leaves and leaves <= {"example", "examples"}:
        return "example"
    return "behavior"


_SET_LIST_KEYS = {"required", "enum", "allof", "anyof", "oneof", "security", "type"}


def _normalize_for_compare(
    value: Any,
    field: str | None = None,
    security_context: bool = False,
) -> Any:
    """Normalize fields whose OpenAPI/JSON Schema semantics are set-like.

    This is intentionally limited to unambiguous collection semantics. Arrays
    such as examples and parameters retain their order unless the index has
    already merged them according to their identity rules.
    """

    if isinstance(value, dict):
        result: dict[Any, Any] = {}
        header_map = field == "headers"
        for key, item in value.items():
            normalized_key = key.lower() if header_map and isinstance(key, str) else key
            child_security = security_context or (
                isinstance(key, str) and key.lower() == "security"
            )
            result[normalized_key] = _normalize_for_compare(
                item,
                field=str(key),
                security_context=child_security,
            )
        if str(result.get("in", "")).lower() == "header" and isinstance(result.get("name"), str):
            result["in"] = "header"
            result["name"] = result["name"].lower()
        return result
    if isinstance(value, list):
        normalized = [
            _normalize_for_compare(item, security_context=security_context) for item in value
        ]
        if security_context or (field is not None and field.lower() in _SET_LIST_KEYS):
            return sorted(normalized, key=_canonical_json)
        return normalized
    if field == "in" and isinstance(value, str):
        return value.lower()
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")
