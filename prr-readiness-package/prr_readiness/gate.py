"""Turn a scored PRR assessment into a Ready / Conditional / Not Ready gate decision.

Mirrors the PRR step in the release flow: mandatory SRE criteria are hard gates
(a single failed mandatory item blocks go-live), non-mandatory items only
affect the overall readiness percentage.
"""
from __future__ import annotations

from dataclasses import dataclass

from arch_compliance.evaluator import EvalResult
from arch_compliance.rubric import RubricItem

READY = "READY"
CONDITIONAL = "CONDITIONAL"
NOT_READY = "NOT READY"


@dataclass
class GateDecision:
    decision: str
    blocking_items: list[dict]
    at_risk_items: list[dict]


def decide(rubric: list[RubricItem], results: list[EvalResult]) -> GateDecision:
    results_by_id = {r.id: r for r in results}
    blocking: list[dict] = []
    at_risk: list[dict] = []

    for item in rubric:
        if not item.mandatory:
            continue
        result = results_by_id.get(item.id)
        if result is None:
            continue
        entry = {
            "id": item.id,
            "requirement": item.requirement,
            "category": item.category,
            "verdict": result.verdict,
            "evidence": result.evidence,
            "rationale": result.rationale,
        }
        if result.verdict == "fail":
            blocking.append(entry)
        elif result.verdict == "partial":
            at_risk.append(entry)

    if blocking:
        decision = NOT_READY
    elif at_risk:
        decision = CONDITIONAL
    else:
        decision = READY

    return GateDecision(decision=decision, blocking_items=blocking, at_risk_items=at_risk)
