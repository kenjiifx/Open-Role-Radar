"""Tests for promoting ATS boards discovered from apply URLs."""

from __future__ import annotations

from datetime import UTC, datetime

from openroleradar.discovery.promote import promote_ats_board_from_url
from openroleradar.models.state import LiveState


def test_promote_greenhouse_board_from_simplify_url() -> None:
    state = LiveState(generated_at=datetime.now(UTC))
    source = promote_ats_board_from_url(
        state,
        apply_url="https://boards.greenhouse.io/stripe/jobs/12345",
        company_name="Stripe",
        company_domain="stripe.com",
        discovered_via="simplify",
    )
    assert source is not None
    assert source.adapter == "greenhouse"
    assert source.adapter_tenant == "stripe"
    assert source.poll_tier == "hot"
    assert source.source_id in state.sources


def test_promote_is_idempotent() -> None:
    state = LiveState(generated_at=datetime.now(UTC))
    first = promote_ats_board_from_url(
        state,
        apply_url="https://jobs.ashbyhq.com/linear/abc",
        company_name="Linear",
        company_domain="linear.app",
    )
    second = promote_ats_board_from_url(
        state,
        apply_url="https://jobs.ashbyhq.com/linear/def",
        company_name="Linear",
        company_domain="linear.app",
    )
    assert first is not None
    assert second is None


def test_promote_skips_non_ats_urls() -> None:
    state = LiveState(generated_at=datetime.now(UTC))
    source = promote_ats_board_from_url(
        state,
        apply_url="https://careers.example.com/jobs/intern",
        company_name="Example",
        company_domain="example.com",
    )
    assert source is None
    assert state.sources == {}
