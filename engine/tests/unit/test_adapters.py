"""Unit tests for ATS adapters."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openroleradar.adapters import (
    get_adapter,
    list_adapters,
)
from openroleradar.adapters.ashby import AshbyAdapter
from openroleradar.adapters.greenhouse import GreenhouseAdapter
from openroleradar.adapters.json_ld import JsonLdAdapter
from openroleradar.adapters.lever import LeverAdapter
from openroleradar.adapters.smartrecruiters import SmartRecruitersAdapter
from openroleradar.adapters.workday import WorkdayAdapter
from openroleradar.models.job import Source

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _sample_source(adapter: str, tenant: str = "tenant") -> Source:
    now = datetime(2025, 8, 1, tzinfo=UTC)
    return Source(
        source_id=f"{adapter}:{tenant}",
        company_id=tenant,
        company_name=tenant.title(),
        company_domain=f"{tenant}.example",
        careers_url=f"https://careers.example/{tenant}",
        adapter=adapter,
        adapter_tenant=tenant,
        first_discovered_at=now,
    )


def test_adapter_registry_contains_all_adapters() -> None:
    names = set(list_adapters())
    assert names == {
        "ashby",
        "greenhouse",
        "json_ld",
        "lever",
        "smartrecruiters",
        "workable",
        "workday",
    }
    assert get_adapter("greenhouse").name == "greenhouse"


def test_greenhouse_parses_stripe_fixture() -> None:
    payload = json.loads((FIXTURES / "greenhouse_stripe.json").read_text(encoding="utf-8"))
    adapter = GreenhouseAdapter()
    source = _sample_source("greenhouse", "stripe")
    jobs = adapter.parse_payload(payload, source)

    assert len(jobs) == 2
    assert jobs[0].title == "Software Engineer, Intern"
    assert jobs[0].source_job_id == "7234561"
    assert jobs[0].requisition_id == "REQ-2025-1842"
    assert jobs[0].locations_raw == ["San Francisco, CA"]
    assert jobs[0].job_url.startswith("https://boards.greenhouse.io/stripe/")
    assert jobs[0].description_text is not None
    assert "economic infrastructure" in jobs[0].description_text


def test_lever_parses_plaid_fixture() -> None:
    payload = json.loads((FIXTURES / "lever_plaid.json").read_text(encoding="utf-8"))
    adapter = LeverAdapter()
    source = _sample_source("lever", "plaid")
    jobs = adapter.parse_payload(payload, source)

    assert len(jobs) == 2
    assert jobs[0].title == "Backend Engineer, Early Career"
    assert jobs[0].employment_type == "Full-time"
    assert jobs[0].department == "Engineering"
    assert jobs[1].title == "Software Engineering Intern"
    assert jobs[1].posted_at is not None


def test_ashby_parses_sample_fixture() -> None:
    payload = json.loads((FIXTURES / "ashby_sample.json").read_text(encoding="utf-8"))
    adapter = AshbyAdapter()
    source = _sample_source("ashby", "ramp")
    jobs = adapter.parse_payload(payload, source)

    assert len(jobs) == 2
    assert jobs[0].title == "Software Engineer, New Grad"
    assert jobs[0].employment_type == "FullTime"
    assert jobs[0].apply_url.endswith("/application")
    assert jobs[1].department == "Operations"


def test_smartrecruiters_parses_sample_fixture() -> None:
    payload = json.loads((FIXTURES / "smartrecruiters_sample.json").read_text(encoding="utf-8"))
    adapter = SmartRecruitersAdapter()
    source = _sample_source("smartrecruiters", "AcmeCorp")
    jobs = adapter.parse_payload(payload, source)

    assert len(jobs) == 2
    assert jobs[0].title == "Graduate Software Engineer"
    assert jobs[0].requisition_id == "REF-GRAD-2025-01"
    assert jobs[0].locations_raw == ["London, England, United Kingdom"]
    assert jobs[1].employment_type == "Internship"


def test_json_ld_parses_html_fixture() -> None:
    html = (FIXTURES / "json_ld_sample.html").read_text(encoding="utf-8")
    adapter = JsonLdAdapter()
    source = _sample_source("json_ld", "example.com")
    source = source.model_copy(update={"careers_url": "https://example.com/careers"})
    jobs = adapter.parse_html(html, source, page_url="https://example.com/careers")

    assert len(jobs) == 1
    assert jobs[0].title == "Junior Data Analyst"
    assert jobs[0].source_job_id == "EC-DA-2025"
    assert jobs[0].employment_type == "FULL_TIME"
    assert jobs[0].locations_raw == ["Toronto, ON, CA"]
    assert jobs[0].job_url == "https://example.com/careers/junior-data-analyst"


@pytest.mark.asyncio
async def test_workday_adapter_requires_host_site_tenant() -> None:
    adapter = WorkdayAdapter()
    source = _sample_source("workday", "acme")
    source = source.model_copy(
        update={"careers_url": "https://acme.wd5.myworkdayjobs.com/en-US/careers"}
    )

    assert adapter.detect_host("acme.wd5.myworkdayjobs.com")
    assert adapter.supported is True

    class _NoopClient:
        pass

    result = await adapter.fetch_jobs(source, _NoopClient())  # type: ignore[arg-type]
    assert result.status == "error"
    assert result.jobs == []
    assert result.message is not None


def test_workday_tenant_parser() -> None:
    from openroleradar.adapters.workday import parse_workday_tenant

    assert parse_workday_tenant("nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite") == (
        "nvidia.wd5.myworkdayjobs.com",
        "nvidia",
        "NVIDIAExternalCareerSite",
    )
    assert parse_workday_tenant(
        "salesforce.wd12.myworkdayjobs.com/salesforce/External_Career_Site"
    ) == (
        "salesforce.wd12.myworkdayjobs.com",
        "salesforce",
        "External_Career_Site",
    )


@pytest.mark.parametrize(
    ("adapter", "url", "tenant"),
    [
        (GreenhouseAdapter(), "https://boards.greenhouse.io/stripe", "stripe"),
        (LeverAdapter(), "https://jobs.lever.co/plaid/uuid", "plaid"),
        (AshbyAdapter(), "https://jobs.ashbyhq.com/ramp/role", "ramp"),
        (
            SmartRecruitersAdapter(),
            "https://careers.smartrecruiters.com/AcmeCorp/job",
            "AcmeCorp",
        ),
    ],
)
def test_adapters_extract_tenant(adapter: object, url: str, tenant: str) -> None:
    extract = adapter.extract_tenant
    assert extract(url) == tenant
