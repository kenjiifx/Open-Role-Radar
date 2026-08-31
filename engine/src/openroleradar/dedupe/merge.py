"""Multi-stage job deduplication and merge logic."""

from __future__ import annotations

from dataclasses import dataclass, field

from openroleradar.dedupe.identity import (
    content_hash_from_job,
    fingerprint_job,
    generate_job_id,
)
from openroleradar.models.job import Job


@dataclass
class DedupeGroup:
    canonical_job_id: str
    members: list[Job] = field(default_factory=list)
    stage: str = "job_id"


def _primary_location(job: Job) -> str:
    if not job.locations:
        return ""
    loc = job.locations[0]
    return loc.raw or loc.city or loc.country_code or ""


def group_by_job_id(jobs: list[Job]) -> dict[str, list[Job]]:
    groups: dict[str, list[Job]] = {}
    for job in jobs:
        groups.setdefault(job.job_id, []).append(job)
    return groups


def group_by_fingerprint(jobs: list[Job]) -> dict[str, list[Job]]:
    groups: dict[str, list[Job]] = {}
    for job in jobs:
        fp = fingerprint_job(
            job.company_name,
            job.title,
            [loc.raw or "" for loc in job.locations],
        )
        groups.setdefault(fp, []).append(job)
    return groups


def group_by_content_hash(jobs: list[Job]) -> dict[str, list[Job]]:
    groups: dict[str, list[Job]] = {}
    for job in jobs:
        digest = content_hash_from_job(job)
        groups.setdefault(digest, []).append(job)
    return groups


def _pick_canonical(members: list[Job]) -> Job:
    """Prefer the job with the earliest first_seen_at, then lexicographic job_id."""
    return sorted(members, key=lambda j: (j.first_seen_at, j.job_id))[0]


def merge_job_group(members: list[Job]) -> Job:
    """Merge duplicate jobs into a single canonical record."""
    if not members:
        raise ValueError("Cannot merge empty job group")
    if len(members) == 1:
        return members[0]

    canonical = _pick_canonical(members)
    merged = canonical.model_copy(deep=True)

    all_skills = sorted({skill for job in members for skill in job.skills})
    merged.skills = all_skills

    seen_urls = {merged.job_url}
    for job in members:
        if job.apply_url and job.apply_url not in seen_urls:
            seen_urls.add(job.apply_url)

    merged.last_seen_at = max(job.last_seen_at for job in members)
    earliest = min(job.first_seen_at for job in members)
    merged.first_seen_at = earliest
    return merged


def dedupe_jobs(jobs: list[Job]) -> list[Job]:
    """Run multi-stage deduplication: job_id, fingerprint, then content hash."""
    if not jobs:
        return []

    by_id = group_by_job_id(jobs)
    stage_one = [merge_job_group(group) for group in by_id.values()]

    by_fingerprint = group_by_fingerprint(stage_one)
    stage_two = [merge_job_group(group) for group in by_fingerprint.values()]

    by_hash = group_by_content_hash(stage_two)
    return [merge_job_group(group) for group in by_hash.values()]


def find_duplicates(jobs: list[Job]) -> list[DedupeGroup]:
    """Return duplicate groups discovered across dedupe stages."""
    groups: list[DedupeGroup] = []

    for job_id, members in group_by_job_id(jobs).items():
        if len(members) > 1:
            groups.append(DedupeGroup(canonical_job_id=job_id, members=members, stage="job_id"))

    fingerprint_seen: dict[str, str] = {}
    for job in jobs:
        fp = fingerprint_job(job.company_name, job.title, [_primary_location(job)])
        if fp in fingerprint_seen and fingerprint_seen[fp] != job.job_id:
            groups.append(
                DedupeGroup(
                    canonical_job_id=fingerprint_seen[fp],
                    members=[
                        j
                        for j in jobs
                        if fingerprint_job(j.company_name, j.title, [_primary_location(j)]) == fp
                    ],
                    stage="fingerprint",
                )
            )
        else:
            fingerprint_seen[fp] = job.job_id

    return groups


__all__ = [
    "DedupeGroup",
    "dedupe_jobs",
    "find_duplicates",
    "generate_job_id",
    "group_by_content_hash",
    "group_by_fingerprint",
    "group_by_job_id",
    "merge_job_group",
]
