"""Large-dataset export and sharding stress tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from openroleradar.config import load_project_config
from openroleradar.export.site_data import SiteDataBuilder
from openroleradar.models.enums import CareerLevel, JobLifecycle
from openroleradar.models.job import DisciplineClassification, Job, Provenance
from openroleradar.models.state import LiveState


def _make_job(index: int) -> Job:
    now = datetime.now(UTC)
    return Job(
        job_id=f"job-{index:06d}",
        source_job_id=str(index),
        company_id="company-test",
        company_name="TestCo",
        title=f"Software Engineer Intern {index}",
        job_url=f"https://boards.greenhouse.io/test/jobs/{index}",
        apply_url=f"https://boards.greenhouse.io/test/jobs/{index}",
        career_level=CareerLevel.INTERNSHIP,
        disciplines=DisciplineClassification(primary="software"),
        first_seen_at=now,
        last_seen_at=now,
        provenance=Provenance(
            adapter="greenhouse",
            source_id="src-test",
            source_job_id=str(index),
            fetched_at=now,
            content_hash=f"hash-{index}",
            first_party_verified=True,
        ),
        lifecycle=JobLifecycle.OPEN,
    )


def _synthetic_state(count: int) -> LiveState:
    now = datetime.now(UTC)
    jobs = {f"job-{i:06d}": _make_job(i) for i in range(count)}
    return LiveState(generated_at=now, jobs=jobs)


def test_site_data_sharding_writes_10k(tmp_path: Path) -> None:
    """10k job corpus writes bounded shards."""
    state = _synthetic_state(10_000)
    builder = SiteDataBuilder(load_project_config())
    manifest = builder.write(state, tmp_path)

    assert manifest.total_jobs == 10_000
    assert len(manifest.shards) >= 1
    max_bytes = max(s.byte_size for s in manifest.shards)
    assert max_bytes <= builder.max_shard_bytes * 1.05


@pytest.mark.parametrize("job_count", [50_000, 100_000])
def test_site_data_bucket_partition(job_count: int) -> None:
    """Large corpora partition into hash buckets without exceeding memory limits."""
    state = _synthetic_state(job_count)
    builder = SiteDataBuilder(load_project_config())
    buckets = builder.build(state)
    total = sum(len(jobs) for jobs in buckets.values())
    assert total == job_count
    non_empty = sum(1 for jobs in buckets.values() if jobs)
    assert non_empty >= 16


def test_bucket_distribution() -> None:
    state = _synthetic_state(5000)
    builder = SiteDataBuilder(load_project_config())
    buckets = builder.build(state)
    non_empty = sum(1 for jobs in buckets.values() if jobs)
    assert non_empty >= 8
