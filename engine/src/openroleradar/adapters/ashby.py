"""Ashby ATS adapter."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, ClassVar
from urllib.parse import urlparse

import orjson

from openroleradar.adapters.base import AdapterFetchResult, register_adapter
from openroleradar.http.client import SafeHTTPClient
from openroleradar.http.url import build_url
from openroleradar.models.job import RawJob, Source
from openroleradar.normalize.text import html_to_plaintext

ASHBY_HOSTS = frozenset({"jobs.ashbyhq.com", "api.ashbyhq.com"})


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class AshbyAdapter:
    """Adapter for Ashby public job board API."""

    name: ClassVar[str] = "ashby"
    supported: ClassVar[bool] = True

    def detect_host(self, hostname: str) -> bool:
        return hostname.lower().rstrip(".") in ASHBY_HOSTS

    def extract_tenant(self, url: str) -> str | None:
        parsed = urlparse(url)
        if not self.detect_host(parsed.hostname or ""):
            return None
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            return None
        if parts[0] == "posting-api" and len(parts) >= 3:
            return parts[2]
        return parts[0]

    def build_api_url(self, tenant: str) -> str:
        return build_url(
            "https",
            "api.ashbyhq.com",
            f"/posting-api/job-board/{tenant}",
        )

    def parse_payload(self, payload: Any, source: Source) -> list[RawJob]:
        data = orjson.loads(payload) if isinstance(payload, (bytes, str)) else payload

        if not isinstance(data, dict):
            return []

        jobs_data = data.get("jobs", [])
        if not isinstance(jobs_data, list):
            return []

        jobs: list[RawJob] = []
        for item in jobs_data:
            if not isinstance(item, dict):
                continue
            job = self._parse_job(item, source)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_job(self, item: dict[str, Any], source: Source) -> RawJob | None:
        job_id = item.get("id")
        title = item.get("title")
        job_url = item.get("jobUrl") or item.get("applyUrl")
        if not job_id or not title or not job_url:
            return None

        location = item.get("location")
        locations: list[str] = []
        if isinstance(location, str):
            locations = [location]
        elif isinstance(location, dict):
            name = location.get("name") or location.get("location")
            if name:
                locations = [str(name)]

        description = item.get("descriptionPlain") or item.get("descriptionHtml")
        description_text = (
            html_to_plaintext(description) or None if isinstance(description, str) else None
        )

        employment_type = item.get("employmentType")
        department = item.get("department")
        if isinstance(department, dict):
            department = department.get("name")

        apply_url = item.get("applyUrl") or job_url

        return RawJob(
            source_job_id=str(job_id),
            title=str(title).strip(),
            job_url=str(job_url),
            apply_url=str(apply_url),
            locations_raw=locations,
            description_text=description_text,
            summary=None,
            employment_type=str(employment_type) if employment_type else None,
            department=str(department) if department else None,
            posted_at=_parse_datetime(item.get("publishedAt")),
            updated_at=_parse_datetime(item.get("updatedAt")),
            metadata={
                "team": item.get("team"),
                "company_name": source.company_name,
            },
        )

    async def fetch_jobs(self, source: Source, client: SafeHTTPClient) -> AdapterFetchResult:
        api_url = self.build_api_url(source.adapter_tenant)
        response = await client.get(
            api_url,
            etag=source.etag,
            if_modified_since=source.last_modified,
        )

        if response.is_not_modified:
            return AdapterFetchResult(
                not_modified=True,
                etag=response.etag or source.etag,
                last_modified=response.last_modified or source.last_modified,
            )

        if response.status_code != 200:
            return AdapterFetchResult(
                status="error",
                message=f"Ashby API returned HTTP {response.status_code}",
            )

        try:
            payload = json.loads(response.content)
        except json.JSONDecodeError as exc:
            return AdapterFetchResult(
                status="error",
                message=f"Invalid JSON from Ashby API: {exc}",
            )

        jobs = self.parse_payload(payload, source)
        return AdapterFetchResult(
            jobs=jobs,
            etag=response.etag,
            last_modified=response.last_modified,
            metadata={"job_count": len(jobs)},
        )


ashby_adapter = register_adapter(AshbyAdapter())
