"""Job lifecycle state machine management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from openroleradar.config import ProjectConfig, load_project_config
from openroleradar.models.enums import JobLifecycle
from openroleradar.models.job import Job


@dataclass
class LifecycleConfig:
    misses_before_suspected_closed: int = 2
    misses_before_closed: int = 4
    unhealthy_source_never_closes: bool = True
    authoritative_status_codes: tuple[int, ...] = (404, 410)

    @classmethod
    def from_project(cls, config: ProjectConfig | None = None) -> LifecycleConfig:
        project = config or load_project_config()
        lifecycle = project.lifecycle or {}
        closure = project.closure or {}
        return cls(
            misses_before_suspected_closed=int(lifecycle.get("misses_before_suspected_closed", 2)),
            misses_before_closed=int(lifecycle.get("misses_before_closed", 4)),
            unhealthy_source_never_closes=bool(
                lifecycle.get("unhealthy_source_never_closes", True)
            ),
            authoritative_status_codes=tuple(closure.get("authoritative_status_codes", [404, 410])),
        )


class LifecycleManager:
    """Manage OPEN -> SUSPECTED_CLOSED -> CLOSED transitions with safe reopening."""

    def __init__(self, config: LifecycleConfig | None = None) -> None:
        self.config = config or LifecycleConfig.from_project()

    def on_job_seen(self, job: Job, now: datetime) -> Job:
        """Mark a job as seen; reopen if it was closed or suspected closed."""
        updated = job.model_copy(deep=True)
        updated.last_seen_at = now

        if updated.lifecycle in {JobLifecycle.CLOSED, JobLifecycle.SUSPECTED_CLOSED}:
            updated.lifecycle = JobLifecycle.REOPENED
            updated.reopened_at = now
            updated.closed_at = None

        if updated.lifecycle == JobLifecycle.REOPENED:
            updated.lifecycle = JobLifecycle.OPEN

        return updated

    def on_job_missing(
        self,
        job: Job,
        *,
        miss_count: int,
        source_health: str,
        now: datetime,
    ) -> Job:
        """Advance lifecycle when a job is absent from a fetch."""
        updated = job.model_copy(deep=True)

        if self.config.unhealthy_source_never_closes and source_health != "healthy":
            return updated

        if updated.lifecycle == JobLifecycle.CLOSED:
            return updated

        if miss_count >= self.config.misses_before_closed:
            updated.lifecycle = JobLifecycle.CLOSED
            updated.closed_at = now
        elif miss_count >= self.config.misses_before_suspected_closed:
            updated.lifecycle = JobLifecycle.SUSPECTED_CLOSED

        return updated

    def on_authoritative_close(
        self,
        job: Job,
        *,
        status_code: int,
        now: datetime,
    ) -> Job:
        """Close immediately when the source returns an authoritative status code."""
        updated = job.model_copy(deep=True)
        if status_code not in self.config.authoritative_status_codes:
            return updated

        updated.lifecycle = JobLifecycle.CLOSED
        updated.closed_at = now
        return updated

    def on_source_failure(self, job: Job, *, source_health: str, now: datetime) -> Job:
        """Never close jobs solely because the source adapter failed."""
        if self.config.unhealthy_source_never_closes and source_health != "healthy":
            return job
        return job

    def record_opened(self, state: object, job: Job) -> None:
        """Record OPENED event — events stored on state if available."""
        from openroleradar.models.job import JobEvent

        events = getattr(state, "events", None)
        if events is None:
            return
        events.append(
            JobEvent(
                event_type="OPENED",
                job_id=job.job_id,
                timestamp=job.first_seen_at,
                new_hash=job.provenance.content_hash,
            )
        )

    def apply_update(self, existing: Job, updated: Job, now: datetime) -> list[str]:
        """Apply meaningful updates; preserve first_seen_at. Returns changed fields."""
        changed: list[str] = []
        if existing.provenance.content_hash == updated.provenance.content_hash:
            existing.last_seen_at = now
            return changed

        preserve_first = existing.first_seen_at
        preserve_opened = existing.provenance.first_seen_at
        for field_name in ("title", "summary", "career_level", "compensation", "locations"):
            if getattr(existing, field_name) != getattr(updated, field_name):
                changed.append(field_name)

        existing.title = updated.title
        existing.summary = updated.summary
        existing.career_level = updated.career_level
        existing.career_level_confidence = updated.career_level_confidence
        existing.disciplines = updated.disciplines
        existing.skills = updated.skills
        existing.locations = updated.locations
        existing.workplace_type = updated.workplace_type
        existing.remote_scope = updated.remote_scope
        existing.compensation = updated.compensation
        existing.eligibility = updated.eligibility
        existing.mobility = updated.mobility
        existing.last_seen_at = now
        existing.last_changed_at = now
        existing.first_seen_at = preserve_first
        existing.provenance.first_seen_at = preserve_opened
        existing.provenance.content_hash = updated.provenance.content_hash
        existing.provenance.fetched_at = updated.provenance.fetched_at
        # Keep ATS posting dates current when the board provides them.
        if updated.source_posted_at is not None:
            existing.source_posted_at = updated.source_posted_at
            existing.provenance.source_posted_at = updated.source_posted_at
        return changed

    def process_missing_jobs(
        self,
        state: object,
        source: object,
        seen_ids: set[str],
        now: datetime,
    ) -> tuple[int, int]:
        """Process jobs missing from a healthy source fetch."""
        from openroleradar.models.enums import JobLifecycle

        jobs = getattr(state, "jobs", {})
        source_id = getattr(source, "source_id", "")
        source_health = getattr(source, "health_status", "healthy")
        closed = 0
        reopened = 0
        miss_counts: dict[str, int] = getattr(state, "metadata", {}).setdefault("miss_counts", {})

        for job in jobs.values():
            if job.provenance.source_id != source_id:
                continue
            if job.source_job_id in seen_ids:
                miss_counts.pop(job.job_id, None)
                if job.lifecycle in {JobLifecycle.CLOSED, JobLifecycle.SUSPECTED_CLOSED}:
                    updated = self.on_job_seen(job, now)
                    jobs[job.job_id] = updated
                    reopened += 1
                else:
                    jobs[job.job_id] = self.on_job_seen(job, now)
                continue

            count = miss_counts.get(job.job_id, 0) + 1
            miss_counts[job.job_id] = count
            updated = self.on_job_missing(
                job,
                miss_count=count,
                source_health=source_health,
                now=now,
            )
            if updated.lifecycle == JobLifecycle.CLOSED and job.lifecycle != JobLifecycle.CLOSED:
                closed += 1
            jobs[job.job_id] = updated

        return closed, reopened
