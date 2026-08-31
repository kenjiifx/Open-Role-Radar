"""Unit tests for deduplication and identity."""

from __future__ import annotations

from datetime import UTC, datetime

from openroleradar.dedupe.identity import (
    content_hash_from_fields,
    fingerprint_job,
    generate_job_id,
)
from openroleradar.dedupe.merge import dedupe_jobs, merge_job_group
from openroleradar.models.job import Job, Provenance


def test_generate_job_id_is_stable() -> None:
    first = generate_job_id("greenhouse", "tenant-a", "job-42")
    second = generate_job_id("greenhouse", "tenant-a", "job-42")
    third = generate_job_id("greenhouse", "tenant-b", "job-42")
    assert first == second
    assert first != third
    assert len(first) == 64


def test_fingerprint_normalizes_case_and_whitespace() -> None:
    a = fingerprint_job("Acme Corp", "Software Intern", ["San Francisco, CA"])
    b = fingerprint_job("acme   corp", "software   intern", ["san francisco, ca"])
    assert a == b


def _job(
    *,
    job_id: str,
    title: str = "Software Intern",
    skills: list[str] | None = None,
) -> Job:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    provenance = Provenance(
        adapter="greenhouse",
        source_id="src-1",
        source_job_id=job_id,
        fetched_at=now,
        content_hash=content_hash_from_fields(title=title, company="Acme"),
    )
    return Job(
        job_id=job_id,
        source_job_id=job_id,
        company_id="co-1",
        company_name="Acme",
        title=title,
        job_url=f"https://example.com/{job_id}",
        apply_url=f"https://example.com/{job_id}/apply",
        skills=skills or [],
        first_seen_at=now,
        last_seen_at=now,
        provenance=provenance,
    )


def test_merge_job_group_unions_skills() -> None:
    id_a = generate_job_id("gh", "t", "1")
    id_b = generate_job_id("gh", "t", "2")
    merged = merge_job_group(
        [
            _job(job_id=id_a, skills=["Python"]),
            _job(job_id=id_b, skills=["React", "Python"]),
        ]
    )
    assert merged.skills == ["Python", "React"]


def test_dedupe_jobs_collapses_identical_job_id() -> None:
    job_id = generate_job_id("gh", "tenant", "same")
    jobs = [
        _job(job_id=job_id, skills=["Python"]),
        _job(job_id=job_id, skills=["Go"]),
    ]
    result = dedupe_jobs(jobs)
    assert len(result) == 1
    assert set(result[0].skills) == {"Python", "Go"}
