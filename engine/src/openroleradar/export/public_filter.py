"""Shared helpers for deciding which jobs appear in public exports."""

from __future__ import annotations

from openroleradar.models.enums import CareerLevel, JobLifecycle
from openroleradar.models.job import Job

EARLY_CAREER_LEVELS: frozenset[CareerLevel] = frozenset(
    {
        CareerLevel.INTERNSHIP,
        CareerLevel.CO_OP,
        CareerLevel.NEW_GRAD,
        CareerLevel.ENTRY_LEVEL,
        CareerLevel.APPRENTICESHIP,
        CareerLevel.GRADUATE_PROGRAM,
        CareerLevel.ROTATIONAL_PROGRAM,
        CareerLevel.RESEARCH_INTERNSHIP,
        CareerLevel.FELLOWSHIP,
        CareerLevel.STUDENT_PROGRAM,
    }
)


def is_public_job(job: Job, *, min_confidence: float = 0.4) -> bool:
    """Return True when a job should appear on the public site/API/feeds."""
    if job.lifecycle not in {JobLifecycle.OPEN, JobLifecycle.REOPENED}:
        return False
    if job.career_level not in EARLY_CAREER_LEVELS:
        return False
    return job.career_level_confidence >= min_confidence
