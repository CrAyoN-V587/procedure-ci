from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["error", "review", "unknown", "info"]
ChangeStatus = Literal["added", "removed", "modified"]
ChangeClass = Literal["behavior", "example", "documentation"]


@dataclass(frozen=True, order=True)
class EntityRef:
    source_name: str
    kind: str
    canonical_id: str
    source_pointer: str

    def key(self) -> str:
        return f"{self.kind}:{self.canonical_id}"

    def to_dict(self) -> dict[str, str]:
        return {
            "sourceName": self.source_name,
            "kind": self.kind,
            "canonicalId": self.canonical_id,
            "sourcePointer": self.source_pointer,
        }


@dataclass(frozen=True, order=True)
class StepRef:
    document: str
    workflow_id: str
    step_id: str
    source_pointer: str

    def key(self) -> str:
        return f"{self.workflow_id}:{self.step_id}"

    def to_dict(self) -> dict[str, str]:
        return {
            "document": self.document,
            "workflowId": self.workflow_id,
            "stepId": self.step_id,
            "sourcePointer": self.source_pointer,
        }


@dataclass(frozen=True)
class DependencyEdge:
    step: StepRef
    entity: EntityRef
    reason: str
    via: tuple[EntityRef, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step.to_dict(),
            "entity": self.entity.to_dict(),
            "reason": self.reason,
            "via": [item.to_dict() for item in self.via],
        }


@dataclass(frozen=True)
class EntityChange:
    entity: EntityRef
    status: ChangeStatus
    changed_paths: tuple[str, ...]
    change_class: ChangeClass
    before: Any = None
    after: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity": self.entity.to_dict(),
            "status": self.status,
            "changedPaths": list(self.changed_paths),
            "changeClass": self.change_class,
        }


@dataclass(frozen=True)
class Diagnostic:
    schema_version: str
    code: str
    severity: Severity
    source_file: str
    source_pointer: str
    message: str
    affected_steps: tuple[StepRef, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    def sort_key(self) -> tuple[Any, ...]:
        severity_order = {"error": 0, "review": 1, "unknown": 2, "info": 3}
        return (
            severity_order.get(self.severity, 9),
            self.code,
            self.source_file,
            self.source_pointer,
            tuple(step.key() for step in self.affected_steps),
            self.message,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "code": self.code,
            "severity": self.severity,
            "sourceFile": self.source_file,
            "sourcePointer": self.source_pointer,
            "message": self.message,
            "affectedSteps": [step.to_dict() for step in self.affected_steps],
            "details": self.details,
        }


@dataclass
class Impact:
    step: StepRef
    changes: list[EntityChange] = field(default_factory=list)
    dependency_paths: list[list[EntityRef]] = field(default_factory=list)
    severity: Severity = "review"
    deterministic_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step.to_dict(),
            "severity": self.severity,
            "deterministicError": self.deterministic_error,
            "changes": [change.to_dict() for change in self.changes],
            "dependencyPaths": [
                [entity.to_dict() for entity in path] for path in self.dependency_paths
            ],
        }


@dataclass
class Report:
    schema_version: str = "0.1"
    impacts: list[Impact] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def sorted_impacts(self) -> list[Impact]:
        return sorted(self.impacts, key=lambda item: item.step.key())

    def sorted_diagnostics(self) -> list[Diagnostic]:
        return sorted(self.diagnostics, key=lambda item: item.sort_key())

    def summary(self) -> dict[str, int]:
        errors = sum(item.severity == "error" for item in self.diagnostics)
        reviews = sum(item.severity == "review" for item in self.diagnostics)
        unknowns = sum(item.severity == "unknown" for item in self.diagnostics)
        return {
            "workflows": len({item.step.workflow_id for item in self.impacts}),
            "affectedSteps": len(self.impacts),
            "errors": errors,
            "reviews": reviews,
            "unknowns": unknowns,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "summary": self.summary(),
            "impacts": [item.to_dict() for item in self.sorted_impacts()],
            "diagnostics": [item.to_dict() for item in self.sorted_diagnostics()],
        }
