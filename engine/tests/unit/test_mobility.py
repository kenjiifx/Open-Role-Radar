"""Unit tests for mobility extraction."""

from __future__ import annotations

from openroleradar.mobility.extract import extract_mobility_benefits
from openroleradar.models.enums import EvidenceStatus


def test_visa_sponsorship_confirmed_with_evidence() -> None:
    benefits = extract_mobility_benefits(
        "We offer visa sponsorship for qualified international candidates."
    )
    assert benefits.visa_sponsorship.status == EvidenceStatus.CONFIRMED
    assert benefits.visa_sponsorship.evidence_excerpt is not None
    assert benefits.visa_sponsorship.confidence > 0


def test_visa_sponsorship_not_available_with_evidence() -> None:
    benefits = extract_mobility_benefits("No visa sponsorship is available for this role.")
    assert benefits.visa_sponsorship.status == EvidenceStatus.NOT_AVAILABLE
    assert benefits.visa_sponsorship.evidence_excerpt is not None


def test_relocation_unknown_without_evidence() -> None:
    benefits = extract_mobility_benefits("Join our engineering team in Austin.")
    assert benefits.relocation_assistance.status == EvidenceStatus.UNKNOWN
    assert benefits.relocation_assistance.evidence_excerpt is None


def test_housing_and_airfare_confirmed() -> None:
    text = "Housing stipend provided. Airfare reimbursement available for relocations."
    benefits = extract_mobility_benefits(text)
    assert benefits.housing_stipend.status == EvidenceStatus.CONFIRMED
    assert benefits.airfare.status == EvidenceStatus.CONFIRMED
