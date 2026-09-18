"""Render a ComplianceReport as JSON or Markdown."""
from __future__ import annotations

import json
from dataclasses import asdict

from .scorer import ComplianceReport

VERDICT_ICON = {"pass": "✅", "partial": "⚠️", "fail": "❌", "not_applicable": "➖"}


def to_json(report: ComplianceReport) -> str:
    return json.dumps(
        {
            "overall_percentage": report.overall_percentage,
            "total_earned": report.total_earned,
            "total_possible": report.total_possible,
            "by_category": [asdict(c) for c in report.by_category],
            "items": report.items,
        },
        indent=2,
    )


def to_markdown(report: ComplianceReport, architecture_source: str) -> str:
    lines = [
        f"# Architecture Compliance Report",
        "",
        f"**Source document:** {architecture_source}",
        f"**Overall compliance: {report.overall_percentage}%** "
        f"({report.total_earned:g} / {report.total_possible:g} weighted points)",
        "",
        "## By category",
        "",
        "| Category | Score |",
        "|---|---|",
    ]
    for cat in report.by_category:
        lines.append(f"| {cat.category} | {cat.percentage}% |")

    lines += ["", "## Findings", ""]
    for item in sorted(report.items, key=lambda i: (i["category"], i["id"])):
        icon = VERDICT_ICON.get(item["verdict"], "•")
        lines.append(f"### {icon} {item['id']} — {item['category']} (weight {item['weight']})")
        lines.append(f"**Requirement:** {item['requirement']}")
        lines.append(f"**Verdict:** {item['verdict']}")
        if item.get("evidence"):
            lines.append(f"**Evidence:** {item['evidence']}")
        if item.get("rationale"):
            lines.append(f"**Rationale:** {item['rationale']}")
        lines.append("")

    return "\n".join(lines)
