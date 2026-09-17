"""Academic term classification from taxonomy configuration."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from openroleradar.config import load_taxonomy
from openroleradar.models.enums import AcademicTerm
from openroleradar.normalize.text import canonicalize_text

# Prefer precise season phrases over bare words that collide with tech jargon.
_PRECISE_TERM_PATTERNS: list[tuple[AcademicTerm, re.Pattern[str]]] = [
    (AcademicTerm.SUMMER, re.compile(r"\bsummer(?:\s+20\d{2}|\s+intern|\s+internship|\s+co-?op)?\b", re.I)),
    (AcademicTerm.FALL, re.compile(r"\b(?:fall|autumn)(?:\s+20\d{2}|\s+intern|\s+internship|\s+co-?op)?\b", re.I)),
    (AcademicTerm.WINTER, re.compile(r"\bwinter(?:\s+20\d{2}|\s+intern|\s+internship|\s+co-?op)?\b", re.I)),
    (
        AcademicTerm.SPRING,
        re.compile(r"\bspring(?!\s+boot)(?:\s+20\d{2}|\s+intern|\s+internship|\s+co-?op)?\b", re.I),
    ),
    (
        AcademicTerm.ROLLING,
        re.compile(
            r"\b(?:rolling\s+(?:admissions?|basis|applications?|hire|hiring)|applications?\s+rolling)\b",
            re.I,
        ),
    ),
    (AcademicTerm.OFF_CYCLE, re.compile(r"\boff[-\s]?cycle\b", re.I)),
]


@lru_cache(maxsize=1)
def _academic_term_rules(
    root: Path | None = None,
) -> list[tuple[AcademicTerm, list[re.Pattern[str]]]]:
    taxonomy = load_taxonomy(root)
    rules: list[tuple[AcademicTerm, list[re.Pattern[str]]]] = []
    for entry in taxonomy.get("academic_terms", []):
        term_id = entry.get("id")
        if not term_id:
            continue
        try:
            term = AcademicTerm(term_id)
        except ValueError:
            continue
        patterns = [
            re.compile(rf"\b{re.escape(canonicalize_text(p))}\b")
            for p in entry.get("patterns", [])
            if p
        ]
        if patterns:
            rules.append((term, patterns))
    return rules


def _first_precise_term(text: str) -> AcademicTerm | None:
    """Return the earliest precise season match so multi-term strings keep order."""
    best: tuple[int, AcademicTerm] | None = None
    for term, pattern in _PRECISE_TERM_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        if best is None or match.start() < best[0]:
            best = (match.start(), term)
    return best[1] if best else None


def classify_academic_term(
    title: str,
    description: str | None = None,
    *,
    summary: str | None = None,
    metadata: dict[str, Any] | None = None,
    root: Path | None = None,
) -> AcademicTerm:
    """Infer academic term; prefer structured Simplify terms, then title, then summary."""
    structured_bits: list[str] = []
    if metadata:
        terms = metadata.get("simplify_terms")
        if isinstance(terms, list):
            structured_bits.extend(str(term) for term in terms if term)
        elif isinstance(terms, str) and terms.strip():
            structured_bits.append(terms)

    for blob in structured_bits:
        hit = _first_precise_term(blob) or _first_precise_term(canonicalize_text(blob))
        if hit is not None:
            return hit

    title_text = title or ""
    title_hit = _first_precise_term(title_text)
    if title_hit is not None:
        return title_hit

    summary_text = summary or ""
    summary_hit = _first_precise_term(summary_text)
    if summary_hit is not None:
        return summary_hit

    # Last resort: taxonomy patterns on title only (never full JD — too noisy).
    title_canon = canonicalize_text(title_text)
    for term, patterns in _academic_term_rules(root):
        if term in {AcademicTerm.ROLLING, AcademicTerm.SPRING}:
            # Bare spring/rolling collide with "Spring Boot" / "rolling out".
            continue
        if any(pattern.search(title_canon) for pattern in patterns):
            return term

    # Explicitly ignore description for season detection unless nothing else matched
    # and the description has a precise phrase (not bare taxonomy words).
    if description:
        desc_hit = _first_precise_term(description)
        if desc_hit is not None:
            return desc_hit

    return AcademicTerm.UNKNOWN
