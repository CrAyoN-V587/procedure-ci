from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import analyze
from .errors import ProcedureCIError
from .report_json import render_json
from .report_markdown import render_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="procedure-ci",
        description="Analyze Arazzo workflow impact from base/head OpenAPI documents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="run deterministic offline impact analysis")
    check.add_argument("--base-openapi", required=True, type=Path)
    check.add_argument("--head-openapi", required=True, type=Path)
    check.add_argument(
        "--arazzo",
        "--current-arazzo",
        dest="arazzo",
        required=True,
        type=Path,
        help="current Arazzo workflow document (the third input)",
    )
    check.add_argument("--format", choices=("json", "markdown"), default="json")
    check.add_argument("--output", type=Path, help="write report to a file instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "check":
        return 2
    try:
        report = analyze(args.base_openapi, args.head_openapi, args.arazzo)
    except ProcedureCIError as exc:
        print(f"procedure-ci: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"procedure-ci: {exc}", file=sys.stderr)
        return 2
    text = render_json(report) if args.format == "json" else render_markdown(report)
    try:
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
    except OSError as exc:
        print(f"procedure-ci: cannot write report: {exc}", file=sys.stderr)
        return 2
    return 1 if report.summary()["errors"] else 0
