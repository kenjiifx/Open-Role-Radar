"""Shared helpers for deciding which jobs appear in public exports."""

from __future__ import annotations

from functools import lru_cache

from openroleradar.config import load_project_config
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


@lru_cache(maxsize=1)
def _configured_min_confidence() -> float:
    try:
        config = load_project_config()
        value = float(config.classification.get("early_career_min_confidence", 0.55))
    except Exception:
        value = 0.55
    return max(0.0, min(value, 1.0))


def is_public_job(job: Job, *, min_confidence: float | None = None) -> bool:
    """Return True when a job should appear on the public site/API/feeds.

    Title-level early-career signals are preferred; min confidence comes from
    config/project.yml unless overridden.
    """
    threshold = _configured_min_confidence() if min_confidence is None else min_confidence
    if job.lifecycle not in {JobLifecycle.OPEN, JobLifecycle.REOPENED}:
        return False
    if job.career_level not in EARLY_CAREER_LEVELS:
        return False
    return job.career_level_confidence >= threshold
