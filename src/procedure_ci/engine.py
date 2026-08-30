from __future__ import annotations

from pathlib import Path

from .arazzo_index import build_arazzo_index
from .checks import run_checks
from .compare import compare_oas
from .graph import build_dependency_graph
from .loader import load_document
from .models import Report
from .oas_index import build_oas_index


def analyze(
    base_openapi: str | Path,
    head_openapi: str | Path,
    arazzo: str | Path,
) -> Report:
    """Analyze one current Arazzo document against base/head OpenAPI documents."""

    base_doc = load_document(base_openapi)
    head_doc = load_document(head_openapi)
    arazzo_doc = load_document(arazzo)
    base_index = build_oas_index(base_doc)
    head_index = build_oas_index(head_doc)
    arazzo_index = build_arazzo_index(arazzo_doc)
    graph = build_dependency_graph(arazzo_index, head_index, base_index)
    comparison = compare_oas(base_index, head_index)
    return run_checks(base_index, head_index, arazzo_index, graph, comparison)
