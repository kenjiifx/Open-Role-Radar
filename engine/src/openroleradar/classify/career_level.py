"""Career level classification from taxonomy configuration."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from openroleradar.config import load_taxonomy
from openroleradar.models.enums import CareerLevel
from openroleradar.normalize.text import canonicalize_text

# Title-only mid/senior signals that should never publish as early-career.
_TITLE_SENIOR_RE = re.compile(
    r"\b("
    r"senior|sr\.?|staff|principal|lead|manager|director|vp|vice\s+president|"
    r"head\s+of|chief|architect|iii|iv|mid[- ]level|experienced"
    r")\b"
)


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
    """Classify early-career level; title hits are required for high confidence.

    Description-only keyword matches stay below the public export threshold so
    mid/senior postings that mention intern programs in benefits text do not leak.
    """
    title_text = canonicalize_text(title)
    corpus = canonicalize_text(f"{title} {description or ''}")
    rules, exclusions = _career_level_rules(root)

    if _has_senior_exclusion(title_text, exclusions) or _TITLE_SENIOR_RE.search(title_text):
        return CareerLevel.UNKNOWN, 0.0

    best_level = CareerLevel.UNKNOWN
    best_score = 0.0

    for level, patterns in rules:
        title_hits = 0
        body_hits = 0
        for pattern in patterns:
            if pattern.search(title_text):
                title_hits += 1
            elif pattern.search(corpus):
                body_hits += 1
        if title_hits == 0 and body_hits == 0:
            continue

        if title_hits > 0:
            # Title match is trustworthy enough for public export.
            score = 0.72 + (0.1 * min(title_hits, 2)) + (0.05 * min(body_hits, 2))
            score = min(score, 0.95)
        else:
            # Description-only: keep below public_filter default (0.65).
            score = min(0.45, 0.28 + (0.08 * min(body_hits, 2)))

        if score > best_score:
            best_score = score
            best_level = level

    return best_level, best_score
