from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from openroleradar.models.job import Company, Job, JobEvent, Source


class DiscoveryState(BaseModel):
    github_cursor: str | None = None
    common_crawl_index: str | None = None
    last_github_run: datetime | None = None
    last_common_crawl_run: datetime | None = None
    quarantined_candidates: list[dict[str, Any]] = Field(default_factory=list)


class AdapterHealthStats(BaseModel):
    adapter: str
    success_count: int = 0
    failure_count: int = 0
    last_failure_at: datetime | None = None
    sample_errors: list[str] = Field(default_factory=list)


class LiveState(BaseModel):
    schema_version: int = 1
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    jobs: dict[str, Job] = Field(default_factory=dict)
    companies: dict[str, Company] = Field(default_factory=dict)
    sources: dict[str, Source] = Field(default_factory=dict)
    events: list[JobEvent] = Field(default_factory=list)
    discovery: DiscoveryState = Field(default_factory=DiscoveryState)
    adapter_health: dict[str, AdapterHealthStats] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def migrate_if_needed(self, target_version: int) -> "LiveState":
        if self.schema_version == target_version:
            return self
        while self.schema_version < target_version:
            self.schema_version += 1
        return self
