"""Career level classification from taxonomy configuration."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from openroleradar.config import load_taxonomy
from openroleradar.models.enums import CareerLevel
from openroleradar.normalize.text import canonicalize_text


@lru_cache(maxsize=1)
def _career_level_rules(
    root: Path | None = None,
) -> tuple[list[tuple[CareerLevel, list[re.Pattern[str]]]], list[str]]:
    taxonomy = load_taxonomy(root)
    rules: list[tuple[CareerLevel, list[re.Pattern[str]]]] = []
    for entry in taxonomy.get("career_levels", []):
        level_id = entry["id"]
        try:
            level = CareerLevel(level_id)
        except ValueError:
            continue
        patterns = [
            re.compile(rf"\b{re.escape(canonicalize_text(p))}\b")
            for p in entry.get("patterns", [])
            if p
        ]
        if patterns:
            rules.append((level, patterns))
    exclusions = [canonicalize_text(x) for x in taxonomy.get("senior_exclusions", [])]
    return rules, exclusions


def _has_senior_exclusion(text: str, exclusions: list[str]) -> bool:
    return any(phrase and phrase in text for phrase in exclusions)


def classify_career_level(
    title: str,
    description: str | None = None,
    *,
    root: Path | None = None,
) -> tuple[CareerLevel, float]:
    """Classify early-career level from title and description using taxonomy patterns."""
    corpus = canonicalize_text(f"{title} {description or ''}")
    rules, exclusions = _career_level_rules(root)

    if _has_senior_exclusion(corpus, exclusions):
        return CareerLevel.UNKNOWN, 0.0

    best_level = CareerLevel.UNKNOWN
    best_score = 0.0

    title_text = canonicalize_text(title)

    for level, patterns in rules:
        hits = 0
        title_hits = 0
        for pattern in patterns:
            if pattern.search(corpus):
                hits += 1
            if pattern.search(title_text):
                title_hits += 1
        if hits == 0:
            continue
        score = 0.55 + (0.15 * min(hits, 2)) + (0.2 if title_hits else 0.0)
        score = min(score, 0.95)
        if score > best_score:
            best_score = score
            best_level = level

    return best_level, best_score
