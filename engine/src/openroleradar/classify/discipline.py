"""Discipline classification from taxonomy configuration."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from openroleradar.config import load_taxonomy
from openroleradar.models.job import DisciplineClassification
from openroleradar.normalize.text import canonicalize_text


@lru_cache(maxsize=1)
def _discipline_rules(root: Path | None = None) -> list[tuple[str, list[re.Pattern[str]]]]:
    taxonomy = load_taxonomy(root)
    rules: list[tuple[str, list[re.Pattern[str]]]] = []
    for entry in taxonomy.get("disciplines", []):
        discipline_id = entry["id"]
        terms = [entry.get("label", "")] + entry.get("aliases", [])
        patterns: list[re.Pattern[str]] = []
        for term in terms:
            term_norm = canonicalize_text(term)
            if not term_norm:
                continue
            patterns.append(re.compile(rf"\b{re.escape(term_norm)}\b"))
        if patterns:
            rules.append((discipline_id, patterns))
    return rules


def classify_discipline(
    title: str,
    department: str | None = None,
    description: str | None = None,
    *,
    root: Path | None = None,
) -> DisciplineClassification:
    """Classify job discipline from title, department, and description."""
    title_text = canonicalize_text(title)
    dept_text = canonicalize_text(department or "")
    desc_text = canonicalize_text(description or "")
    corpus = f"{title_text} {dept_text} {desc_text}".strip()

    scores: dict[str, float] = {}
    for discipline_id, patterns in _discipline_rules(root):
        hits = 0
        title_hits = 0
        for pattern in patterns:
            if pattern.search(corpus):
                hits += 1
            if pattern.search(title_text):
                title_hits += 1
        if hits == 0:
            continue
        score = 0.4 + (0.1 * min(hits, 3)) + (0.25 if title_hits else 0.0)
        if dept_text and any(p.search(dept_text) for p in patterns):
            score += 0.15
        scores[discipline_id] = min(score, 0.98)

    if not scores:
        return DisciplineClassification(primary="other", secondary=[], confidence=0.0)

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    primary, primary_score = ranked[0]
    secondary = [disc_id for disc_id, score in ranked[1:4] if score >= 0.5 and disc_id != primary]

    return DisciplineClassification(
        primary=primary,
        secondary=secondary,
        confidence=round(primary_score, 3),
    )
