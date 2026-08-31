"""Property-based invariant tests."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from openroleradar.dedupe.identity import generate_job_id
from openroleradar.normalize.text import canonicalize_text, normalize_whitespace


@given(st.text())
def test_normalize_whitespace_idempotent(text: str) -> None:
    once = normalize_whitespace(text)
    twice = normalize_whitespace(once)
    assert once == twice


@given(st.text())
def test_canonicalize_text_idempotent(text: str) -> None:
    once = canonicalize_text(text)
    twice = canonicalize_text(once)
    assert once == twice


@given(
    adapter=st.text(min_size=1, max_size=20),
    tenant=st.text(min_size=1, max_size=20),
    source_job_id=st.text(min_size=1, max_size=40),
)
def test_job_id_stable(adapter: str, tenant: str, source_job_id: str) -> None:
    first = generate_job_id(adapter, tenant, source_job_id)
    second = generate_job_id(adapter, tenant, source_job_id)
    assert first == second
    assert len(first) == 64
