"""Tests for academic term classification."""

from __future__ import annotations

from openroleradar.classify.academic_term import classify_academic_term
from openroleradar.models.enums import AcademicTerm


def test_summer_from_title() -> None:
    assert classify_academic_term("Software Engineering Intern - Summer 2027") == AcademicTerm.SUMMER


def test_fall_from_title() -> None:
    assert classify_academic_term("Fall Co-op Software Developer") == AcademicTerm.FALL


def test_unknown_when_absent() -> None:
    assert classify_academic_term("New Grad Software Engineer") == AcademicTerm.UNKNOWN


def test_simplify_terms_preferred() -> None:
    assert (
        classify_academic_term(
            "Software Engineering Intern",
            metadata={"simplify_terms": ["Summer 2026"]},
        )
        == AcademicTerm.SUMMER
    )


def test_spring_boot_not_spring_term() -> None:
    assert (
        classify_academic_term(
            "Backend Engineer",
            description="Build APIs with Spring Boot and Java.",
        )
        == AcademicTerm.UNKNOWN
    )


def test_rolling_out_not_rolling_term() -> None:
    assert (
        classify_academic_term(
            "Platform Intern",
            description="We are rolling out a new deployment pipeline.",
        )
        == AcademicTerm.UNKNOWN
    )


def test_leftmost_season_wins() -> None:
    assert (
        classify_academic_term("Fall / Winter 2026 Software Intern") == AcademicTerm.FALL
    )
