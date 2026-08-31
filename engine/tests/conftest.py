"""Shared test fixtures for OpenRoleRadar."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from openroleradar.config import find_repo_root
from openroleradar.models.job import Company, Job, Provenance, Source
from openroleradar.models.state import LiveState


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return find_repo_root(Path(__file__).resolve().parent)


def sample_provenance(**overrides: object) -> Provenance:
    base = {
        "adapter": "greenhouse",
        "source_id": "src-stripe",
        "source_job_id": "job-1",
        "fetched_at": datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
        "content_hash": "abc123",
    }
    base.update(overrides)
    return Provenance.model_validate(base)


def sample_job(job_id: str = "job-1", **overrides: object) -> Job:
    now = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    base = {
        "job_id": job_id,
        "source_job_id": f"src-{job_id}",
        "company_id": "co-stripe",
        "company_name": "Stripe",
        "title": "Software Engineer Intern",
        "job_url": "https://boards.greenhouse.io/stripe/jobs/1",
        "apply_url": "https://boards.greenhouse.io/stripe/jobs/1/apply",
        "first_seen_at": now,
        "last_seen_at": now,
        "provenance": sample_provenance(source_job_id=f"src-{job_id}"),
    }
    base.update(overrides)
    return Job.model_validate(base)


def sample_company(company_id: str = "co-stripe", **overrides: object) -> Company:
    now = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    base = {
        "company_id": company_id,
        "name": "Stripe",
        "normalized_name": "stripe",
        "canonical_domain": "stripe.com",
        "first_seen_at": now,
        "last_seen_at": now,
    }
    base.update(overrides)
    return Company.model_validate(base)


def sample_source(source_id: str = "src-stripe", **overrides: object) -> Source:
    now = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    base = {
        "source_id": source_id,
        "company_id": "co-stripe",
        "company_name": "Stripe",
        "company_domain": "stripe.com",
        "careers_url": "https://stripe.com/careers",
        "adapter": "greenhouse",
        "adapter_tenant": "stripe",
        "first_discovered_at": now,
    }
    base.update(overrides)
    return Source.model_validate(base)


@pytest.fixture
def sample_state() -> LiveState:
    return _sample_state()


def _sample_state(**overrides: object) -> LiveState:
    job = sample_job()
    company = sample_company()
    source = sample_source()
    base = {
        "jobs": {job.job_id: job},
        "companies": {company.company_id: company},
        "sources": {source.source_id: source},
    }
    base.update(overrides)
    return LiveState.model_validate(base)
