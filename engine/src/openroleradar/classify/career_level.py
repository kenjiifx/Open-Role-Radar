"""Career level classification from taxonomy configuration."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from openroleradar.config import load_taxonomy
from openroleradar.models.enums import CareerLevel
from openroleradar.normalize.text import canonicalize_text

# Title-only mid/senior signals that should never publish as early-career.
# "lead" is handled separately so "Lead Intern" remains early-career.
_TITLE_SENIOR_RE = re.compile(
    r"\b("
    r"senior|sr\.?|staff|principal|manager|director|vp|vice\s+president|"
    r"head\s+of|chief|architect|iii|iv|mid[- ]level|experienced"
    r")\b"
)
_TITLE_LEAD_RE = re.compile(r"\blead\b")
_EARLY_OVERRIDE_RE = re.compile(
    r"\b(intern|internship|co-?op|new\s+grad|student|apprentice|trainee|campus)\b"
)

_ATS_INTERNSHIP = re.compile(r"\b(intern|internship|co-?op|trainee)\b", re.I)
_ATS_ENTRY = re.compile(
    r"\b(entry[- ]level|junior|early[- ]career|new\s+grad|graduate|student|apprentice)\b",
    re.I,
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


def _is_senior_title(title_text: str, exclusions: list[str]) -> bool:
    if _has_senior_exclusion(title_text, exclusions) or _TITLE_SENIOR_RE.search(title_text):
        return True
    if _TITLE_LEAD_RE.search(title_text) and not _EARLY_OVERRIDE_RE.search(title_text):
        return True
    return False


def _from_ats_metadata(
    *,
    employment_type: str | None,
    metadata: dict[str, Any] | None,
) -> tuple[CareerLevel, float] | None:
    """Map ATS structured fields to early-career levels when titles are generic."""
    blobs: list[str] = []
    if employment_type:
        blobs.append(str(employment_type))
    if metadata:
        for key in (
            "experience_level",
            "experienceLevel",
            "employmentType",
            "workplaceType",
            "ats_employment_type",
        ):
            value = metadata.get(key)
            if isinstance(value, dict):
                label = value.get("label") or value.get("id") or value.get("name")
                if label:
                    blobs.append(str(label))
            elif value:
                blobs.append(str(value))
    if not blobs:
        return None
    joined = " ".join(blobs)
    if _ATS_INTERNSHIP.search(joined):
        return CareerLevel.INTERNSHIP, 0.78
    if _ATS_ENTRY.search(joined):
        return CareerLevel.ENTRY_LEVEL, 0.72
    return None


def classify_career_level(
    title: str,
    description: str | None = None,
    *,
    employment_type: str | None = None,
    metadata: dict[str, Any] | None = None,
    root: Path | None = None,
) -> tuple[CareerLevel, float]:
    """Classify early-career level; title hits are required for high confidence.

    Description-only keyword matches stay below the public export threshold so
    mid/senior postings that mention intern programs in benefits text do not leak.
    ATS employment/experience metadata can promote generic titles when present.
    """
    title_text = canonicalize_text(title)
    corpus = canonicalize_text(f"{title} {description or ''}")
    rules, exclusions = _career_level_rules(root)

    if _is_senior_title(title_text, exclusions):
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
            score = 0.72 + (0.1 * min(title_hits, 2)) + (0.05 * min(body_hits, 2))
            score = min(score, 0.95)
        else:
            score = min(0.45, 0.28 + (0.08 * min(body_hits, 2)))

        if score > best_score:
            best_score = score
            best_level = level

    if best_score < 0.55:
        ats_hit = _from_ats_metadata(employment_type=employment_type, metadata=metadata)
        if ats_hit is not None:
            level, score = ats_hit
            if score > best_score:
                return level, score

    return best_level, best_score
