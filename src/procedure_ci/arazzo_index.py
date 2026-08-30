from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from .errors import InputError
from .loader import LoadedDocument, escape_pointer, iter_refs, pointer_get, validate_ref_depth
from .models import Diagnostic, StepRef


@dataclass(frozen=True)
class ArazzoStep:
    ref: StepRef
    operation_id: str | None
    operation_path: str | None
    value: dict[str, Any]
    output_names: tuple[str, ...]
    output_expressions: tuple[tuple[str, str], ...]
    step_output_refs: tuple[tuple[str, str], ...]
    has_dynamic_payload: bool = False


@dataclass(frozen=True)
class ArazzoWorkflow:
    workflow_id: str
    pointer: str
    steps: tuple[ArazzoStep, ...]


@dataclass
class ArazzoIndex:
    document: LoadedDocument
    workflows: list[ArazzoWorkflow] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def source_file(self) -> str:
        return self.document.path

    @property
    def steps(self) -> list[ArazzoStep]:
        return [step for workflow in self.workflows for step in workflow.steps]


_STEP_OUTPUT_RE = re.compile(
    r"\$steps\.([A-Za-z0-9_-]+)\.outputs(?:\.([A-Za-z0-9_-]+)|\[['\"]([^'\"]+)['\"]\])"
)
_SOURCE_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_SOURCE_OPERATION_RE = re.compile(r"^\$sourceDescriptions\.([A-Za-z0-9_-]+)\.(.+)$")
_WORKFLOW_OUTPUT_RE = re.compile(r"\$workflows\.([A-Za-z0-9_-]+)\.outputs")
_EXPRESSION_RE = re.compile(
    r"\$(?:steps|workflows|inputs|response|request|statusCode|outputs|components)\b"
)
_SUPPORTED_RESPONSE_RE = re.compile(
    r"^\$(?:response\.(?:body(?:#/[A-Za-z0-9_~./-]*)?|header\.[A-Za-z0-9_.-]+|statusCode)|"
    r"inputs\.[A-Za-z0-9_.-]+|steps\.[A-Za-z0-9_-]+\.outputs(?:\.[A-Za-z0-9_-]+|\[['\"][^'\"]+['\"]\]))$"
)
_KNOWN_ROOT_KEYS = {"arazzo", "info", "sourceDescriptions", "workflows"}
_KNOWN_WORKFLOW_KEYS = {
    "workflowId",
    "summary",
    "description",
    "inputs",
    "steps",
    "outputs",
    "parameters",
    "dependsOn",
    "onSuccess",
    "onFailure",
}
_UNSUPPORTED_WORKFLOW_KEYS = {"outputs", "parameters", "dependsOn", "onSuccess", "onFailure"}
_KNOWN_STEP_KEYS = {
    "stepId",
    "description",
    "operationId",
    "operationPath",
    "parameters",
    "requestBody",
    "successCriteria",
    "failureActions",
    "onSuccess",
    "onFailure",
    "outputs",
    "dependsOn",
}
_UNSUPPORTED_STEP_KEYS = {
    "operationPath",
    "successCriteria",
    "failureActions",
    "onSuccess",
    "onFailure",
}


def build_arazzo_index(document: LoadedDocument) -> ArazzoIndex:
    root = document.data
    version = root.get("arazzo")
    if not isinstance(version, str) or not re.fullmatch(r"1\.1(?:\.\d+)?", version):
        raise InputError(
            f"only Arazzo 1.1.x is supported in the MVP ({document.path!s}, found {version!r})"
        )
    workflows = root.get("workflows")
    if not isinstance(workflows, list):
        raise InputError(f"Arazzo workflows must be an array: {document.path}")
    index = ArazzoIndex(document=document)
    _validate_refs(index)
    for key in root:
        if isinstance(key, str) and key not in _KNOWN_ROOT_KEYS and not key.startswith("x-"):
            index.diagnostics.append(
                _diag(
                    document,
                    "UNSUPPORTED_ARAZZO_FEATURE",
                    "unknown",
                    f"/{key}",
                    f"Arazzo root key is not supported by the MVP: {key}",
                    details={"key": key},
                )
            )
    source_descriptions = root.get("sourceDescriptions")
    if (
        not isinstance(source_descriptions, list)
        or len(source_descriptions) != 1
        or not isinstance(source_descriptions[0], dict)
        or source_descriptions[0].get("type") != "openapi"
        or not isinstance(source_descriptions[0].get("name"), str)
        or not source_descriptions[0]["name"]
        or not _SOURCE_NAME_RE.fullmatch(source_descriptions[0]["name"])
        or not isinstance(source_descriptions[0].get("url"), str)
        or not source_descriptions[0]["url"].strip()
    ):
        raise InputError(
            "MVP requires exactly one sourceDescriptions entry with type=openapi, "
            "a non-empty name matching [A-Za-z0-9_-]+, and a non-empty string url: "
            f"{document.path}"
        )
    source_names = {source_descriptions[0]["name"]}
    workflow_ids: set[str] = set()
    for workflow_number, workflow in enumerate(workflows):
        workflow_pointer = f"/workflows/{workflow_number}"
        if not isinstance(workflow, dict):
            index.diagnostics.append(
                _diag(
                    document,
                    "ARAZZO_WORKFLOW_INVALID",
                    "error",
                    workflow_pointer,
                    "workflow must be an object",
                )
            )
            continue
        workflow_id = workflow.get("workflowId")
        if not isinstance(workflow_id, str) or not workflow_id:
            index.diagnostics.append(
                _diag(
                    document,
                    "ARAZZO_WORKFLOW_INVALID",
                    "error",
                    workflow_pointer,
                    "workflowId must be a non-empty string",
                )
            )
            continue
        if workflow_id in workflow_ids:
            index.diagnostics.append(
                _diag(
                    document,
                    "ARAZZO_WORKFLOW_ID_DUPLICATE",
                    "error",
                    f"{workflow_pointer}/workflowId",
                    f"workflowId is duplicated: {workflow_id}",
                )
            )
        workflow_ids.add(workflow_id)
        _validate_unsupported_workflow_features(index, workflow_pointer, workflow)
        raw_steps = workflow.get("steps", [])
        if "steps" not in workflow:
            index.diagnostics.append(
                _diag(
                    document,
                    "ARAZZO_WORKFLOW_INVALID",
                    "error",
                    workflow_pointer,
                    "workflow must declare steps",
                )
            )
        if not isinstance(raw_steps, list):
            raise InputError(f"Arazzo workflow steps must be an array: {document.path}")
        steps: list[ArazzoStep] = []
        step_ids: set[str] = set()
        for step_number, raw_step in enumerate(raw_steps):
            step_pointer = f"{workflow_pointer}/steps/{step_number}"
            if not isinstance(raw_step, dict):
                index.diagnostics.append(
                    _diag(
                        document,
                        "ARAZZO_STEP_INVALID",
                        "error",
                        step_pointer,
                        "step must be an object",
                    )
                )
                continue
            step_id = raw_step.get("stepId")
            if not isinstance(step_id, str) or not step_id:
                index.diagnostics.append(
                    _diag(
                        document,
                        "ARAZZO_STEP_INVALID",
                        "error",
                        step_pointer,
                        "stepId must be a non-empty string",
                    )
                )
                continue
            step_ref = StepRef(
                document=document.path,
                workflow_id=workflow_id,
                step_id=step_id,
                source_pointer=step_pointer,
            )
            if step_id in step_ids:
                index.diagnostics.append(
                    _diag(
                        document,
                        "ARAZZO_STEP_ID_DUPLICATE",
                        "error",
                        f"{step_pointer}/stepId",
                        f"stepId is duplicated in workflow {workflow_id}: {step_id}",
                        steps=(step_ref,),
                    )
                )
            step_ids.add(step_id)
            operation_id_raw = raw_step.get("operationId")
            operation_path = raw_step.get("operationPath")
            operation_id = _normalise_operation_id(operation_id_raw, source_names)
            if operation_id is None and operation_path is None:
                index.diagnostics.append(
                    _diag(
                        document,
                        "ARAZZO_STEP_INVALID",
                        "error",
                        step_pointer,
                        "step must declare operationId or operationPath",
                        steps=(step_ref,),
                    )
                )
            output_names = _output_names(raw_step.get("outputs"))
            output_expressions = _output_expressions(raw_step.get("outputs"))
            refs = tuple(_step_output_refs(raw_step))
            dynamic_payload = _payload_is_dynamic(raw_step.get("requestBody"))
            _validate_unsupported_step_features(index, step_ref, raw_step)
            steps.append(
                ArazzoStep(
                    ref=step_ref,
                    operation_id=operation_id,
                    operation_path=operation_path if isinstance(operation_path, str) else None,
                    value=raw_step,
                    output_names=tuple(sorted(output_names)),
                    output_expressions=tuple(sorted(output_expressions.items())),
                    step_output_refs=refs,
                    has_dynamic_payload=dynamic_payload,
                )
            )
        _validate_step_references(index, workflow_id, steps)
        _validate_dependency_cycles(index, workflow_id, steps)
        index.workflows.append(
            ArazzoWorkflow(workflow_id=workflow_id, pointer=workflow_pointer, steps=tuple(steps))
        )
    return index


def _normalise_operation_id(value: Any, source_names: set[str]) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    source_match = _SOURCE_OPERATION_RE.fullmatch(value)
    if source_match:
        if source_match.group(1) in source_names and source_match.group(2):
            return source_match.group(2)
        return value
    if "." in value:
        prefix, operation_id = value.split(".", 1)
        if prefix in source_names and operation_id:
            return operation_id
    return value


def _output_names(value: Any) -> set[str]:
    if not isinstance(value, dict):
        return set()
    return {name for name in value if isinstance(name, str)}


def _output_expressions(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        name: expression
        for name, expression in value.items()
        if isinstance(name, str) and isinstance(expression, str)
    }


def _validate_output_values(index: ArazzoIndex, step_ref: StepRef, value: Any) -> None:
    if value is None:
        return
    output_pointer = f"{step_ref.source_pointer}/outputs"
    if not isinstance(value, dict):
        _append_unsupported(
            index,
            step_ref,
            output_pointer,
            "Arazzo step outputs must be a mapping of names to runtime expressions",
        )
        return
    for name, expression in value.items():
        pointer = f"{output_pointer}/{escape_pointer(str(name))}"
        if not isinstance(name, str) or not isinstance(expression, str):
            _append_unsupported(
                index,
                step_ref,
                pointer,
                "Arazzo step output names and values must be strings",
                output=str(name),
            )
            continue
        if not _SUPPORTED_RESPONSE_RE.fullmatch(expression):
            _append_unsupported(
                index,
                step_ref,
                pointer,
                f"step output expression is outside the MVP expression subset: {expression}",
                expression=expression,
            )


def _validate_unsupported_step_features(
    index: ArazzoIndex, step_ref: StepRef, step: dict[str, Any]
) -> None:
    for key in sorted(step):
        if key.startswith("x-"):
            continue
        if key not in _KNOWN_STEP_KEYS:
            _append_unsupported(
                index,
                step_ref,
                f"{step_ref.source_pointer}/{key}",
                f"Arazzo step key is not supported by the MVP: {key}",
                key=key,
            )
        elif key in _UNSUPPORTED_STEP_KEYS:
            _append_unsupported(
                index,
                step_ref,
                f"{step_ref.source_pointer}/{key}",
                f"Arazzo feature is not evaluated by the MVP: {key}",
                key=key,
            )
    _validate_output_values(index, step_ref, step.get("outputs"))
    output_prefix = f"{step_ref.source_pointer}/outputs/"
    for pointer, key in _keys_with_pointers(step, step_ref.source_pointer):
        if key == "selector" and pointer != f"{step_ref.source_pointer}/selector":
            _append_unsupported(
                index,
                step_ref,
                pointer,
                "Arazzo selector expressions are not evaluated by the MVP",
                key=key,
            )
    for pointer, value in iter_refs(step, step_ref.source_pointer):
        _append_unsupported(
            index,
            step_ref,
            pointer,
            "parameter and reusable Arazzo $ref values are outside the MVP",
            ref=value,
        )
    request_body = step.get("requestBody")
    if isinstance(request_body, dict) and "contentType" in request_body:
        content_type = request_body.get("contentType")
        if (
            not isinstance(content_type, str)
            or content_type.split(";", 1)[0].strip().lower() != "application/json"
        ):
            _append_unsupported(
                index,
                step_ref,
                f"{step_ref.source_pointer}/requestBody/contentType",
                "only application/json request bodies are evaluated by the MVP",
                contentType=str(content_type),
            )
    for pointer, value in _strings_with_pointers(step, step_ref.source_pointer):
        if pointer.startswith(output_prefix):
            continue
        if not _EXPRESSION_RE.search(value):
            continue
        if pointer.endswith("/operationId") and _SOURCE_OPERATION_RE.fullmatch(value):
            continue
        if _SUPPORTED_RESPONSE_RE.fullmatch(value):
            continue
        _append_unsupported(
            index,
            step_ref,
            pointer,
            f"runtime expression is outside the MVP expression subset: {value}",
            expression=value,
        )


def _validate_unsupported_workflow_features(
    index: ArazzoIndex, workflow_pointer: str, workflow: dict[str, Any]
) -> None:
    for key in sorted(workflow):
        if key.startswith("x-"):
            continue
        if key not in _KNOWN_WORKFLOW_KEYS:
            _append_unsupported(
                index,
                None,
                f"{workflow_pointer}/{key}",
                f"Arazzo workflow key is not supported by the MVP: {key}",
                key=key,
            )
        elif key in _UNSUPPORTED_WORKFLOW_KEYS:
            _append_unsupported(
                index,
                None,
                f"{workflow_pointer}/{key}",
                f"Arazzo workflow feature is not evaluated by the MVP: {key}",
                key=key,
            )


def _append_unsupported(
    index: ArazzoIndex,
    step_ref: StepRef | None,
    pointer: str,
    message: str,
    **details: str,
) -> None:
    index.diagnostics.append(
        _diag(
            index.document,
            "UNSUPPORTED_ARAZZO_FEATURE",
            "unknown",
            pointer,
            message,
            steps=(step_ref,) if step_ref is not None else (),
            details=details,
        )
    )


def _strings_with_pointers(value: Any, pointer: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield pointer, value
    elif isinstance(value, dict):
        for key, item in value.items():
            child = f"{pointer}/{str(key).replace('~', '~0').replace('/', '~1')}"
            yield from _strings_with_pointers(item, child)
    elif isinstance(value, list):
        for number, item in enumerate(value):
            yield from _strings_with_pointers(item, f"{pointer}/{number}")


def _keys_with_pointers(value: Any, pointer: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{pointer}/{escape_pointer(str(key))}"
            yield child, str(key)
            yield from _keys_with_pointers(item, child)
    elif isinstance(value, list):
        for number, item in enumerate(value):
            yield from _keys_with_pointers(item, f"{pointer}/{number}")


def _step_output_refs(value: Any) -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for item in value.values():
            yield from _step_output_refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from _step_output_refs(item)
    elif isinstance(value, str):
        for match in _STEP_OUTPUT_RE.finditer(value):
            output_name = match.group(2) or match.group(3)
            if output_name:
                yield match.group(1), output_name


def _payload_is_dynamic(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(_EXPRESSION_RE.search(value))
    if isinstance(value, dict):
        return any(_payload_is_dynamic(item) for item in value.values())
    if isinstance(value, list):
        return any(_payload_is_dynamic(item) for item in value)
    return False


def _validate_step_references(
    index: ArazzoIndex, workflow_id: str, steps: list[ArazzoStep]
) -> None:
    known = {step.ref.step_id for step in steps}
    outputs = {step.ref.step_id: set(step.output_names) for step in steps}
    for step in steps:
        for target_step, output_name in step.step_output_refs:
            if target_step not in known or output_name not in outputs[target_step]:
                index.diagnostics.append(
                    _diag(
                        index.document,
                        "ARAZZO_STEP_OUTPUT_MISSING",
                        "error",
                        step.ref.source_pointer,
                        f"step {step.ref.step_id} references missing output "
                        f"{target_step}.{output_name}",
                        steps=(step.ref,),
                        details={"targetStep": target_step, "output": output_name},
                    )
                )
        depends_on = step.value.get("dependsOn", [])
        if isinstance(depends_on, list):
            for target in depends_on:
                if isinstance(target, str) and target not in known:
                    index.diagnostics.append(
                        _diag(
                            index.document,
                            "ARAZZO_STEP_OUTPUT_MISSING",
                            "error",
                            f"{step.ref.source_pointer}/dependsOn",
                            f"step {step.ref.step_id} depends on missing step {target}",
                            steps=(step.ref,),
                            details={"targetStep": target},
                        )
                    )
        for value in _all_strings(step.value):
            if _WORKFLOW_OUTPUT_RE.search(value):
                index.diagnostics.append(
                    _diag(
                        index.document,
                        "UNSUPPORTED_ARAZZO_FEATURE",
                        "unknown",
                        step.ref.source_pointer,
                        "cross-workflow output references are not evaluated in the MVP",
                        steps=(step.ref,),
                    )
                )


def _validate_dependency_cycles(
    index: ArazzoIndex, workflow_id: str, steps: list[ArazzoStep]
) -> None:
    graph: dict[str, set[str]] = {step.ref.step_id: set() for step in steps}
    for step in steps:
        depends_on = step.value.get("dependsOn", [])
        if isinstance(depends_on, list):
            graph[step.ref.step_id].update(
                item for item in depends_on if isinstance(item, str) and item in graph
            )
        graph[step.ref.step_id].update(
            target for target, _ in step.step_output_refs if target in graph
        )
    state: dict[str, int] = {key: 0 for key in graph}

    def visit(node: str) -> bool:
        state[node] = 1
        for target in sorted(graph[node]):
            if state[target] == 1:
                return True
            if state[target] == 0 and visit(target):
                return True
        state[node] = 2
        return False

    if any(state[node] == 0 and visit(node) for node in sorted(graph)):
        affected = tuple(step.ref for step in steps if state[step.ref.step_id] == 1)
        index.diagnostics.append(
            _diag(
                index.document,
                "ARAZZO_DEPENDENCY_CYCLE",
                "error",
                f"/workflows/{workflow_id}",
                f"workflow dependency graph contains a cycle: {workflow_id}",
                steps=affected,
            )
        )


def _all_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _all_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _all_strings(item)


def _validate_refs(index: ArazzoIndex) -> None:
    for pointer, value in iter_refs(index.document.data):
        if value.startswith("#/"):
            try:
                pointer_get(index.document.data, value[1:])
            except KeyError:
                index.diagnostics.append(
                    _diag(
                        index.document,
                        "ARAZZO_REF_UNRESOLVED",
                        "error",
                        pointer,
                        f"internal Arazzo reference cannot be resolved: {value}",
                        details={"ref": value},
                    )
                )
        elif value:
            index.diagnostics.append(
                _diag(
                    index.document,
                    "UNSUPPORTED_EXTERNAL_REF",
                    "unknown",
                    pointer,
                    f"external Arazzo reference is outside the MVP: {value}",
                    details={"ref": value},
                )
            )
    validate_ref_depth(index.document.data, index.document.path)


def _diag(
    document: LoadedDocument,
    code: str,
    severity: str,
    pointer: str,
    message: str,
    steps: tuple[StepRef, ...] = (),
    details: dict[str, Any] | None = None,
) -> Diagnostic:
    return Diagnostic(
        schema_version="0.1",
        code=code,
        severity=severity,  # type: ignore[arg-type]
        source_file=document.path,
        source_pointer=pointer,
        message=message,
        affected_steps=steps,
        details=details or {},
    )
