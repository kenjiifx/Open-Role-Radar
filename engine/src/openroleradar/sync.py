"""Synchronization orchestrator — fetch, normalize, lifecycle, export."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from openroleradar.adapters import get_adapter
from openroleradar.config import find_repo_root, load_project_config
from openroleradar.discovery.registry import load_seed_sources, seed_to_company, seed_to_source
from openroleradar.export.site_data import SiteDataBuilder
from openroleradar.export.static_api import StaticApiExporter
from openroleradar.feeds.generator import FeedGenerator
from openroleradar.health.monitor import HealthMonitor
from openroleradar.http.client import SafeHTTPClient
from openroleradar.lifecycle.manager import LifecycleManager
from openroleradar.models.job import Source
from openroleradar.models.state import LiveState
from openroleradar.normalize.pipeline import normalize_raw_job
from openroleradar.storage.local import LocalStateStore

logger = logging.getLogger(__name__)


class SyncOrchestrator:
    """Coordinates source polling, normalization, and state updates."""

    def __init__(self, root: Path | None = None, state_dir: Path | None = None) -> None:
        self.root = root or find_repo_root()
        self.config = load_project_config(self.root)
        self.state_dir = state_dir or (self.root / ".local" / "state")
        self.store = LocalStateStore(self.state_dir)
        self.lifecycle = LifecycleManager()
        self.health = HealthMonitor(self.config)

    def bootstrap_state(self) -> LiveState:
        """Initialize empty state with seed sources."""
        now = datetime.now(UTC)
        state = LiveState(generated_at=now)
        for seed in load_seed_sources(self.root):
            company = seed_to_company(seed, now=now)
            source = seed_to_source(seed, now=now)
            state.companies[company.company_id] = company
            state.sources[source.source_id] = source
        state.metadata["bootstrapped_at"] = now.isoformat()
        return state

    def load_or_bootstrap(self) -> LiveState:
        self.store.ensure_directory()
        if self.store.exists():
            return self.store.load()
        state = self.bootstrap_state()
        self.store.save(state)
        return state

    def _sources_due(self, state: LiveState, now: datetime) -> list[Source]:
        max_sources = int(self.config.polling.get("max_sources_per_sync", 200))
        due: list[Source] = []
        for source in state.sources.values():
            if not source.enabled:
                continue
            if source.health_status in ("blocked", "disabled", "unsupported"):
                continue
            if source.next_due_at is None or source.next_due_at <= now:
                due.append(source)
        due.sort(key=lambda s: s.next_due_at or datetime.min.replace(tzinfo=UTC))
        return due[:max_sources]

    async def _fetch_source(
        self,
        client: SafeHTTPClient,
        source: Source,
        state: LiveState,
    ) -> dict[str, Any]:
        try:
            adapter = get_adapter(source.adapter)
        except KeyError:
            source.health_status = "unsupported"
            return {"source_id": source.source_id, "status": "unsupported", "jobs": []}

        try:
            result = await adapter.fetch_jobs(source, client)
            now = datetime.now(UTC)
            source.last_success_at = now
            source.consecutive_failures = 0
            source.health_status = "healthy"
            source.last_validated_at = now
            if result.etag:
                source.etag = result.etag
            if result.last_modified:
                source.last_modified = result.last_modified
            if result.not_modified:
                return {"source_id": source.source_id, "status": "not_modified", "jobs": []}
            state = self.health.record_success(state, source.adapter)
            return {
                "source_id": source.source_id,
                "status": "ok",
                "jobs": result.jobs,
                "adapter": source.adapter,
            }
        except Exception as exc:
            now = datetime.now(UTC)
            source.last_failure_at = now
            source.consecutive_failures += 1
            if source.consecutive_failures >= 3:
                source.health_status = "degraded"
            if source.consecutive_failures >= 10:
                source.health_status = "failing"
            logger.warning("Source %s failed: %s", source.source_id, exc)
            state = self.health.record_failure(state, source.adapter, str(exc))
            return {"source_id": source.source_id, "status": "error", "error": str(exc), "jobs": []}

    async def run_sync(self, *, sample: bool = False) -> dict[str, Any]:
        """Execute a full synchronization cycle."""
        now = datetime.now(UTC)
        state = self.load_or_bootstrap()
        due = self._sources_due(state, now)
        if sample:
            due = due[:3]

        summary: dict[str, Any] = {
            "sources_due": len(due),
            "fetched": 0,
            "not_modified": 0,
            "new_jobs": 0,
            "updated_jobs": 0,
            "closed": 0,
            "reopened": 0,
            "failures": 0,
            "started_at": now.isoformat(),
        }

        seen_by_source: dict[str, set[str]] = {}

        async with SafeHTTPClient(self.config) as client:
            for source in due:
                result = await self._fetch_source(client, source, state)
                tier_key = f"{source.poll_tier}_minutes"
                tier_minutes = int(self.config.polling.get("tiers", {}).get(tier_key, 60))
                source.next_due_at = now + timedelta(minutes=tier_minutes)

                if result["status"] == "not_modified":
                    summary["not_modified"] += 1
                    continue
                if result["status"] in ("error", "unsupported"):
                    summary["failures"] += 1
                    continue

                summary["fetched"] += 1
                company = state.companies.get(source.company_id)
                if company is None:
                    continue

                source_job_ids: set[str] = set()
                for raw in result.get("jobs", []):
                    source_job_ids.add(raw.source_job_id)
                    try:
                        job = normalize_raw_job(
                            raw,
                            company_id=company.company_id,
                            company_name=company.name,
                            adapter=source.adapter,
                            adapter_tenant=source.adapter_tenant,
                            source_id=source.source_id,
                            fetched_at=now,
                            source_health=source.health_status,
                            root=self.root,
                        )
                    except Exception as exc:
                        logger.warning("Normalize failed for %s: %s", raw.source_job_id, exc)
                        continue

                    existing = state.jobs.get(job.job_id)
                    if existing is None:
                        state.jobs[job.job_id] = job
                        summary["new_jobs"] += 1
                        self.lifecycle.record_opened(state, job)
                    else:
                        changes = self.lifecycle.apply_update(existing, job, now)
                        if changes:
                            summary["updated_jobs"] += 1

                seen_by_source[source.source_id] = source_job_ids
                company.active_job_count = sum(
                    1
                    for j in state.jobs.values()
                    if j.company_id == company.company_id
                    and j.lifecycle.value in ("open", "reopened")
                )
                company.last_seen_at = now

        for source_id, seen_ids in seen_by_source.items():
            src = state.sources.get(source_id)
            if src is None or src.health_status == "failing":
                continue
            closed, reopened = self.lifecycle.process_missing_jobs(state, src, seen_ids, now)
            summary["closed"] += closed
            summary["reopened"] += reopened

        state.generated_at = datetime.now(UTC)
        self.store.save(state)
        summary["finished_at"] = state.generated_at.isoformat()
        summary["total_jobs"] = len(state.jobs)
        return summary

    def build_exports(self) -> dict[str, Any]:
        """Generate static API, site data, and feeds."""
        state = self.store.load()
        api_dir = self.root / "site" / "public" / "api" / "v1"
        StaticApiExporter(self.config).export(state, api_dir)

        data_dir = self.root / "site" / "public" / "data"
        manifest = SiteDataBuilder(self.config).write(state, data_dir)

        feeds_dir = self.root / "site" / "public" / "feeds"
        FeedGenerator(self.config).write_all(state, feeds_dir)

        return {
            "api_dir": str(api_dir),
            "data_shards": len(manifest.shards),
            "total_jobs": manifest.total_jobs,
        }
