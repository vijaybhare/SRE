from __future__ import annotations

import sys
import argparse

from arch_compliance import extractors
from arch_compliance.evaluator import evaluate
from arch_compliance.llm import DEFAULT_MODEL
from arch_compliance.rubric import load_rubric, normalize_standards, save_rubric
from arch_compliance.scorer import score

from . import report
from .default_rubric import DEFAULT_RUBRIC
from .gate import decide


def cmd_normalize_criteria(args: argparse.Namespace) -> None:
    docs = [extractors.extract(p, render_images=False) for p in args.input]
    items = normalize_standards(docs, model=args.model)
    save_rubric(items, args.output)
    print(f"Wrote {len(items)} PRR criteria to {args.output}")


def cmd_assess(args: argparse.Namespace) -> None:
    rubric = load_rubric(args.rubric) if args.rubric else DEFAULT_RUBRIC
    change = extractors.extract(args.change, render_images=True)
    results = evaluate(change, rubric, model=args.model)
    readiness_report = score(rubric, results)
    gate = decide(rubric, results)

    if args.format == "json":
        output = report.to_json(readiness_report, gate, change.source)
    else:
        output = report.to_markdown(readiness_report, gate, change.source)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Wrote report to {args.output}")
    else:
        print(output)

    print(
        f"\nGate decision: {gate.decision} "
        f"(readiness {readiness_report.overall_percentage}%, "
        f"{len(gate.blocking_items)} blocking, {len(gate.at_risk_items)} at risk)",
        file=sys.stderr,
    )
    if gate.decision == "NOT READY":
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="prr-readiness",
        description=(
            "Assess a change/service against SRE production-readiness criteria "
            "for the Production Readiness Review (PRR) gate."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_norm = sub.add_parser(
        "normalize-criteria",
        help=(
            "Convert your org's own SRE readiness standards documents (PDF/Word/Excel) "
            "into a rubric JSON file, instead of using the built-in default rubric"
        ),
    )
    p_norm.add_argument("--input", nargs="+", required=True, help="SRE standards document(s)")
    p_norm.add_argument("--output", required=True, help="Path to write rubric JSON")
    p_norm.add_argument("--model", default=DEFAULT_MODEL)
    p_norm.set_defaults(func=cmd_normalize_criteria)

    p_assess = sub.add_parser(
        "assess",
        help="Assess a change/release document against SRE PRR criteria and get a gate decision",
    )
    p_assess.add_argument(
        "--change", required=True, help="Change/release documentation (PDF/Word)"
    )
    p_assess.add_argument(
        "--rubric",
        help="Rubric JSON from normalize-criteria (default: built-in SRE Workbook PRR rubric)",
    )
    p_assess.add_argument("--output", help="Path to write the report (default: stdout)")
    p_assess.add_argument("--format", choices=["md", "json"], default="md")
    p_assess.add_argument("--model", default=DEFAULT_MODEL)
    p_assess.set_defaults(func=cmd_assess)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
