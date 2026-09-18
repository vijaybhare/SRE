from __future__ import annotations

import argparse
import sys

from . import extractors, report
from .evaluator import evaluate
from .llm import DEFAULT_MODEL
from .rubric import load_rubric, normalize_standards, save_rubric
from .scorer import score


def cmd_normalize_standards(args: argparse.Namespace) -> None:
    docs = [extractors.extract(p, render_images=False) for p in args.input]
    items = normalize_standards(docs, model=args.model)
    save_rubric(items, args.output)
    print(f"Wrote {len(items)} rubric items to {args.output}")


def cmd_evaluate(args: argparse.Namespace) -> None:
    rubric = load_rubric(args.rubric)
    architecture = extractors.extract(args.architecture, render_images=True)
    results = evaluate(architecture, rubric, model=args.model)
    compliance_report = score(rubric, results)

    if args.format == "json":
        output = report.to_json(compliance_report)
    else:
        output = report.to_markdown(compliance_report, architecture.source)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Wrote report to {args.output}")
    else:
        print(output)

    print(f"\nOverall compliance: {compliance_report.overall_percentage}%", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="arch-compliance",
        description="Score a solution architecture document against your org's architecture standards.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_norm = sub.add_parser(
        "normalize-standards",
        help="Convert one or more standards documents (PDF/Word/Excel) into a rubric JSON file",
    )
    p_norm.add_argument("--input", nargs="+", required=True, help="Standards document(s)")
    p_norm.add_argument("--output", required=True, help="Path to write rubric JSON")
    p_norm.add_argument("--model", default=DEFAULT_MODEL)
    p_norm.set_defaults(func=cmd_normalize_standards)

    p_eval = sub.add_parser(
        "evaluate", help="Evaluate an architecture document against a rubric"
    )
    p_eval.add_argument("--architecture", required=True, help="Architecture document (PDF/Word)")
    p_eval.add_argument("--rubric", required=True, help="Rubric JSON produced by normalize-standards")
    p_eval.add_argument("--output", help="Path to write the report (default: stdout)")
    p_eval.add_argument("--format", choices=["md", "json"], default="md")
    p_eval.add_argument("--model", default=DEFAULT_MODEL)
    p_eval.set_defaults(func=cmd_evaluate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
