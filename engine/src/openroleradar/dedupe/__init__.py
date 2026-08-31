"""Deduplication utilities."""

from openroleradar.dedupe.identity import (
    content_hash_from_job,
    content_hash_from_raw,
    fingerprint_job,
    generate_job_id,
)
from openroleradar.dedupe.merge import DedupeGroup, dedupe_jobs, find_duplicates, merge_job_group

__all__ = [
    "DedupeGroup",
    "content_hash_from_job",
    "content_hash_from_raw",
    "dedupe_jobs",
    "find_duplicates",
    "fingerprint_job",
    "generate_job_id",
    "merge_job_group",
]
