from __future__ import annotations

from .models import Diagnostic, Impact, Report


def render_markdown(report: Report) -> str:
    summary = report.summary()
    lines = [
        "# Procedure CI impact report",
        "",
        "## 结论",
        "",
        f"- 工作流：{summary['workflows']}",
        f"- 受影响步骤：{summary['affectedSteps']}",
        f"- 确定性错误：{summary['errors']}",
        f"- 需要审查：{summary['reviews']}",
        f"- 未知项：{summary['unknowns']}",
        "",
    ]
    impacts = report.sorted_impacts()
    if impacts:
        lines.extend(["## 受影响步骤", ""])
        for impact in impacts:
            lines.extend(_render_impact(impact))
    diagnostics = report.sorted_diagnostics()
    if diagnostics:
        lines.extend(["## 诊断", ""])
        for diagnostic in diagnostics:
            lines.extend(_render_diagnostic(diagnostic))
    if not impacts and not diagnostics:
        lines.extend(["## 结果", "", "未检测到受影响的 Arazzo workflow step。", ""])
    return "\n".join(lines)


def _render_impact(impact: Impact) -> list[str]:
    lines = [
        f"### `{impact.step.workflow_id}/{impact.step.step_id}`",
        "",
        f"严重级别：`{impact.severity}`；来源：`{impact.step.document}` "
        f"(`{impact.step.source_pointer}`)",
        "",
        "变化：",
    ]
    for change in impact.changes:
        paths = ", ".join(f"`{path}`" for path in change.changed_paths)
        lines.append(
            f"- `{change.entity.kind}` `{change.entity.canonical_id}`："
            f"`{change.status}`，{change.change_class}，路径 {paths}"
        )
    if impact.dependency_paths:
        lines.extend(["", "依赖路径："])
        for path in impact.dependency_paths:
            lines.append("- " + " → ".join(f"`{item.kind}:{item.canonical_id}`" for item in path))
    lines.append("")
    return lines


def _render_diagnostic(diagnostic: Diagnostic) -> list[str]:
    affected = (
        ", ".join(f"{step.workflow_id}/{step.step_id}" for step in diagnostic.affected_steps)
        or "全局"
    )
    return [
        f"- **`{diagnostic.severity}` `{diagnostic.code}`**：{diagnostic.message} "
        f"（`{diagnostic.source_file}{diagnostic.source_pointer}`；影响：{affected}）",
    ]
