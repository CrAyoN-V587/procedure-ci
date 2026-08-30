from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from .errors import InputError
from .loader import (
    MAX_REF_DEPTH,
    LoadedDocument,
    escape_pointer,
    iter_refs,
    pointer_get,
    validate_ref_depth,
)
from .models import Diagnostic, EntityRef


@dataclass(frozen=True)
class EntityRecord:
    ref: EntityRef
    value: Any


@dataclass(frozen=True)
class OperationRecord:
    operation_id: str
    method: str
    path: str
    pointer: str
    value: dict[str, Any]
    ref: EntityRef
    dependency_keys: tuple[str, ...]
    response_dependency_keys: tuple[str, ...]


@dataclass
class OasIndex:
    document: LoadedDocument
    operations: dict[str, OperationRecord] = field(default_factory=dict)
    duplicate_operation_ids: dict[str, list[str]] = field(default_factory=dict)
    entities: dict[str, EntityRecord] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    operation_locations: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    @property
    def source_file(self) -> str:
        return self.document.path

    def entity(self, key: str) -> EntityRecord | None:
        return self.entities.get(key)

    def operation(self, operation_id: str) -> OperationRecord | None:
        return self.operations.get(operation_id)


def build_oas_index(document: LoadedDocument) -> OasIndex:
    root = document.data
    version = root.get("openapi")
    if not isinstance(version, str) or not version.startswith("3.1."):
        raise InputError(
            f"only OpenAPI 3.1 is supported in the MVP ({document.path!s}, found {version!r})"
        )
    index = OasIndex(document=document)
    _index_components(index)
    _index_global_security(index)
    paths = root.get("paths", {})
    if not isinstance(paths, dict):
        raise InputError(f"OpenAPI paths must be an object: {document.path}")
    for path, path_item in paths.items():
        if not isinstance(path, str) or not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in _HTTP_METHODS or not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id:
                continue
            pointer = f"/paths/{escape_pointer(path)}/{escape_pointer(method)}"
            index.operation_locations.setdefault(operation_id, []).append((method.lower(), path))
            ref = EntityRef(
                source_name=document.path,
                kind="operation",
                canonical_id=operation_id,
                source_pointer=pointer,
            )
            path_parameters = path_item.get("parameters", [])
            effective_operation = dict(operation)
            operation_parameters = operation.get("parameters", [])
            if isinstance(path_parameters, list) or isinstance(operation_parameters, list):
                effective_operation["parameters"] = _merge_parameters(
                    document.data,
                    path_parameters if isinstance(path_parameters, list) else [],
                    operation_parameters if isinstance(operation_parameters, list) else [],
                )
            entity = EntityRecord(
                ref=ref,
                value={"method": method.lower(), "path": path, **effective_operation},
            )
            index.entities[ref.key()] = entity
            deps = _operation_dependencies(index, effective_operation, pointer)
            response_deps = _response_dependencies(index, effective_operation, pointer)
            record = OperationRecord(
                operation_id=operation_id,
                method=method.lower(),
                path=path,
                pointer=pointer,
                value=entity.value,
                ref=ref,
                dependency_keys=tuple(sorted({ref.key(), *deps})),
                response_dependency_keys=tuple(sorted({ref.key(), *response_deps})),
            )
            if operation_id in index.operations:
                locations = index.operation_locations[operation_id]
                index.duplicate_operation_ids[operation_id] = [
                    f"{item_method.upper()} {item_path}" for item_method, item_path in locations
                ]
                index.operations.pop(operation_id, None)
            elif operation_id not in index.duplicate_operation_ids:
                index.operations[operation_id] = record
    _validate_unsupported_oas_features(index)
    _validate_refs(index)
    return index


_HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def _index_components(index: OasIndex) -> None:
    root = index.document.data
    components = root.get("components", {})
    if not isinstance(components, dict):
        return
    for component_name, values in components.items():
        if not isinstance(values, dict):
            continue
        kind = _COMPONENT_KINDS.get(component_name)
        if kind is None:
            continue
        for name, value in values.items():
            if not isinstance(name, str):
                continue
            pointer = f"/components/{escape_pointer(component_name)}/{escape_pointer(name)}"
            ref = EntityRef(
                source_name=index.document.path,
                kind=kind,
                canonical_id=name,
                source_pointer=pointer,
            )
            index.entities[ref.key()] = EntityRecord(ref=ref, value=value)


def _index_global_security(index: OasIndex) -> None:
    ref = EntityRef(
        source_name=index.document.path,
        kind="security",
        canonical_id="root",
        source_pointer="/security",
    )
    # Missing and explicit [] both mean that no global security requirement is
    # inherited by operations, so compare their semantic value as the same set.
    index.entities[ref.key()] = EntityRecord(
        ref=ref,
        value=index.document.data.get("security", []),
    )


_COMPONENT_KINDS = {
    "schemas": "schema",
    "securitySchemes": "security_scheme",
    "parameters": "component_parameter",
    "requestBodies": "component_request_body",
    "responses": "component_response",
    "headers": "component_header",
}


def _operation_dependencies(index: OasIndex, operation: dict[str, Any], pointer: str) -> set[str]:
    return _value_dependencies(index, operation, pointer)


def _response_dependencies(index: OasIndex, operation: dict[str, Any], pointer: str) -> set[str]:
    responses = operation.get("responses")
    if not isinstance(responses, dict):
        return set()
    return _value_dependencies(index, responses, f"{pointer}/responses")


def _value_dependencies(index: OasIndex, value: Any, pointer: str) -> set[str]:
    dependencies: set[str] = set()
    for _, ref_value in iter_refs(value, pointer):
        if ref_value.startswith("#/"):
            try:
                target = pointer_get(index.document.data, ref_value[1:])
            except KeyError:
                continue
            target_ref = _entity_for_pointer(index, ref_value[1:])
            if target_ref is not None:
                dependencies.add(target_ref.key())
            _collect_nested_refs(index, target, ref_value, dependencies, seen=set(), depth=1)
        elif ref_value:
            # The dedicated validation pass turns this into an unknown diagnostic.
            continue
    if isinstance(value, dict) and "responses" in value:
        _collect_security_dependencies(index, value, dependencies)
    return dependencies


def _collect_nested_refs(
    index: OasIndex,
    value: Any,
    pointer: str,
    dependencies: set[str],
    seen: set[str],
    depth: int,
) -> None:
    if depth > MAX_REF_DEPTH:
        raise InputError(
            f"internal reference depth exceeds {MAX_REF_DEPTH}: {index.document.path} ({pointer})"
        )
    if pointer in seen:
        return
    seen.add(pointer)
    for _, ref_value in iter_refs(value, pointer):
        if not ref_value.startswith("#/"):
            continue
        try:
            target = pointer_get(index.document.data, ref_value[1:])
        except KeyError:
            continue
        target_ref = _entity_for_pointer(index, ref_value[1:])
        if target_ref is not None:
            dependencies.add(target_ref.key())
        _collect_nested_refs(index, target, ref_value, dependencies, seen, depth + 1)


def _entity_for_pointer(index: OasIndex, pointer: str) -> EntityRef | None:
    parts = pointer.lstrip("/").split("/")
    if len(parts) == 3 and parts[0] == "components":
        component = parts[1].replace("~1", "/").replace("~0", "~")
        name = parts[2].replace("~1", "/").replace("~0", "~")
        kind = _COMPONENT_KINDS.get(component)
        if kind is not None:
            return EntityRef(
                source_name=index.document.path,
                kind=kind,
                canonical_id=name,
                source_pointer=pointer,
            )
    return None


def _collect_security_dependencies(
    index: OasIndex, operation: dict[str, Any], dependencies: set[str]
) -> None:
    inherits_global = "security" not in operation
    security = (
        operation.get("security") if not inherits_global else index.document.data.get("security")
    )
    if inherits_global and "security" in index.document.data:
        dependencies.add("security:root")
    if not isinstance(security, list):
        return
    components = index.document.data.get("components", {})
    schemes = components.get("securitySchemes", {}) if isinstance(components, dict) else {}
    if not isinstance(schemes, dict):
        return
    for requirement in security:
        if not isinstance(requirement, dict):
            continue
        for scheme_name in requirement:
            if scheme_name in schemes:
                ref = EntityRef(
                    source_name=index.document.path,
                    kind="security_scheme",
                    canonical_id=scheme_name,
                    source_pointer=f"/components/securitySchemes/{escape_pointer(scheme_name)}",
                )
                dependencies.add(ref.key())


def _merge_parameters(
    document: dict[str, Any], path_parameters: list[Any], operation_parameters: list[Any]
) -> list[Any]:
    """Merge path and operation parameters by the OpenAPI identity tuple.

    Operation-level parameters override path-level parameters with the same
    ``(in, name)`` identity. Header names are wire identifiers and therefore
    compare case-insensitively.
    """

    merged: dict[tuple[str, str], Any] = {}
    order: list[tuple[str, str]] = []
    for parameter in [*path_parameters, *operation_parameters]:
        key = _parameter_identity(document, parameter)
        if key is None:
            key = ("$ref", str(parameter))
        if key not in merged:
            order.append(key)
        merged[key] = _normalise_parameter(parameter, document)
    return [merged[key] for key in order]


def _parameter_identity(document: dict[str, Any], parameter: Any) -> tuple[str, str] | None:
    resolved = parameter
    if isinstance(parameter, dict) and isinstance(parameter.get("$ref"), str):
        ref = parameter["$ref"]
        if ref.startswith("#/"):
            try:
                resolved = pointer_get(document, ref[1:])
            except KeyError:
                return None
    if not isinstance(resolved, dict):
        return None
    location = resolved.get("in")
    name = resolved.get("name")
    if not isinstance(location, str) or not isinstance(name, str):
        return None
    location = location.lower()
    return location, name.lower() if location == "header" else name


def _normalise_parameter(parameter: Any, document: dict[str, Any]) -> Any:
    result = deepcopy(parameter)
    resolved = parameter
    if isinstance(parameter, dict) and isinstance(parameter.get("$ref"), str):
        ref = parameter["$ref"]
        if ref.startswith("#/"):
            try:
                resolved = pointer_get(document, ref[1:])
            except KeyError:
                return result
    if not isinstance(resolved, dict):
        return result
    location = resolved.get("in")
    name = resolved.get("name")
    if isinstance(location, str) and isinstance(name, str) and location.lower() == "header":
        if isinstance(result, dict) and "$ref" not in result:
            result["in"] = "header"
            result["name"] = name.lower()
    return result


def _validate_refs(index: OasIndex) -> None:
    for pointer, value in iter_refs(index.document.data):
        if not value.startswith("#/"):
            index.diagnostics.append(
                Diagnostic(
                    schema_version="0.1",
                    code="UNSUPPORTED_EXTERNAL_REF",
                    severity="unknown",
                    source_file=index.document.path,
                    source_pointer=pointer,
                    message=f"external reference is outside the MVP and was not fetched: {value}",
                    details={"ref": value},
                )
            )
            continue
        try:
            pointer_get(index.document.data, value[1:])
        except KeyError:
            index.diagnostics.append(
                Diagnostic(
                    schema_version="0.1",
                    code="OAS_REF_UNRESOLVED",
                    severity="error",
                    source_file=index.document.path,
                    source_pointer=pointer,
                    message=f"internal reference cannot be resolved: {value}",
                    details={"ref": value},
                )
            )
    validate_ref_depth(index.document.data, index.document.path)


def _validate_unsupported_oas_features(index: OasIndex) -> None:
    unsupported = {"$dynamicRef", "$anchor", "$id"}
    for pointer, key in _mapping_keys(index.document.data):
        if key not in unsupported:
            continue
        index.diagnostics.append(
            Diagnostic(
                schema_version="0.1",
                code="UNSUPPORTED_OAS_FEATURE",
                severity="unknown",
                source_file=index.document.path,
                source_pointer=pointer,
                message=f"OpenAPI feature is outside the MVP and was not evaluated: {key}",
                details={"key": key},
            )
        )


def _mapping_keys(value: Any, pointer: str = "", seen: set[int] | None = None):
    if seen is None:
        seen = set()
    if isinstance(value, (dict, list)):
        value_id = id(value)
        if value_id in seen:
            return
        seen.add(value_id)
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{pointer}/{escape_pointer(str(key))}"
            yield child, str(key)
            yield from _mapping_keys(item, child, seen)
    elif isinstance(value, list):
        for number, item in enumerate(value):
            yield from _mapping_keys(item, f"{pointer}/{number}", seen)
