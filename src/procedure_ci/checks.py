from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from .arazzo_index import ArazzoIndex, ArazzoStep
from .compare import CompareResult
from .graph import DependencyGraph
from .loader import pointer_get
from .models import Diagnostic, EntityChange, EntityRef, Impact, Report, StepRef
from .oas_index import OasIndex, OperationRecord


@dataclass(frozen=True)
class CheckContext:
    base: OasIndex
    head: OasIndex
    arazzo: ArazzoIndex
    graph: DependencyGraph
    comparison: CompareResult


def run_checks(
    base: OasIndex,
    head: OasIndex,
    arazzo: ArazzoIndex,
    graph: DependencyGraph,
    comparison: CompareResult,
) -> Report:
    context = CheckContext(base, head, arazzo, graph, comparison)
    report = Report()
    report.diagnostics.extend(base.diagnostics)
    report.diagnostics.extend(head.diagnostics)
    report.diagnostics.extend(arazzo.diagnostics)
    report.diagnostics.extend(_duplicate_operation_diagnostics(context))
    report.diagnostics.extend(_missing_security_diagnostics(context))
    changes = comparison.by_key()

    for step in arazzo.steps:
        operation = head.operation(step.operation_id) if step.operation_id else None
        step_changes = _step_changes(step, graph, changes)
        if step.operation_id:
            if step.operation_id in head.duplicate_operation_ids:
                report.impacts.append(
                    Impact(step=step.ref, severity="error", deterministic_error=True)
                )
                continue
            if operation is None:
                report.diagnostics.append(
                    _diag(
                        head,
                        "OAS_OPERATION_MISSING",
                        "error",
                        "/paths",
                        f"Arazzo step {step.ref.step_id} references missing operationId "
                        f"{step.operation_id}",
                        step.ref,
                        details={"operationId": step.operation_id},
                    )
                )
                report.impacts.append(
                    Impact(step=step.ref, severity="error", deterministic_error=True)
                )
                continue

        if not step.operation_id:
            continue

        impact = _make_impact(step, step_changes, graph)
        if impact is not None:
            report.impacts.append(impact)
            for change in step_changes:
                if change.change_class == "documentation":
                    code, severity, message = (
                        "DEPENDENCY_DOC_ONLY",
                        "info",
                        "referenced API documentation changed; no behavior change was detected",
                    )
                else:
                    code, severity, message = (
                        "DEPENDENCY_CHANGED",
                        "review",
                        "referenced API behavior or example changed; review this workflow step",
                    )
                report.diagnostics.append(
                    _diag(
                        head,
                        code,
                        severity,
                        change.entity.source_pointer,
                        f"{message}: {change.entity.kind} {change.entity.canonical_id}",
                        step.ref,
                        details={"change": change.to_dict()},
                    )
                )

        report.diagnostics.extend(_unsupported_request_body_diagnostics(step, operation, head))
        example_diagnostics = _validate_step_payload(step, operation, head)
        report.diagnostics.extend(example_diagnostics)
        if step.has_dynamic_payload and _has_request_payload(step):
            report.diagnostics.append(
                _diag(
                    head,
                    "DYNAMIC_PAYLOAD_UNCHECKED",
                    "unknown",
                    f"{step.ref.source_pointer}/requestBody",
                    "request payload contains runtime expressions and was not schema-validated",
                    step.ref,
                )
            )
    _propagate_missing_producer_impacts(report, arazzo, graph, head)
    _deduplicate(report)
    return report


def _step_changes(
    step: ArazzoStep,
    graph: DependencyGraph,
    changes: dict[str, EntityChange],
) -> list[EntityChange]:
    result: list[EntityChange] = []
    seen: set[str] = set()
    for edge in graph.edges_for(step.ref):
        key = edge.entity.key()
        if key in changes and key not in seen:
            result.append(changes[key])
            seen.add(key)
    return result


def _make_impact(
    step: ArazzoStep, changes: list[EntityChange], graph: DependencyGraph
) -> Impact | None:
    if not changes:
        return None
    severity = (
        "info" if all(change.change_class == "documentation" for change in changes) else "review"
    )
    paths: list[list[Any]] = []
    for change in changes:
        for edge in graph.edges_for(step.ref):
            if edge.entity.key() == change.entity.key():
                paths.append([*edge.via, edge.entity])
    return Impact(
        step=step.ref,
        changes=changes,
        dependency_paths=paths,
        severity=severity,  # type: ignore[arg-type]
        deterministic_error=False,
    )


def _propagate_missing_producer_impacts(
    report: Report, arazzo: ArazzoIndex, graph: DependencyGraph, head: OasIndex
) -> None:
    """Mark downstream consumers when a producer has no usable head operation.

    A missing producer may have no entity edge in either OpenAPI version (for
    example, a workflow step was added before its operation existed). The
    workflow graph still makes that uncertainty observable to every consumer,
    including consumers several steps away.
    """

    missing = {
        step.ref.key()
        for step in arazzo.steps
        if step.operation_id and head.operation(step.operation_id) is None
    }
    if not missing:
        return
    impacts = {impact.step.key(): impact for impact in report.impacts}
    for consumer in arazzo.steps:
        if not consumer.operation_id:
            continue
        paths: list[list[EntityRef]] = []
        for chain in graph.dependency_chains_for(consumer.ref):
            for number, producer in enumerate(chain):
                if producer.key() in missing:
                    path = [_step_marker(item) for item in chain[: number + 1]]
                    existing = {_path_key(item) for item in paths}
                    if path and _path_key(path) not in existing:
                        paths.append(path)
                    break
        if not paths:
            continue
        impact = impacts.get(consumer.ref.key())
        if impact is None:
            impact = Impact(
                step=consumer.ref,
                dependency_paths=sorted(paths, key=_path_key),
                severity="review",
                deterministic_error=False,
            )
            report.impacts.append(impact)
            impacts[consumer.ref.key()] = impact
            continue
        if impact.severity == "info":
            impact.severity = "review"
        existing = {_path_key(path) for path in impact.dependency_paths}
        impact.dependency_paths.extend(path for path in paths if _path_key(path) not in existing)
        impact.dependency_paths.sort(key=_path_key)


def _step_marker(step: StepRef) -> EntityRef:
    return EntityRef(
        source_name=step.document,
        kind="workflow_step",
        canonical_id=step.key(),
        source_pointer=step.source_pointer,
    )


def _path_key(path: list[EntityRef]) -> tuple[str, ...]:
    return tuple(
        f"{item.kind}:{item.canonical_id}:{item.source_name}:{item.source_pointer}" for item in path
    )


def _duplicate_operation_diagnostics(context: CheckContext) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for index in (context.base, context.head):
        for operation_id, locations in sorted(index.duplicate_operation_ids.items()):
            steps = tuple(
                step.ref for step in context.arazzo.steps if step.operation_id == operation_id
            )
            diagnostics.append(
                Diagnostic(
                    schema_version="0.1",
                    code="OAS_OPERATION_AMBIGUOUS",
                    severity="error",
                    source_file=index.source_file,
                    source_pointer="/paths",
                    message=f"operationId is not unique: {operation_id}",
                    affected_steps=steps,
                    details={"operationId": operation_id, "locations": locations},
                )
            )
    return diagnostics


def _missing_security_diagnostics(context: CheckContext) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    components = context.head.document.data.get("components", {})
    schemes = components.get("securitySchemes", {}) if isinstance(components, dict) else {}
    if not isinstance(schemes, dict):
        schemes = {}
    for step in context.arazzo.steps:
        if not step.operation_id:
            continue
        operation = context.head.operation(step.operation_id)
        if operation is None:
            continue
        security = operation.value.get("security")
        if security is None:
            security = context.head.document.data.get("security")
        if not isinstance(security, list):
            continue
        missing: list[str] = []
        for requirement in security:
            if isinstance(requirement, dict):
                missing.extend(name for name in requirement if name not in schemes)
        for name in sorted(set(missing)):
            diagnostics.append(
                _diag(
                    context.head,
                    "SECURITY_SCHEME_MISSING",
                    "error",
                    f"{operation.pointer}/security",
                    f"security scheme is not defined: {name}",
                    step.ref,
                    details={"scheme": name},
                )
            )
    return diagnostics


def _validate_step_payload(
    step: ArazzoStep, operation: OperationRecord | None, head: OasIndex
) -> list[Diagnostic]:
    if operation is None or step.has_dynamic_payload:
        return []
    request_body = step.value.get("requestBody")
    if not isinstance(request_body, dict) or "payload" not in request_body:
        return []
    payload = request_body.get("payload")
    request_definition = operation.value.get("requestBody")
    if isinstance(request_definition, dict) and "$ref" in request_definition:
        request_definition = _resolve_ref(head.document.data, request_definition)
    if not isinstance(request_definition, dict):
        return []
    content = request_definition.get("content")
    if not isinstance(content, dict) or not content:
        return []
    content_type = request_body.get("contentType")
    media = content.get(content_type) if isinstance(content_type, str) else None
    if media is None:
        media = next(iter(content.values()))
    if not isinstance(media, dict):
        return []
    schema = media.get("schema")
    if not isinstance(schema, dict):
        return []
    try:
        root_uri = "urn:procedure-ci:openapi"
        registry = Registry().with_resource(
            root_uri,
            Resource.from_contents(
                head.document.data,
                default_specification=DRAFT202012,
            ),
        )
        schema_for_validation = deepcopy(schema)
        _make_refs_absolute(schema_for_validation, root_uri)
        validator = Draft202012Validator(schema_for_validation, registry=registry)
        error = next(iter(validator.iter_errors(payload)), None)
    except Exception as exc:  # validator errors are tool/input failures, but keep CI deterministic
        return [
            _diag(
                head,
                "EXAMPLE_SCHEMA_INVALID",
                "unknown",
                f"{step.ref.source_pointer}/requestBody/payload",
                f"could not validate literal payload against schema: {exc}",
                step.ref,
            )
        ]
    if error is None:
        return []
    location = "/".join(str(item) for item in error.absolute_path)
    pointer = f"{step.ref.source_pointer}/requestBody/payload"
    if location:
        pointer += "/" + location
    return [
        _diag(
            head,
            "EXAMPLE_SCHEMA_INVALID",
            "error",
            pointer,
            f"literal request payload does not satisfy the OpenAPI schema: {error.message}",
            step.ref,
            details={"validator": error.validator, "path": list(error.absolute_path)},
        )
    ]


def _unsupported_request_body_diagnostics(
    step: ArazzoStep, operation: OperationRecord | None, head: OasIndex
) -> list[Diagnostic]:
    """Report non-JSON request bodies when Arazzo omitted contentType."""

    if operation is None:
        return []
    request_body = step.value.get("requestBody")
    if not isinstance(request_body, dict):
        return []
    requested_content_type = request_body.get("contentType")
    if isinstance(requested_content_type, str):
        requested_media_type = requested_content_type.split(";", 1)[0].strip().lower()
        if requested_media_type != "application/json":
            return []
    elif "contentType" in request_body:
        return []
    definition = operation.value.get("requestBody")
    if isinstance(definition, dict) and "$ref" in definition:
        definition = _resolve_ref(head.document.data, definition)
    if not isinstance(definition, dict):
        return []
    content = definition.get("content")
    if not isinstance(content, dict) or not content:
        return []
    has_json = any(
        isinstance(content_type, str)
        and content_type.split(";", 1)[0].strip().lower() == "application/json"
        for content_type in content
    )
    if has_json:
        return []
    content_type = next(iter(content), "unknown")
    return [
        _diag(
            head,
            "UNSUPPORTED_ARAZZO_FEATURE",
            "unknown",
            f"{step.ref.source_pointer}/requestBody",
            "only application/json request bodies are evaluated by the MVP",
            step.ref,
            details={"contentType": str(content_type)},
        )
    ]


def _resolve_ref(document: Any, value: Any) -> Any:
    if not isinstance(value, dict) or not isinstance(value.get("$ref"), str):
        return value
    ref = value["$ref"]
    if not ref.startswith("#/"):
        return value
    try:
        return pointer_get(document, ref[1:])
    except KeyError:
        return value


def _make_refs_absolute(value: Any, root_uri: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "$ref" and isinstance(item, str) and item.startswith("#/"):
                value[key] = root_uri + item
            else:
                _make_refs_absolute(item, root_uri)
    elif isinstance(value, list):
        for item in value:
            _make_refs_absolute(item, root_uri)


def _has_request_payload(step: ArazzoStep) -> bool:
    value = step.value.get("requestBody")
    return isinstance(value, dict) and "payload" in value


def _diag(
    index: OasIndex,
    code: str,
    severity: str,
    pointer: str,
    message: str,
    step: StepRef,
    details: dict[str, Any] | None = None,
) -> Diagnostic:
    return Diagnostic(
        schema_version="0.1",
        code=code,
        severity=severity,  # type: ignore[arg-type]
        source_file=index.source_file,
        source_pointer=pointer,
        message=message,
        affected_steps=(step,),
        details=details or {},
    )


def _deduplicate(report: Report) -> None:
    seen: set[tuple[Any, ...]] = set()
    unique: list[Diagnostic] = []
    for diagnostic in report.diagnostics:
        key = (
            diagnostic.code,
            diagnostic.severity,
            diagnostic.source_file,
            diagnostic.source_pointer,
            diagnostic.message,
            tuple(step.key() for step in diagnostic.affected_steps),
        )
        if key not in seen:
            seen.add(key)
            unique.append(diagnostic)
    report.diagnostics = unique
