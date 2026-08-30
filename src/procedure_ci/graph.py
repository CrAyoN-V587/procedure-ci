from __future__ import annotations

from dataclasses import dataclass, field

from .arazzo_index import ArazzoIndex
from .models import DependencyEdge, EntityRef, StepRef
from .oas_index import OasIndex


@dataclass(frozen=True)
class StepDependency:
    """A directed workflow dependency from a consumer to its producer."""

    producer: StepRef
    consumer: StepRef
    reason: str


@dataclass
class DependencyGraph:
    edges_by_step: dict[str, list[DependencyEdge]] = field(default_factory=dict)
    steps_by_operation: dict[str, list[StepRef]] = field(default_factory=dict)
    step_dependencies: dict[str, list[StepDependency]] = field(default_factory=dict)

    def edges_for(self, step: StepRef) -> list[DependencyEdge]:
        return self.edges_by_step.get(step.key(), [])

    def dependencies_for(self, consumer: StepRef) -> list[StepDependency]:
        return self.step_dependencies.get(consumer.key(), [])

    def dependency_chains_for(self, consumer: StepRef) -> list[tuple[StepRef, ...]]:
        """Return all finite producer-to-ancestor chains for a consumer.

        A chain is ordered from the consumer's immediate producer toward the
        oldest producer. Arazzo cycles are diagnosed while indexing; the active
        set here is still needed to keep impact reporting bounded for invalid
        input.
        """

        chains: list[tuple[StepRef, ...]] = []

        def visit(producer: StepRef, chain: tuple[StepRef, ...], active: set[str]) -> None:
            chains.append(chain)
            producer_key = producer.key()
            if producer_key in active:
                return
            next_active = {*active, producer_key}
            for dependency in sorted(
                self.dependencies_for(producer), key=lambda item: (item.producer.key(), item.reason)
            ):
                visit(dependency.producer, (*chain, dependency.producer), next_active)

        for dependency in sorted(
            self.dependencies_for(consumer), key=lambda item: (item.producer.key(), item.reason)
        ):
            visit(dependency.producer, (dependency.producer,), set())
        return sorted(chains, key=lambda chain: tuple(item.key() for item in chain))

    def paths_for(self, step: StepRef, entity_key: str) -> list[list[EntityRef]]:
        paths: list[list[EntityRef]] = []
        for edge in self.edges_for(step):
            if edge.entity.key() == entity_key:
                paths.append([*edge.via, edge.entity])
        return paths


def build_dependency_graph(
    arazzo: ArazzoIndex, oas: OasIndex, *additional_oas: OasIndex
) -> DependencyGraph:
    """Build the union of reachable dependencies in each supplied OAS version.

    Keeping base and head edges preserves the old source pointer when an entity
    is removed or moved, while still allowing the current Arazzo to bind to the
    head operation whenever it exists. Step-to-step dependencies are rebuilt in
    each version and merged, so a downstream consumer can inherit changes from
    any producer at arbitrary depth.
    """

    graph = DependencyGraph()
    for index in (oas, *additional_oas):
        version_graph = _build_direct_graph(arazzo, index)
        _merge_graph(graph, version_graph)
    return graph


def _build_direct_graph(arazzo: ArazzoIndex, oas: OasIndex) -> DependencyGraph:
    graph = DependencyGraph()
    for step in arazzo.steps:
        graph.edges_by_step.setdefault(step.ref.key(), [])
        graph.step_dependencies.setdefault(step.ref.key(), [])
        if not step.operation_id:
            continue
        operation = oas.operation(step.operation_id)
        if operation is None:
            continue
        operation_edge = DependencyEdge(
            step=step.ref,
            entity=operation.ref,
            reason="operation",
        )
        graph.edges_by_step[step.ref.key()].append(operation_edge)
        graph.steps_by_operation.setdefault(step.operation_id, []).append(step.ref)
        for dependency_key in operation.dependency_keys:
            if dependency_key == operation.ref.key():
                continue
            entity_record = oas.entity(dependency_key)
            if entity_record is None:
                continue
            graph.edges_by_step[step.ref.key()].append(
                DependencyEdge(
                    step=step.ref,
                    entity=entity_record.ref,
                    reason="transitive_ref" if entity_record.ref.kind == "schema" else "dependency",
                    via=(operation.ref,),
                )
            )
    _add_step_dependencies(graph, arazzo)
    direct_edges = {key: list(edges) for key, edges in graph.edges_by_step.items()}
    _add_step_dependency_edges(graph, arazzo, direct_edges)
    for edges in graph.edges_by_step.values():
        edges.sort(
            key=lambda edge: (
                edge.entity.kind,
                edge.entity.canonical_id,
                edge.entity.source_name,
                edge.entity.source_pointer,
                edge.reason,
                tuple(item.key() for item in edge.via),
            )
        )
    for steps in graph.steps_by_operation.values():
        steps.sort(key=lambda item: item.key())
    for dependencies in graph.step_dependencies.values():
        dependencies.sort(key=lambda item: (item.producer.key(), item.reason))
    return graph


def _add_step_dependencies(graph: DependencyGraph, arazzo: ArazzoIndex) -> None:
    for workflow in arazzo.workflows:
        producers = {step.ref.step_id: step for step in workflow.steps}
        for consumer in workflow.steps:
            targets: dict[str, str] = {}
            for producer_id, _ in consumer.step_output_refs:
                if producer_id in producers:
                    targets[producer_id] = "step_output"
            depends_on = consumer.value.get("dependsOn", [])
            if isinstance(depends_on, list):
                for producer_id in depends_on:
                    if isinstance(producer_id, str) and producer_id in producers:
                        targets.setdefault(producer_id, "depends_on")
            for producer_id, reason in sorted(targets.items()):
                dependency = StepDependency(
                    producer=producers[producer_id].ref,
                    consumer=consumer.ref,
                    reason=reason,
                )
                _append_step_dependency(graph, dependency)


def _add_step_dependency_edges(
    graph: DependencyGraph,
    arazzo: ArazzoIndex,
    direct_edges: dict[str, list[DependencyEdge]],
) -> None:
    for consumer in arazzo.steps:
        for chain in graph.dependency_chains_for(consumer.ref):
            upstream = chain[-1]
            markers = tuple(_step_marker(step) for step in chain)
            dependency = next(
                (
                    item
                    for item in graph.dependencies_for(consumer.ref)
                    if item.producer.key() == chain[0].key()
                ),
                None,
            )
            reason = dependency.reason if dependency is not None else "step_dependency"
            for edge in direct_edges.get(upstream.key(), []):
                _append_edge(
                    graph,
                    DependencyEdge(
                        step=consumer.ref,
                        entity=edge.entity,
                        reason=reason,
                        via=(*markers, *edge.via),
                    ),
                )


def _step_marker(step: StepRef) -> EntityRef:
    return EntityRef(
        source_name=step.document,
        kind="workflow_step",
        canonical_id=step.key(),
        source_pointer=step.source_pointer,
    )


def _append_step_dependency(graph: DependencyGraph, dependency: StepDependency) -> None:
    dependencies = graph.step_dependencies.setdefault(dependency.consumer.key(), [])
    key = (dependency.producer.key(), dependency.reason)
    if any((item.producer.key(), item.reason) == key for item in dependencies):
        return
    dependencies.append(dependency)


def _merge_graph(target: DependencyGraph, source: DependencyGraph) -> None:
    for step_key, edges in source.edges_by_step.items():
        target.edges_by_step.setdefault(step_key, [])
        for edge in edges:
            _append_edge(target, edge)
    for operation_id, steps in source.steps_by_operation.items():
        target.steps_by_operation.setdefault(operation_id, [])
        for step in steps:
            if step not in target.steps_by_operation[operation_id]:
                target.steps_by_operation[operation_id].append(step)
    for consumer_key, dependencies in source.step_dependencies.items():
        target.step_dependencies.setdefault(consumer_key, [])
        for dependency in dependencies:
            _append_step_dependency(target, dependency)
        target.step_dependencies[consumer_key].sort(
            key=lambda item: (item.producer.key(), item.reason)
        )


def _append_edge(graph: DependencyGraph, edge: DependencyEdge) -> None:
    edges = graph.edges_by_step.setdefault(edge.step.key(), [])
    edge_key = (
        edge.entity.kind,
        edge.entity.canonical_id,
        edge.entity.source_name,
        edge.entity.source_pointer,
        edge.reason,
        tuple(
            (item.kind, item.canonical_id, item.source_name, item.source_pointer)
            for item in edge.via
        ),
    )
    existing = {
        (
            item.entity.kind,
            item.entity.canonical_id,
            item.entity.source_name,
            item.entity.source_pointer,
            item.reason,
            tuple(
                (via.kind, via.canonical_id, via.source_name, via.source_pointer)
                for via in item.via
            ),
        )
        for item in edges
    }
    if edge_key not in existing:
        edges.append(edge)
