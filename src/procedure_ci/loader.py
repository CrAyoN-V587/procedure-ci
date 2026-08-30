from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from ruamel.yaml import YAML
from ruamel.yaml.constructor import DuplicateKeyError
from ruamel.yaml.error import YAMLError
from ruamel.yaml.parser import ParserError
from ruamel.yaml.scanner import ScannerError

from .errors import InputError

MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
MAX_NODES = 100_000
MAX_REF_DEPTH = 100


@dataclass(frozen=True)
class LoadedDocument:
    path: str
    data: dict[str, Any]


def _display_path(path: Path | str) -> str:
    return str(path).replace("\\", "/")


def load_document(path: Path | str) -> LoadedDocument:
    """Safely load a local JSON or YAML document.

    The loader deliberately never resolves URLs, expands tags, evaluates templates,
    or reads anything except the explicitly supplied file.
    """

    source = Path(path)
    if not source.exists() or not source.is_file():
        raise InputError(f"input file does not exist: {path}")
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise InputError(f"cannot stat input file {path}: {exc}") from exc
    if size > MAX_DOCUMENT_BYTES:
        raise InputError(f"input file exceeds {MAX_DOCUMENT_BYTES} bytes: {path}")
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise InputError(f"cannot read input file {path}: {exc}") from exc

    suffix = source.suffix.lower()
    try:
        if suffix == ".json":
            data = json.loads(text)
        else:
            yaml = YAML(typ="safe")
            yaml.version = (1, 2)
            yaml.allow_duplicate_keys = False
            data = yaml.load(text)
    except (ValueError, YAMLError, DuplicateKeyError, ParserError, ScannerError) as exc:
        raise InputError(f"cannot parse input file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError(f"input document must have an object root: {path}")
    node_count = count_nodes(data)
    if node_count > MAX_NODES:
        raise InputError(f"input document exceeds {MAX_NODES} nodes: {path}")
    return LoadedDocument(path=_display_path(path), data=data)


def count_nodes(value: Any, _seen: set[int] | None = None) -> int:
    if _seen is None:
        _seen = set()
    if isinstance(value, (dict, list)):
        value_id = id(value)
        if value_id in _seen:
            return 0
        _seen.add(value_id)
    if isinstance(value, dict):
        return 1 + sum(
            count_nodes(key, _seen) + count_nodes(item, _seen) for key, item in value.items()
        )
    if isinstance(value, list):
        return 1 + sum(count_nodes(item, _seen) for item in value)
    return 1


def iter_refs(
    value: Any, pointer: str = "", _seen: set[int] | None = None
) -> Iterator[tuple[str, str]]:
    """Yield ``(json_pointer, ref_value)`` pairs in stable document order."""

    if _seen is None:
        _seen = set()
    if isinstance(value, (dict, list)):
        value_id = id(value)
        if value_id in _seen:
            return
        _seen.add(value_id)
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{pointer}/{escape_pointer(str(key))}"
            if key == "$ref" and isinstance(item, str):
                yield child, item
            yield from iter_refs(item, child, _seen)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_refs(item, f"{pointer}/{index}", _seen)


def escape_pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def unescape_pointer(value: str) -> str:
    return value.replace("~1", "/").replace("~0", "~")


def pointer_get(document: Any, pointer: str) -> Any:
    if pointer in ("", "/"):
        return document
    current = document
    for token in pointer.lstrip("/").split("/"):
        token = unescape_pointer(token)
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            raise KeyError(pointer)
    return current


def validate_ref_depth(document: Any, source: str) -> None:
    """Reject internal reference chains deeper than the shared safety limit.

    This walks all reachable internal references in the supplied document, not
    just references used by a particular operation. Cycles are allowed and are
    stopped by the active pointer set; a longer acyclic path still consumes the
    limit even when it leads through an otherwise unused component.
    """

    deepest: dict[str, int] = {}

    def visit(value: Any, pointer: str, depth: int, active: set[str]) -> None:
        if depth > MAX_REF_DEPTH:
            raise InputError(
                f"internal reference depth exceeds {MAX_REF_DEPTH}: {source} ({pointer})"
            )
        if pointer in active:
            return
        if depth <= deepest.get(pointer, -1):
            return
        deepest[pointer] = depth
        next_active = active | {pointer}
        for _, reference in iter_refs(value, pointer):
            if not reference.startswith("#/"):
                continue
            try:
                target = pointer_get(document, reference[1:])
            except KeyError:
                continue
            visit(target, reference, depth + 1, next_active)

    visit(document, "", 0, set())


def canonical_pointer(pointer: str) -> str:
    return pointer or "/"
