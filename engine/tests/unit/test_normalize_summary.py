"""Tests for job summary truncation during normalization."""

from __future__ import annotations

from datetime import UTC, datetime

from openroleradar.models.job import RawJob
from openroleradar.normalize.pipeline import normalize_raw_job


def test_long_html_summary_is_stripped_and_truncated() -> None:
    raw = RawJob(
        source_job_id="long-1",
        title="Software Engineering Intern",
        job_url="https://boards.greenhouse.io/example/jobs/1",
        apply_url="https://boards.greenhouse.io/example/jobs/1",
        summary="<p>" + ("Opportunity details " * 120) + "</p>",
        description_text="<p>Short description</p>",
    )
    job = normalize_raw_job(
        raw,
        company_id="co-example",
        company_name="Example",
        adapter="greenhouse",
        adapter_tenant="example",
        source_id="src-example",
        fetched_at=datetime.now(UTC),
    )
    assert job.summary is not None
    assert len(job.summary) <= 1000
    assert "<p>" not in job.summary
    assert job.career_level.value == "internship"
