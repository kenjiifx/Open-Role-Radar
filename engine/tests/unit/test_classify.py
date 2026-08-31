"""Unit tests for classification modules."""

from __future__ import annotations

from pathlib import Path

from openroleradar.classify.career_level import classify_career_level
from openroleradar.classify.discipline import classify_discipline
from openroleradar.classify.skills import extract_skills
from openroleradar.models.enums import CareerLevel


def test_classify_internship_from_title(repo_root: Path) -> None:
    level, confidence = classify_career_level(
        "Software Engineering Intern",
        "Summer internship for students.",
        root=repo_root,
    )
    assert level == CareerLevel.INTERNSHIP
    assert confidence >= 0.6


def test_senior_exclusion_blocks_intern_match(repo_root: Path) -> None:
    level, confidence = classify_career_level(
        "Senior Software Engineer",
        "Not an intern role.",
        root=repo_root,
    )
    assert level == CareerLevel.UNKNOWN
    assert confidence == 0.0


def test_classify_discipline_backend(repo_root: Path) -> None:
    result = classify_discipline(
        "Backend Engineer",
        department="Platform Engineering",
        description="Build APIs and services.",
        root=repo_root,
    )
    assert result.primary == "backend"
    assert result.confidence >= 0.5


def test_extract_skills_python_react(repo_root: Path) -> None:
    skills = extract_skills(
        "Experience with Python, React, and Kubernetes required.",
        root=repo_root,
    )
    assert "Python" in skills
    assert "React" in skills
    assert "Kubernetes" in skills
