"""Greenhouse ATS adapter."""

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

GREENHOUSE_HOSTS = frozenset(
    {
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "boards-api.greenhouse.io",
    }
)


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


class GreenhouseAdapter:
    """Adapter for Greenhouse Job Board API."""

    name: ClassVar[str] = "greenhouse"
    supported: ClassVar[bool] = True

    def detect_host(self, hostname: str) -> bool:
        return hostname.lower().rstrip(".") in GREENHOUSE_HOSTS

    def extract_tenant(self, url: str) -> str | None:
        parsed = urlparse(url)
        if not self.detect_host(parsed.hostname or ""):
            return None
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            return None
        if parts[0] == "v1" and len(parts) >= 3 and parts[1] == "boards":
            return parts[2]
        return parts[0]

    def build_api_url(self, tenant: str) -> str:
        return build_url(
            "https",
            "boards-api.greenhouse.io",
            f"/v1/boards/{tenant}/jobs",
            query={"content": "true"},
        )

    def parse_payload(self, payload: Any, source: Source) -> list[RawJob]:
        data = orjson.loads(payload) if isinstance(payload, (bytes, str)) else payload

        jobs_data = data.get("jobs", data) if isinstance(data, dict) else data
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
        job_url = item.get("absolute_url")
        if job_id is None or not title or not job_url:
            return None

        location = item.get("location") or {}
        location_name = location.get("name") if isinstance(location, dict) else None
        locations = [location_name] if location_name else []

        description = html_to_plaintext(item.get("content")) or None
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}

        departments: list[str] = []
        offices: list[str] = []
        if isinstance(metadata, dict):
            for key in ("department", "departments", "team"):
                value = metadata.get(key)
                if isinstance(value, str):
                    departments.append(value)
                elif isinstance(value, list):
                    departments.extend(str(v) for v in value)
            office_value = metadata.get("office") or metadata.get("offices")
            if isinstance(office_value, str):
                offices.append(office_value)
            elif isinstance(office_value, list):
                offices.extend(str(v) for v in office_value)

        department = departments[0] if departments else item.get("department")
        if offices and not locations:
            locations = offices

        return RawJob(
            source_job_id=str(job_id),
            requisition_id=item.get("requisition_id"),
            title=str(title).strip(),
            job_url=str(job_url),
            apply_url=str(job_url),
            locations_raw=locations,
            description_text=description,
            summary=None,
            department=str(department) if department else None,
            posted_at=_parse_datetime(item.get("first_published")),
            updated_at=_parse_datetime(item.get("updated_at")),
            metadata={
                "internal_job_id": item.get("internal_job_id"),
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
                message=f"Greenhouse API returned HTTP {response.status_code}",
            )

        try:
            payload = json.loads(response.content)
        except json.JSONDecodeError as exc:
            return AdapterFetchResult(
                status="error",
                message=f"Invalid JSON from Greenhouse API: {exc}",
            )

        jobs = self.parse_payload(payload, source)
        return AdapterFetchResult(
            jobs=jobs,
            etag=response.etag,
            last_modified=response.last_modified,
            metadata={"job_count": len(jobs)},
        )


greenhouse_adapter = register_adapter(GreenhouseAdapter())
