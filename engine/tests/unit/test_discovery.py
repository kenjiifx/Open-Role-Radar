"""Unit tests for discovery pipeline."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from openroleradar.config import find_repo_root
from openroleradar.discovery.ats_detect import detect_ats_from_url
from openroleradar.discovery.registry import (
    SeedSource,
    deterministic_id,
    load_seed_sources,
    seed_to_company,
    seed_to_source,
)
from openroleradar.discovery.validate import ValidationResult, validate_candidate


def test_deterministic_id_stable() -> None:
    first = deterministic_id("source", "stripe.com", "greenhouse", "stripe")
    second = deterministic_id("source", "stripe.com", "greenhouse", "stripe")
    assert first == second
    assert len(first) == 16


def test_load_seed_sources_from_repo() -> None:
    root = find_repo_root()
    seeds = load_seed_sources(root)
    assert len(seeds) >= 10
    stripe = next(seed for seed in seeds if seed.company == "Stripe")
    assert stripe.adapter == "greenhouse"
    assert stripe.tenant == "stripe"


def test_seed_to_source_and_company() -> None:
    seed = SeedSource(
        company="Stripe",
        domain="stripe.com",
        adapter="greenhouse",
        tenant="stripe",
    )
    source = seed_to_source(seed)
    company = seed_to_company(seed)
    assert source.source_id == seed.source_id
    assert company.company_id == seed.company_id
    assert source.discovery_confidence == 1.0


@pytest.mark.parametrize(
    ("url", "platform", "tenant"),
    [
        ("https://boards.greenhouse.io/stripe/jobs/1", "greenhouse", "stripe"),
        ("https://jobs.lever.co/plaid/abc", "lever", "plaid"),
        ("https://jobs.ashbyhq.com/ramp", "ashby", "ramp"),
    ],
)
def test_detect_ats_from_url(url: str, platform: str, tenant: str) -> None:
    match = detect_ats_from_url(url)
    assert match is not None
    assert match.platform == platform
    assert match.tenant == tenant
    assert match.confidence >= 0.7


def test_validate_candidate_accepts_seed_url() -> None:
    result = validate_candidate(
        url="https://boards.greenhouse.io/stripe",
        company_domain="stripe.com",
        platform="greenhouse",
        tenant="stripe",
        is_seed=True,
    )
    assert isinstance(result, ValidationResult)
    assert result.accepted is True
    assert result.confidence == 1.0


def test_validate_candidate_quarantines_denylisted_domain() -> None:
    result = validate_candidate(
        url="https://www.linkedin.com/jobs/view/123",
        company_domain="linkedin.com",
        platform="greenhouse",
        tenant="example",
    )
    assert result.accepted is False
    assert result.quarantine is True
    assert result.reason == "aggregator_denylist"


@patch("openroleradar.discovery.validate._is_private_ip", return_value=True)
def test_validate_candidate_quarantines_private_ip(_mock_private: object) -> None:
    result = validate_candidate(
        url="https://boards.greenhouse.io/internal",
        company_domain="internal.corp",
        platform="greenhouse",
        tenant="internal",
        base_confidence=0.9,
    )
    assert result.accepted is False
    assert result.quarantine is True
    assert any("private" in issue for issue in result.issues)


def test_quarantine_record_shape() -> None:
    result = validate_candidate(
        url="https://example.com/jobs",
        base_confidence=0.1,
    )
    record = result.to_quarantine_record()
    assert "quarantined_at" in record
    assert record["confidence"] < 0.5
