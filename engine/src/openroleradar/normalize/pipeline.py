"""RawJob to Job normalization orchestrator."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from openroleradar.classify.academic_term import classify_academic_term
from openroleradar.classify.career_level import classify_career_level
from openroleradar.classify.discipline import classify_discipline
from openroleradar.classify.skills import extract_skills
from openroleradar.config import load_project_config
from openroleradar.dedupe.identity import content_hash_from_raw, generate_job_id
from openroleradar.eligibility.extract import extract_eligibility
from openroleradar.mobility.extract import extract_mobility_benefits
from openroleradar.models.enums import EmploymentType, JobLifecycle
from openroleradar.models.job import Compensation, Job, Provenance, RawJob
from openroleradar.normalize.compensation import parse_compensation
from openroleradar.normalize.location import parse_locations, parse_remote_info
from openroleradar.normalize.text import (
    canonicalize_text,
    html_to_plaintext,
    normalize_whitespace,
    truncate_summary,
)

_EMPLOYMENT_MAP: dict[str, EmploymentType] = {
    "full_time": EmploymentType.FULL_TIME,
    "full-time": EmploymentType.FULL_TIME,
    "full time": EmploymentType.FULL_TIME,
    "part_time": EmploymentType.PART_TIME,
    "part-time": EmploymentType.PART_TIME,
    "part time": EmploymentType.PART_TIME,
    "contract": EmploymentType.CONTRACT,
    "temporary": EmploymentType.TEMPORARY,
    "internship": EmploymentType.INTERNSHIP,
    "intern": EmploymentType.INTERNSHIP,
}


def _parse_employment_type(raw: str | None) -> EmploymentType:
    if not raw:
        return EmploymentType.UNKNOWN
    key = canonicalize_text(raw)
    return _EMPLOYMENT_MAP.get(key, EmploymentType.UNKNOWN)


def _extract_compensation(description: str | None, metadata: dict[str, Any]) -> Compensation | None:
    for key in ("compensation", "salary", "pay_range"):
        value = metadata.get(key)
        if isinstance(value, str):
            parsed = parse_compensation(value)
            if parsed:
                return parsed
    if not description:
        return None
    for match in re.finditer(
        r"(?:salary|compensation|pay)\s*[:\-]?\s*([^\n.;]{5,80})",
        description,
        re.I,
    ):
        parsed = parse_compensation(match.group(1))
        if parsed and parsed.min_amount is not None:
            return parsed
    return None


def normalize_raw_job(
    raw: RawJob,
    *,
    company_id: str,
    company_name: str,
    adapter: str,
    adapter_tenant: str,
    source_id: str,
    fetched_at: datetime,
    candidate_country: str | None = None,
    source_health: str = "healthy",
    root: Path | None = None,
) -> Job:
    """Transform a RawJob into a normalized Job with classification and enrichment."""
    project = load_project_config(root)
    parser_version = project.versions.parser
    classification_version = project.versions.classification

    description = html_to_plaintext(raw.description_text)
    summary_raw = html_to_plaintext(raw.summary)
    # Prefer the richest cleaned corpus; never keep adapter-pretruncated dirty HTML.
    summary_source = description if len(description) >= len(summary_raw) else summary_raw
    if not summary_source:
        summary_source = description or summary_raw
    summary = truncate_summary(summary_source)

    career_level, career_confidence = classify_career_level(raw.title, description, root=root)
    academic_term = classify_academic_term(raw.title, description, root=root)
    disciplines = classify_discipline(
        raw.title,
        raw.department,
        description,
        root=root,
    )
    skill_corpus = f"{raw.title} {raw.department or ''} {description}"
    skills = extract_skills(skill_corpus, root=root)

    locations = parse_locations(raw.locations_raw)
    remote_info = parse_remote_info(raw.locations_raw, description)

    compensation = _extract_compensation(description, raw.metadata)
    eligibility = extract_eligibility(description, candidate_country=candidate_country)
    mobility = extract_mobility_benefits(description)

    content_hash = content_hash_from_raw(raw, company_name)
    job_id = generate_job_id(adapter, adapter_tenant, raw.source_job_id)

    provenance = Provenance(
        adapter=adapter,
        source_id=source_id,
        source_job_id=raw.source_job_id,
        fetched_at=fetched_at,
        source_posted_at=raw.posted_at,
        first_seen_at=fetched_at,
        parser_version=parser_version,
        classification_version=classification_version,
        content_hash=content_hash,
        source_health_at_fetch=source_health,
        first_party_verified=bool(raw.metadata.get("first_party_verified", False)),
    )

    return Job(
        job_id=job_id,
        source_job_id=raw.source_job_id,
        requisition_id=raw.requisition_id,
        company_id=company_id,
        company_name=company_name,
        title=normalize_whitespace(raw.title),
        job_url=raw.job_url,
        apply_url=raw.apply_url,
        careers_url=raw.metadata.get("careers_url"),
        source_url=raw.metadata.get("source_url"),
        summary=summary,
        career_level=career_level,
        career_level_confidence=career_confidence,
        academic_term=academic_term,
        employment_type=_parse_employment_type(raw.employment_type),
        disciplines=disciplines,
        skills=skills,
        locations=locations,
        workplace_type=remote_info.workplace_type,
        remote_scope=remote_info.remote_scope,
        remote_allowed_countries=remote_info.remote_allowed_countries,
        remote_allowed_regions=remote_info.remote_allowed_regions,
        source_posted_at=raw.posted_at,
        first_seen_at=fetched_at,
        last_seen_at=fetched_at,
        application_deadline=raw.application_deadline,
        compensation=compensation,
        eligibility=eligibility,
        mobility=mobility,
        provenance=provenance,
        lifecycle=JobLifecycle.OPEN,
        extra=dict(raw.metadata),
    )
