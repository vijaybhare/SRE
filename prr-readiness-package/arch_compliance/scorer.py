"""Deterministic weighted aggregation of per-item verdicts into a compliance score."""
from __future__ import annotations

from dataclasses import dataclass

from .evaluator import EvalResult
from .rubric import RubricItem

VERDICT_CREDIT = {"pass": 1.0, "partial": 0.5, "fail": 0.0}


@dataclass
class CategoryScore:
    category: str
    percentage: float
    earned: float
    possible: float


@dataclass
class ComplianceReport:
    overall_percentage: float
    total_earned: float
    total_possible: float
    by_category: list[CategoryScore]
    items: list[dict]


def score(rubric: list[RubricItem], results: list[EvalResult]) -> ComplianceReport:
    results_by_id = {r.id: r for r in results}
    by_category_earned: dict[str, float] = {}
    by_category_possible: dict[str, float] = {}
    items = []

    total_earned = 0.0
    total_possible = 0.0

    for item in rubric:
        result = results_by_id.get(item.id)
        if result is None or result.verdict == "not_applicable":
            items.append(
                {
                    "id": item.id,
                    "requirement": item.requirement,
                    "category": item.category,
                    "verdict": result.verdict if result else "not_evaluated",
                    "evidence": result.evidence if result else "",
                    "rationale": result.rationale if result else "",
                    "weight": item.weight,
                }
            )
            continue

        credit = VERDICT_CREDIT.get(result.verdict, 0.0)
        earned = credit * item.weight
        total_earned += earned
        total_possible += item.weight
        by_category_earned[item.category] = by_category_earned.get(item.category, 0.0) + earned
        by_category_possible[item.category] = (
            by_category_possible.get(item.category, 0.0) + item.weight
        )
        items.append(
            {
                "id": item.id,
                "requirement": item.requirement,
                "category": item.category,
                "verdict": result.verdict,
                "evidence": result.evidence,
                "rationale": result.rationale,
                "weight": item.weight,
            }
        )

    by_category = [
        CategoryScore(
            category=cat,
            percentage=round(100 * by_category_earned[cat] / by_category_possible[cat], 1),
            earned=by_category_earned[cat],
            possible=by_category_possible[cat],
        )
        for cat in sorted(by_category_possible)
    ]

    overall_percentage = (
        round(100 * total_earned / total_possible, 1) if total_possible else 0.0
    )

    return ComplianceReport(
        overall_percentage=overall_percentage,
        total_earned=total_earned,
        total_possible=total_possible,
        by_category=by_category,
        items=items,
    )
