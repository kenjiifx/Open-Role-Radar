"""Unit tests for career level classification accuracy."""

from __future__ import annotations

from openroleradar.classify.career_level import classify_career_level
from openroleradar.export.public_filter import is_public_job
from openroleradar.models.enums import CareerLevel
from tests.conftest import sample_job


def test_internship_title_is_public() -> None:
    level, confidence = classify_career_level("Software Engineering Intern")
    assert level == CareerLevel.INTERNSHIP
    assert confidence >= 0.65
    assert is_public_job(sample_job(career_level=level, career_level_confidence=confidence))


def test_senior_title_rejected() -> None:
    level, confidence = classify_career_level("Senior Software Engineer")
    assert level == CareerLevel.UNKNOWN
    assert confidence == 0.0


def test_description_only_intern_mention_not_public() -> None:
    level, confidence = classify_career_level(
        "Software Engineer II",
        "We also run an intern program and hire junior teammates.",
    )
    assert confidence < 0.55
    assert not is_public_job(
        sample_job(career_level=level, career_level_confidence=confidence)
    )


def test_new_grad_title() -> None:
    level, confidence = classify_career_level("New Grad Software Engineer")
    assert level == CareerLevel.NEW_GRAD
    assert confidence >= 0.65


def test_step_intern_title() -> None:
    level, confidence = classify_career_level("STEP Intern — Software Engineering")
    assert level == CareerLevel.INTERNSHIP
    assert confidence >= 0.65


def test_jr_and_engineer_i_titles() -> None:
    level, confidence = classify_career_level("Jr. Software Engineer")
    assert level == CareerLevel.ENTRY_LEVEL
    assert confidence >= 0.65
    level, confidence = classify_career_level("Software Engineer I")
    assert level == CareerLevel.ENTRY_LEVEL
    assert confidence >= 0.65


def test_lead_intern_not_rejected() -> None:
    level, confidence = classify_career_level("Lead Intern, Product Design")
    assert level == CareerLevel.INTERNSHIP
    assert confidence >= 0.65


def test_ats_metadata_promotes_generic_title() -> None:
    level, confidence = classify_career_level(
        "Software Engineer",
        employment_type="Intern",
        metadata={"experience_level": "Internship"},
    )
    assert level == CareerLevel.INTERNSHIP
    assert confidence >= 0.7
