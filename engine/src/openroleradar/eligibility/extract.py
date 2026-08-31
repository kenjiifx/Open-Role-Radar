"""Work authorization and eligibility extraction."""

from __future__ import annotations

import re

from openroleradar.models.enums import EligibilityMatch
from openroleradar.models.job import Eligibility
from openroleradar.normalize.text import canonicalize_text, normalize_whitespace

_COUNTRY_CODE_PATTERN = re.compile(
    r"\b(?:citizens?|nationals?|residents?)\s+of\s+"
    r"(?P<countries>(?:[a-z][a-z\s,&/-]+(?:and\s+[a-z][a-z\s,&/-]+)*))",
    re.I,
)

_WORK_AUTH_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "us_citizen_required",
        re.compile(r"\b(?:u\.?s\.?\s+citizen(?:ship)?|united states citizen)\b", re.I),
    ),
    (
        "us_work_authorized",
        re.compile(
            r"\b(?:authorized to work in (?:the )?u\.?s\.?|eligible to work in (?:the )?u\.?s\.?)\b",
            re.I,
        ),
    ),
    ("canada_work_authorized", re.compile(r"\bauthorized to work in canada\b", re.I)),
    ("uk_work_authorized", re.compile(r"\bauthorized to work in (?:the )?uk\b", re.I)),
    ("eu_work_authorized", re.compile(r"\bauthorized to work in (?:the )?eu\b", re.I)),
    (
        "no_sponsorship",
        re.compile(r"\b(?:no sponsorship|unable to sponsor|will not sponsor)\b", re.I),
    ),
]

_CLEARANCE_PATTERN = re.compile(
    r"\b(?:active\s+)?(?:secret|top secret|ts/sci|security clearance)\b",
    re.I,
)

_EXPORT_CONTROL = re.compile(
    r"\bexport control(?:led)?\b|\bitar\b|\bear99\b",
    re.I,
)

_LANGUAGE_PATTERN = re.compile(
    r"\b(?:fluent|proficient|native)\s+(?:in\s+)?([a-z]{3,20}(?:\s+[a-z]{3,20})?)\b",
    re.I,
)

_COUNTRY_ALIASES: dict[str, str] = {
    "united states": "US",
    "usa": "US",
    "u.s.": "US",
    "us": "US",
    "canada": "CA",
    "united kingdom": "GB",
    "uk": "GB",
    "india": "IN",
    "germany": "DE",
    "france": "FR",
    "australia": "AU",
    "ireland": "IE",
}


def _country_codes_from_phrase(phrase: str) -> list[str]:
    codes: list[str] = []
    for part in re.split(r",|\band\b|/", phrase):
        token = canonicalize_text(part)
        if not token:
            continue
        code = _COUNTRY_ALIASES.get(token)
        if code and code not in codes:
            codes.append(code)
    return codes


def _extract_allowed_countries(text: str) -> list[str]:
    allowed: list[str] = []
    for match in re.finditer(
        r"\b(?:must be located in|candidates in|open to candidates in|eligible in)\s+"
        r"(?P<countries>[a-z][a-z\s,&/]+)",
        text,
        re.I,
    ):
        allowed.extend(_country_codes_from_phrase(match.group("countries")))
    return sorted(set(allowed))


def _extract_excluded_countries(text: str) -> list[str]:
    excluded: list[str] = []
    for match in re.finditer(
        r"\b(?:not available (?:in|to)|excluded (?:in|for)|not open to candidates in)\s+"
        r"(?P<countries>[a-z][a-z\s,&/]+)",
        text,
        re.I,
    ):
        excluded.extend(_country_codes_from_phrase(match.group("countries")))
    return sorted(set(excluded))


def _extract_citizenship(text: str) -> list[str]:
    citizenship: list[str] = []
    for match in _COUNTRY_CODE_PATTERN.finditer(text):
        citizenship.extend(_country_codes_from_phrase(match.group("countries")))
    if re.search(r"\bu\.?s\.?\s+citizen", text, re.I):
        citizenship.append("US")
    return sorted(set(citizenship))


def _extract_residency(text: str) -> list[str]:
    residency: list[str] = []
    for match in re.finditer(
        r"\b(?:must (?:be|reside|live) in|residents? of)\s+(?P<place>[a-z][a-z\s,&/]+)",
        text,
        re.I,
    ):
        residency.extend(_country_codes_from_phrase(match.group("place")))
    return sorted(set(residency))


def _detect_work_authorization(text: str) -> str | None:
    for label, pattern in _WORK_AUTH_PATTERNS:
        if pattern.search(text):
            return label
    return None


def compute_origin_match(
    eligibility: Eligibility,
    candidate_country: str | None,
) -> EligibilityMatch:
    """Determine whether a candidate origin country matches explicit eligibility rules."""
    if not candidate_country:
        return EligibilityMatch.UNKNOWN

    origin = candidate_country.upper()

    if origin in {c.upper() for c in eligibility.explicit_excluded_countries}:
        return EligibilityMatch.EXPLICITLY_INELIGIBLE

    if eligibility.citizenship_requirements:
        if origin in {c.upper() for c in eligibility.citizenship_requirements}:
            return EligibilityMatch.EXPLICIT_MATCH
        return EligibilityMatch.EXPLICITLY_INELIGIBLE

    if eligibility.explicit_allowed_countries:
        if origin in {c.upper() for c in eligibility.explicit_allowed_countries}:
            return EligibilityMatch.EXPLICIT_MATCH
        return EligibilityMatch.EXPLICITLY_INELIGIBLE

    if eligibility.work_authorization == "us_citizen_required" and origin != "US":
        return EligibilityMatch.EXPLICITLY_INELIGIBLE
    if eligibility.work_authorization == "no_sponsorship" and origin != "US":
        return EligibilityMatch.POTENTIAL_MATCH

    if eligibility.residency_requirements and origin in {
        c.upper() for c in eligibility.residency_requirements
    }:
        return EligibilityMatch.POTENTIAL_MATCH

    return EligibilityMatch.UNKNOWN


def extract_eligibility(
    description: str | None,
    *,
    candidate_country: str | None = None,
) -> Eligibility:
    """Extract eligibility constraints and optional origin match."""
    if not description:
        eligibility = Eligibility()
        eligibility.origin_match = compute_origin_match(eligibility, candidate_country)
        return eligibility

    normalized = canonicalize_text(description)

    languages = sorted(
        {
            match.group(1).strip().title()
            for match in _LANGUAGE_PATTERN.finditer(normalized)
            if match.group(1) not in {"English", "And"}
        }
    )

    eligibility = Eligibility(
        work_authorization=_detect_work_authorization(normalized),
        explicit_allowed_countries=_extract_allowed_countries(normalized),
        explicit_excluded_countries=_extract_excluded_countries(normalized),
        citizenship_requirements=_extract_citizenship(normalized),
        residency_requirements=_extract_residency(normalized),
        security_clearance=(
            normalize_whitespace(_CLEARANCE_PATTERN.search(description).group(0))  # type: ignore[union-attr]
            if _CLEARANCE_PATTERN.search(description)
            else None
        ),
        export_control_restrictions=bool(_EXPORT_CONTROL.search(normalized)),
        language_requirements=languages,
    )
    eligibility.origin_match = compute_origin_match(eligibility, candidate_country)
    return eligibility
