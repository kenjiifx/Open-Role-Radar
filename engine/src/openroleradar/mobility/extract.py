"""Evidence-based mobility benefit extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass

from openroleradar.models.enums import EvidenceStatus
from openroleradar.models.job import EvidenceClaim, MobilityBenefits
from openroleradar.normalize.text import canonicalize_text, normalize_whitespace


@dataclass(frozen=True)
class PhraseRule:
    field: str
    positive: tuple[str, ...]
    negative: tuple[str, ...]
    confidence: float = 0.85


def _compile_phrases(phrases: tuple[str, ...]) -> list[re.Pattern[str]]:
    return [re.compile(re.escape(canonicalize_text(p))) for p in phrases if p]


def _find_excerpt(text: str, pattern: re.Pattern[str], *, window: int = 120) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    start = max(0, match.start() - 40)
    end = min(len(text), match.end() + window)
    return normalize_whitespace(text[start:end])[:500]


def _evaluate_rules(
    text: str,
    rules: list[PhraseRule],
) -> dict[str, EvidenceClaim]:
    normalized = canonicalize_text(text)
    claims: dict[str, EvidenceClaim] = {}

    for rule in rules:
        pos_patterns = _compile_phrases(rule.positive)
        neg_patterns = _compile_phrases(rule.negative)

        for pattern in neg_patterns:
            if pattern.search(normalized):
                claims[rule.field] = EvidenceClaim(
                    status=EvidenceStatus.NOT_AVAILABLE,
                    confidence=rule.confidence,
                    extraction_rule=f"{rule.field}:negative",
                    evidence_excerpt=_find_excerpt(normalized, pattern),
                )
                break

        if rule.field in claims:
            continue

        for pattern in pos_patterns:
            if pattern.search(normalized):
                claims[rule.field] = EvidenceClaim(
                    status=EvidenceStatus.CONFIRMED,
                    confidence=rule.confidence,
                    extraction_rule=f"{rule.field}:positive",
                    evidence_excerpt=_find_excerpt(normalized, pattern),
                )
                break

    return claims


_PHRASE_RULES: list[PhraseRule] = [
    PhraseRule(
        field="visa_sponsorship",
        positive=(
            "visa sponsorship",
            "will sponsor visa",
            "h-1b sponsorship",
            "h1b sponsorship",
            "work visa sponsorship",
            "sponsor work authorization",
        ),
        negative=(
            "no visa sponsorship",
            "unable to sponsor",
            "cannot sponsor",
            "will not sponsor",
            "not eligible for sponsorship",
            "must have unrestricted work authorization",
            "must be authorized to work",
        ),
    ),
    PhraseRule(
        field="immigration_assistance",
        positive=(
            "immigration assistance",
            "immigration support",
            "relocation and immigration",
        ),
        negative=("no immigration assistance",),
    ),
    PhraseRule(
        field="international_candidates",
        positive=(
            "international candidates welcome",
            "open to international applicants",
            "global candidates",
        ),
        negative=(
            "us citizens only",
            "must be legally authorized",
            "no international candidates",
        ),
    ),
    PhraseRule(
        field="relocation_assistance",
        positive=(
            "relocation assistance",
            "relocation package",
            "relocation support",
            "assisted relocation",
        ),
        negative=(
            "no relocation assistance",
            "relocation not provided",
            "relocation unavailable",
        ),
    ),
    PhraseRule(
        field="relocation_stipend",
        positive=("relocation stipend", "relocation bonus"),
        negative=("no relocation stipend",),
    ),
    PhraseRule(
        field="moving_expenses",
        positive=("moving expenses", "moving allowance", "cover moving costs"),
        negative=("no moving expenses", "moving expenses not covered"),
    ),
    PhraseRule(
        field="airfare",
        positive=("airfare provided", "flight reimbursement", "airfare reimbursement"),
        negative=("no airfare", "airfare not provided"),
    ),
    PhraseRule(
        field="travel_reimbursement",
        positive=("travel reimbursement", "travel expenses reimbursed"),
        negative=("no travel reimbursement",),
    ),
    PhraseRule(
        field="housing_provided",
        positive=("housing provided", "company housing", "accommodation provided"),
        negative=("housing not provided", "no housing provided"),
    ),
    PhraseRule(
        field="housing_stipend",
        positive=("housing stipend", "housing allowance"),
        negative=("no housing stipend",),
    ),
    PhraseRule(
        field="temporary_housing",
        positive=("temporary housing", "short-term housing", "corporate apartment"),
        negative=("no temporary housing",),
    ),
    PhraseRule(
        field="fully_funded_relocation",
        positive=("fully funded relocation", "full relocation package"),
        negative=("no fully funded relocation",),
    ),
]


def extract_mobility_benefits(description: str | None) -> MobilityBenefits:
    """Extract mobility benefits with evidence-backed status claims only."""
    benefits = MobilityBenefits()
    if not description:
        return benefits

    extracted = _evaluate_rules(description, _PHRASE_RULES)
    for field, claim in extracted.items():
        setattr(benefits, field, claim)

    return benefits
