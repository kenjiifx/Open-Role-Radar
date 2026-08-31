"""Unit tests for lifecycle state machine."""

from __future__ import annotations

from datetime import UTC, datetime

from openroleradar.dedupe.identity import generate_job_id
from openroleradar.lifecycle.manager import LifecycleConfig, LifecycleManager
from openroleradar.models.enums import JobLifecycle
from openroleradar.models.job import Job, Provenance


def _sample_job(lifecycle: JobLifecycle = JobLifecycle.OPEN) -> Job:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    provenance = Provenance(
        adapter="greenhouse",
        source_id="src-1",
        source_job_id="123",
        fetched_at=now,
        content_hash="abc",
    )
    return Job(
        job_id=generate_job_id("greenhouse", "tenant-a", "123"),
        source_job_id="123",
        company_id="co-1",
        company_name="Acme",
        title="Intern",
        job_url="https://example.com/jobs/123",
        apply_url="https://example.com/jobs/123/apply",
        first_seen_at=now,
        last_seen_at=now,
        provenance=provenance,
        lifecycle=lifecycle,
    )


def test_missing_job_becomes_suspected_then_closed() -> None:
    manager = LifecycleManager(
        LifecycleConfig(
            misses_before_suspected_closed=2,
            misses_before_closed=4,
            unhealthy_source_never_closes=True,
        )
    )
    now = datetime(2026, 2, 1, tzinfo=UTC)
    job = _sample_job()

    job = manager.on_job_missing(job, miss_count=2, source_health="healthy", now=now)
    assert job.lifecycle == JobLifecycle.SUSPECTED_CLOSED

    job = manager.on_job_missing(job, miss_count=4, source_health="healthy", now=now)
    assert job.lifecycle == JobLifecycle.CLOSED
    assert job.closed_at == now


def test_unhealthy_source_never_closes() -> None:
    manager = LifecycleManager(
        LifecycleConfig(
            misses_before_suspected_closed=1,
            misses_before_closed=2,
            unhealthy_source_never_closes=True,
        )
    )
    now = datetime(2026, 2, 1, tzinfo=UTC)
    job = _sample_job()
    updated = manager.on_job_missing(job, miss_count=10, source_health="failing", now=now)
    assert updated.lifecycle == JobLifecycle.OPEN


def test_reopen_on_seen_after_closed() -> None:
    manager = LifecycleManager()
    now = datetime(2026, 3, 1, tzinfo=UTC)
    job = _sample_job(JobLifecycle.CLOSED)
    job.closed_at = datetime(2026, 2, 1, tzinfo=UTC)

    updated = manager.on_job_seen(job, now)
    assert updated.lifecycle == JobLifecycle.OPEN
    assert updated.reopened_at == now
    assert updated.closed_at is None


def test_authoritative_close_on_404() -> None:
    manager = LifecycleManager()
    now = datetime(2026, 3, 1, tzinfo=UTC)
    job = _sample_job()
    updated = manager.on_authoritative_close(job, status_code=404, now=now)
    assert updated.lifecycle == JobLifecycle.CLOSED
    assert updated.closed_at == now
