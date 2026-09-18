"""Normalize architecture-standards documents (PDF/Word/Excel) into a canonical rubric."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .extractors import ExtractedDocument
from .llm import call_json

NORMALIZE_SYSTEM_PROMPT = """\
You turn an organization's architecture-standards documents into a checklist of \
discrete, independently-verifiable requirements ("rubric items").

Rules:
- Each rubric item must be a single, atomic, checkable requirement (split compound \
  sentences like "must use TLS and rotate keys every 90 days" into two items).
- Skip prose that is purely explanatory/background and has no checkable requirement.
- category: a short label such as "security", "resilience", "scalability", "cost", \
  "data", "observability", "governance" (invent others only if needed).
- mandatory: true if the source uses language like "must/shall/required"; false if \
  "should/recommended/may".
- weight: integer 1-5, how heavily this item should count toward the compliance \
  score (5 = critical/mandatory, 1 = minor/nice-to-have).

Respond with ONLY a JSON array of objects, no prose, no markdown fences:
[{"id": "SEC-1", "requirement": "...", "category": "security", "mandatory": true, "weight": 5}, ...]
IDs must be unique, short, and prefixed by category (e.g. SEC-1, RES-2, COST-1).
"""


@dataclass
class RubricItem:
    id: str
    requirement: str
    category: str
    mandatory: bool
    weight: int


def normalize_standards(documents: list[ExtractedDocument], model: str) -> list[RubricItem]:
    combined = "\n\n".join(
        f"=== SOURCE: {doc.source} ===\n{doc.full_text}" for doc in documents
    )
    if not combined.strip():
        raise ValueError("No extractable text found in the provided standards documents")

    raw = call_json(
        model=model,
        system=NORMALIZE_SYSTEM_PROMPT,
        user_text=combined,
        max_tokens=8000,
    )
    items = [RubricItem(**item) for item in raw]
    seen_ids = set()
    for item in items:
        if item.id in seen_ids:
            raise ValueError(f"Duplicate rubric id from normalization: {item.id}")
        seen_ids.add(item.id)
    return items


def save_rubric(items: list[RubricItem], path: str) -> None:
    with open(path, "w") as f:
        json.dump([asdict(i) for i in items], f, indent=2)


def load_rubric(path: str) -> list[RubricItem]:
    with open(path) as f:
        raw = json.load(f)
    return [RubricItem(**item) for item in raw]
