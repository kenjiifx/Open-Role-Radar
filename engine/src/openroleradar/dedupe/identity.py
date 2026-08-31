"""Job identity, fingerprinting, and content hashing."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from openroleradar.models.job import Job, RawJob
from openroleradar.normalize.text import canonicalize_text


def generate_job_id(adapter: str, tenant: str, source_job_id: str) -> str:
    """Deterministic job ID: sha256(adapter + tenant + source_job_id)."""
    payload = f"{adapter}:{tenant}:{source_job_id}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fingerprint_job(
    company_name: str,
    title: str,
    locations: list[str] | None = None,
) -> str:
    """Secondary fingerprint for cross-source deduplication."""
    loc_key = "|".join(sorted(canonicalize_text(loc) for loc in (locations or []) if loc))
    payload = f"{canonicalize_text(company_name)}|{canonicalize_text(title)}|{loc_key}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _stable_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash_from_fields(**fields: Any) -> str:
    """Hash canonical job content fields for change detection."""
    normalized = {
        key: canonicalize_text(value) if isinstance(value, str) else value
        for key, value in fields.items()
    }
    return hashlib.sha256(_stable_json(normalized).encode("utf-8")).hexdigest()


def content_hash_from_raw(raw: RawJob, company_name: str) -> str:
    """Compute content hash from a raw job payload."""
    return content_hash_from_fields(
        company_name=company_name,
        source_job_id=raw.source_job_id,
        title=raw.title,
        job_url=raw.job_url,
        apply_url=raw.apply_url,
        locations="|".join(raw.locations_raw),
        description=raw.description_text or "",
        summary=raw.summary or "",
        employment_type=raw.employment_type or "",
        department=raw.department or "",
    )


def content_hash_from_job(job: Job) -> str:
    """Compute content hash from a normalized job."""
    return content_hash_from_fields(
        company_name=job.company_name,
        source_job_id=job.source_job_id,
        title=job.title,
        job_url=job.job_url,
        apply_url=job.apply_url,
        locations="|".join(loc.raw or "" for loc in job.locations),
        summary=job.summary or "",
        employment_type=job.employment_type.value,
        career_level=job.career_level.value,
        primary_discipline=job.disciplines.primary,
        skills=",".join(job.skills),
    )
