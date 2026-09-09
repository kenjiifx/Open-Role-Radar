"""Tests for job summary truncation during normalization."""

from __future__ import annotations

from datetime import UTC, datetime

from openroleradar.models.job import RawJob
from openroleradar.normalize.pipeline import normalize_raw_job
from openroleradar.normalize.text import html_to_plaintext


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
    assert len(job.summary) <= 2000
    assert "<p>" not in job.summary
    assert "Opportunity details" in job.summary
    assert job.career_level.value == "internship"


def test_double_encoded_greenhouse_html_becomes_readable() -> None:
    raw = RawJob(
        source_job_id="enc-1",
        title="New Grad Software Engineer",
        job_url="https://boards.greenhouse.io/example/jobs/2",
        apply_url="https://boards.greenhouse.io/example/jobs/2",
        description_text=(
            "&lt;div&gt;&lt;h2&gt;About the role&lt;/h2&gt;"
            "&lt;p&gt;Build product with mentorship.&lt;/p&gt;&lt;/div&gt;"
        ),
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
    assert "About the role" in job.summary
    assert "Build product with mentorship" in job.summary
    assert "&lt;" not in job.summary
    assert "<h2>" not in job.summary


def test_html_to_plaintext_preserves_paragraphs() -> None:
    text = html_to_plaintext("<p>First</p><p>Second</p>")
    assert "First" in text
    assert "Second" in text
