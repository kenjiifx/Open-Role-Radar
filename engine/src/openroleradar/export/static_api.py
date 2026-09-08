"""Generate static API shards for site/public/api/v1/."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import orjson

from openroleradar.config import ProjectConfig, load_project_config
from openroleradar.export.public_filter import is_public_job
from openroleradar.export.site_data import SiteDataBuilder
from openroleradar.models.job import Company, Job, Source
from openroleradar.models.state import LiveState


@dataclass(frozen=True)
class ApiManifest:
    """Top-level static API manifest."""

    version: int
    generated_at: str
    endpoints: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "endpoints": self.endpoints,
        }


class StaticApiExporter:
    """Export versioned static API JSON under site/public/api/v1/."""

    API_VERSION = "v1"

    def __init__(self, config: ProjectConfig | None = None) -> None:
        self.config = config or load_project_config()
        self._site_builder = SiteDataBuilder(self.config)

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))

    def _export_meta(self, state: LiveState, api_dir: Path) -> None:
        public_jobs = sum(1 for job in state.jobs.values() if is_public_job(job))
        meta = {
            "schema_version": state.schema_version,
            "generated_at": state.generated_at.isoformat(),
            "job_count": public_jobs,
            "tracked_job_count": len(state.jobs),
            "company_count": len(state.companies),
            "source_count": len(state.sources),
            "event_count": len(state.events),
            "project": {
                "name": self.config.display_name,
                "slug": self.config.slug,
                "website_url": self.config.website_url,
            },
            "versions": self.config.versions.model_dump(),
        }
        self._write_json(api_dir / "meta.json", meta)

    def _export_companies(self, state: LiveState, api_dir: Path) -> None:
        companies: dict[str, dict[str, Any]] = {}
        for company_id, company in state.companies.items():
            companies[company_id] = company.model_dump(mode="json")
        self._write_json(api_dir / "companies.json", companies)

    def _export_sources(self, state: LiveState, api_dir: Path) -> None:
        sources: dict[str, dict[str, Any]] = {}
        for source_id, source in state.sources.items():
            sources[source_id] = source.model_dump(mode="json")
        self._write_json(api_dir / "sources.json", sources)

    def _export_jobs_index(self, state: LiveState, api_dir: Path) -> list[dict[str, str]]:
        index: list[dict[str, str]] = []
        for job in state.jobs.values():
            if not is_public_job(job):
                continue
            bucket = SiteDataBuilder.bucket_for_job(job.job_id, self._site_builder.hash_buckets)
            index.append(
                {
                    "job_id": job.job_id,
                    "company_id": job.company_id,
                    "title": job.title,
                    "bucket": f"{bucket:02d}",
                }
            )
        index.sort(key=lambda item: item["job_id"])
        self._write_json(api_dir / "jobs-index.json", index)
        return index

    def export(self, state: LiveState, site_root: Path) -> ApiManifest:
        """Write all static API artifacts and return the manifest."""
        api_dir = site_root / "public" / "api" / self.API_VERSION
        jobs_dir = api_dir / "jobs"

        self._export_meta(state, api_dir)
        self._export_companies(state, api_dir)
        self._export_sources(state, api_dir)
        self._export_jobs_index(state, api_dir)
        site_manifest = self._site_builder.write(state, jobs_dir)

        manifest = ApiManifest(
            version=self.config.versions.static_api,
            generated_at=state.generated_at.isoformat(),
            endpoints={
                "meta": f"api/{self.API_VERSION}/meta.json",
                "companies": f"api/{self.API_VERSION}/companies.json",
                "sources": f"api/{self.API_VERSION}/sources.json",
                "jobs_index": f"api/{self.API_VERSION}/jobs-index.json",
                "jobs_shards": f"api/{self.API_VERSION}/jobs/manifest.json",
            },
        )
        self._write_json(api_dir / "manifest.json", manifest.to_dict())
        self._write_json(jobs_dir / "manifest.json", site_manifest.to_dict())
        return manifest

    @staticmethod
    def load_job_shard(path: Path) -> list[Job]:
        raw = orjson.loads(path.read_bytes())
        if not isinstance(raw, list):
            raise ValueError("Job shard must be a JSON array")
        return [Job.model_validate(item) for item in raw]

    @staticmethod
    def load_company_map(path: Path) -> dict[str, Company]:
        raw = orjson.loads(path.read_bytes())
        if not isinstance(raw, dict):
            raise ValueError("Companies file must be a JSON object")
        return {key: Company.model_validate(value) for key, value in raw.items()}

    @staticmethod
    def load_source_map(path: Path) -> dict[str, Source]:
        raw = orjson.loads(path.read_bytes())
        if not isinstance(raw, dict):
            raise ValueError("Sources file must be a JSON object")
        return {key: Source.model_validate(value) for key, value in raw.items()}
