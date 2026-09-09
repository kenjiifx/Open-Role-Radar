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
