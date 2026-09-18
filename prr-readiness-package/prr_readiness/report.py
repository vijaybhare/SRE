"""Render a PRR assessment (score + gate decision) as Markdown or JSON."""
from __future__ import annotations

import json
from dataclasses import asdict

from arch_compliance.report import VERDICT_ICON
from arch_compliance.scorer import ComplianceReport

from .gate import GateDecision

DECISION_ICON = {"READY": "✅", "CONDITIONAL": "⚠️", "NOT READY": "⛔"}


def to_json(report: ComplianceReport, gate: GateDecision, change_source: str) -> str:
    return json.dumps(
        {
            "change": change_source,
            "gate_decision": gate.decision,
            "overall_readiness_percentage": report.overall_percentage,
            "blocking_items": gate.blocking_items,
            "at_risk_items": gate.at_risk_items,
            "by_category": [asdict(c) for c in report.by_category],
            "items": report.items,
        },
        indent=2,
    )


def to_markdown(report: ComplianceReport, gate: GateDecision, change_source: str) -> str:
    icon = DECISION_ICON.get(gate.decision, "")
    lines = [
        "# Production Readiness Review",
        "",
        f"**Change:** {change_source}",
        f"**Gate decision: {icon} {gate.decision}**",
        f"**Overall readiness: {report.overall_percentage}%** "
        f"({report.total_earned:g} / {report.total_possible:g} weighted points)",
        "",
    ]

    if gate.blocking_items:
        lines += ["## Blocking (mandatory, failed)", ""]
        for item in gate.blocking_items:
            lines.append(f"- **{item['id']}** ({item['category']}): {item['requirement']}")
            if item.get("rationale"):
                lines.append(f"  - {item['rationale']}")
        lines.append("")

    if gate.at_risk_items:
        lines += ["## At risk (mandatory, partial)", ""]
        for item in gate.at_risk_items:
            lines.append(f"- **{item['id']}** ({item['category']}): {item['requirement']}")
            if item.get("rationale"):
                lines.append(f"  - {item['rationale']}")
        lines.append("")

    lines += ["## By category", "", "| Category | Score |", "|---|---|"]
    for cat in report.by_category:
        lines.append(f"| {cat.category} | {cat.percentage}% |")

    lines += ["", "## Findings", ""]
    for item in sorted(report.items, key=lambda i: (i["category"], i["id"])):
        vicon = VERDICT_ICON.get(item["verdict"], "•")
        lines.append(f"### {vicon} {item['id']} — {item['category']} (weight {item['weight']})")
        lines.append(f"**Requirement:** {item['requirement']}")
        lines.append(f"**Verdict:** {item['verdict']}")
        if item.get("evidence"):
            lines.append(f"**Evidence:** {item['evidence']}")
        if item.get("rationale"):
            lines.append(f"**Rationale:** {item['rationale']}")
        lines.append("")

    return "\n".join(lines)
