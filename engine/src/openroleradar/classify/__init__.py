"""Classification modules for jobs."""

from openroleradar.classify.academic_term import classify_academic_term
from openroleradar.classify.career_level import classify_career_level
from openroleradar.classify.discipline import classify_discipline
from openroleradar.classify.skills import extract_skills

__all__ = [
    "classify_academic_term",
    "classify_career_level",
    "classify_discipline",
    "extract_skills",
]
