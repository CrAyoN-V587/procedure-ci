from __future__ import annotations

import json
from pathlib import Path

from .models import Report


def render_json(report: Report) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_json(report: Report, output: str | Path) -> None:
    Path(output).write_text(render_json(report), encoding="utf-8")
