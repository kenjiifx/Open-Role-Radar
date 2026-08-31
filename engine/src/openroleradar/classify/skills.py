"""Technical skill extraction from skills configuration."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from openroleradar.config import load_skills_config
from openroleradar.normalize.text import canonicalize_text


@lru_cache(maxsize=1)
def _skill_patterns(root: Path | None = None) -> list[tuple[str, re.Pattern[str]]]:
    data = load_skills_config(root)
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for skill_name, meta in data.get("skills", {}).items():
        terms = [skill_name] + meta.get("aliases", [])
        escaped = [re.escape(canonicalize_text(term)) for term in terms if term]
        if not escaped:
            continue
        regex = re.compile(rf"\b(?:{'|'.join(escaped)})\b")
        patterns.append((skill_name, regex))
    patterns.sort(key=lambda item: (-len(item[0]), item[0]))
    return patterns


def extract_skills(text: str | None, *, root: Path | None = None) -> list[str]:
    """Extract canonical skill names found in free text."""
    if not text:
        return []

    normalized = canonicalize_text(text)
    found: list[str] = []
    seen: set[str] = set()

    for skill_name, pattern in _skill_patterns(root):
        if skill_name in seen:
            continue
        if pattern.search(normalized):
            found.append(skill_name)
            seen.add(skill_name)

    return sorted(found)
