"""Evaluate an architecture document against a rubric, one batch of items at a time."""
from __future__ import annotations

from dataclasses import dataclass

from .extractors import ExtractedDocument
from .llm import call_json
from .rubric import RubricItem

EVAL_SYSTEM_PROMPT = """\
You are an architecture-compliance reviewer. You are given (a) a solution \
architecture document (text and/or page images) and (b) a list of requirements \
to check against it.

For EACH requirement, decide:
- "pass": the architecture clearly satisfies the requirement.
- "fail": the architecture clearly violates or omits the requirement.
- "partial": partially addressed, ambiguous, or only for part of the system.
- "not_applicable": the requirement does not apply to this architecture/domain.

For every verdict, include a short quote or specific reference from the document \
as evidence (for "fail"/"not_applicable", explain why no evidence exists instead).
Do not guess generously — if the document is silent on a requirement, that is a "fail" \
for mandatory items, not a "pass".

Respond with ONLY a JSON array, no prose, no markdown fences:
[{"id": "SEC-1", "verdict": "pass", "evidence": "...", "rationale": "..."}, ...]
"""

BATCH_SIZE = 8
MAX_TEXT_CHARS = 60_000
MAX_IMAGE_PAGES = 20


@dataclass
class EvalResult:
    id: str
    verdict: str
    evidence: str
    rationale: str


def _batches(items: list[RubricItem], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def evaluate(
    architecture: ExtractedDocument, rubric: list[RubricItem], model: str
) -> list[EvalResult]:
    text = architecture.full_text[:MAX_TEXT_CHARS]
    image_b64_list = [
        p.image_b64 for p in architecture.pages[:MAX_IMAGE_PAGES] if p.image_b64
    ]

    results: list[EvalResult] = []
    for batch in _batches(rubric, BATCH_SIZE):
        requirements_text = "\n".join(
            f"- id={item.id} (mandatory={item.mandatory}): {item.requirement}"
            for item in batch
        )
        user_text = (
            f"ARCHITECTURE DOCUMENT ({architecture.source}):\n{text}\n\n"
            f"REQUIREMENTS TO CHECK:\n{requirements_text}"
        )
        raw = call_json(
            model=model,
            system=EVAL_SYSTEM_PROMPT,
            user_text=user_text,
            image_b64_list=image_b64_list,
            max_tokens=4000,
        )
        raw_by_id = {r["id"]: r for r in raw}
        for item in batch:
            r = raw_by_id.get(item.id)
            if r is None:
                results.append(
                    EvalResult(
                        id=item.id,
                        verdict="fail",
                        evidence="",
                        rationale="Model did not return a verdict for this item.",
                    )
                )
            else:
                results.append(
                    EvalResult(
                        id=item.id,
                        verdict=r["verdict"],
                        evidence=r.get("evidence", ""),
                        rationale=r.get("rationale", ""),
                    )
                )
    return results
