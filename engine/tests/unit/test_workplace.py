"""Unit tests for workplace type inference."""

from __future__ import annotations

from openroleradar.models.enums import WorkplaceType
from openroleradar.normalize.location import parse_workplace_type


def test_hybrid_location_is_hybrid() -> None:
    assert parse_workplace_type(["Hybrid - New York, NY"]) == WorkplaceType.HYBRID


def test_hybrid_not_classified_as_remote() -> None:
    result = parse_workplace_type(["Hybrid"])
    assert result == WorkplaceType.HYBRID
    assert result != WorkplaceType.REMOTE


def test_remote_only_is_remote() -> None:
    assert parse_workplace_type(["Remote - United States"]) == WorkplaceType.REMOTE


def test_onsite_city_is_onsite() -> None:
    assert parse_workplace_type(["San Francisco, CA, USA"]) == WorkplaceType.ONSITE
