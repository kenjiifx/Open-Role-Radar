"""Unit tests for public early-career export filtering."""

from __future__ import annotations

from openroleradar.export.public_filter import is_public_job
from openroleradar.models.enums import CareerLevel, JobLifecycle
from tests.conftest import sample_job


def test_public_job_requires_early_career() -> None:
    job = sample_job(career_level=CareerLevel.UNKNOWN, career_level_confidence=0.9)
    assert is_public_job(job) is False


def test_public_job_accepts_internship() -> None:
    job = sample_job(career_level=CareerLevel.INTERNSHIP, career_level_confidence=0.8)
    assert is_public_job(job) is True


def test_public_job_rejects_closed() -> None:
    job = sample_job(
        career_level=CareerLevel.INTERNSHIP,
        career_level_confidence=0.9,
        lifecycle=JobLifecycle.CLOSED,
    )
    assert is_public_job(job) is False


def test_public_job_rejects_low_confidence() -> None:
    job = sample_job(career_level=CareerLevel.NEW_GRAD, career_level_confidence=0.2)
    assert is_public_job(job) is False


def test_public_job_rejects_closed_application_copy() -> None:
    job = sample_job(
        career_level=CareerLevel.INTERNSHIP,
        career_level_confidence=0.9,
        summary="Thanks for your interest. We are no longer accepting applications.",
    )
    assert is_public_job(job) is False


def test_public_job_rejects_missing_apply_url() -> None:
    job = sample_job(
        career_level=CareerLevel.INTERNSHIP,
        career_level_confidence=0.9,
        apply_url="",
    )
    assert is_public_job(job) is False


def test_public_job_rejects_non_cs_retail() -> None:
    job = sample_job(
        title="Team Member - Guest Experience",
        career_level=CareerLevel.INTERNSHIP,
        career_level_confidence=0.9,
        disciplines={"primary": "retail", "secondary": [], "confidence": 0.9},
    )
    assert is_public_job(job) is False


def test_public_job_accepts_cs_by_title_when_discipline_other() -> None:
    job = sample_job(
        title="Software Engineering Intern",
        career_level=CareerLevel.INTERNSHIP,
        career_level_confidence=0.9,
        disciplines={"primary": "other", "secondary": [], "confidence": 0.2},
    )
    assert is_public_job(job) is True


def test_public_job_rejects_support_noise_even_if_discipline_matches() -> None:
    job = sample_job(
        title="Technical Support Engineer I",
        career_level=CareerLevel.ENTRY_LEVEL,
        career_level_confidence=0.9,
        disciplines={"primary": "software", "secondary": [], "confidence": 0.9},
    )
    assert is_public_job(job) is False
