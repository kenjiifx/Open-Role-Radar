"""Academic term classification from taxonomy configuration."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from openroleradar.config import load_taxonomy
from openroleradar.models.enums import AcademicTerm
from openroleradar.normalize.text import canonicalize_text


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


def classify_academic_term(
    title: str,
    description: str | None = None,
    *,
    root: Path | None = None,
) -> AcademicTerm:
    """Infer academic term from title/description; prefer title matches."""
    title_text = canonicalize_text(title)
    corpus = canonicalize_text(f"{title} {description or ''}")
    for term, patterns in _academic_term_rules(root):
        if any(pattern.search(title_text) for pattern in patterns):
            return term
    for term, patterns in _academic_term_rules(root):
        if any(pattern.search(corpus) for pattern in patterns):
            return term
    return AcademicTerm.UNKNOWN
