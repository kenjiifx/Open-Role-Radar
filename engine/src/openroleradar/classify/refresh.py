"""Re-apply taxonomy classification to stored jobs before public export."""

from __future__ import annotations

from pathlib import Path

from openroleradar.classify.career_level import classify_career_level
from openroleradar.classify.discipline import classify_discipline
from openroleradar.models.state import LiveState


def reclassify_state(state: LiveState, *, root: Path | None = None) -> int:
    """Refresh career level (and discipline) for every job using current taxonomy.

    Returns the number of jobs whose career_level or confidence changed.
    """
    changed = 0
    for job in state.jobs.values():
        level, confidence = classify_career_level(job.title, job.summary, root=root)
        disciplines = classify_discipline(job.title, description=job.summary, root=root)
        if job.career_level != level or abs(job.career_level_confidence - confidence) > 1e-9:
            changed += 1
        job.career_level = level
        job.career_level_confidence = confidence
        job.disciplines = disciplines
    return changed
