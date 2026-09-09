"""Workable public widget/job-board adapter."""

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

WORKABLE_HOSTS = frozenset({"apply.workable.com", "jobs.workable.com"})


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


class WorkableAdapter:
    """Adapter for Workable public account widget API."""

    name: ClassVar[str] = "workable"
    supported: ClassVar[bool] = True

    def detect_host(self, hostname: str) -> bool:
        return hostname.lower().rstrip(".") in WORKABLE_HOSTS

    def extract_tenant(self, url: str) -> str | None:
        parsed = urlparse(url)
        if not self.detect_host(parsed.hostname or ""):
            return None
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            return None
        if parts[0] == "api" and len(parts) >= 4 and parts[3] == "accounts":
            return parts[4] if len(parts) > 4 else None
        return parts[0]

    def build_api_url(self, tenant: str) -> str:
        return build_url(
            "https",
            "apply.workable.com",
            f"/api/v1/widget/accounts/{tenant}",
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
        job_id = item.get("id") or item.get("shortcode")
        title = str(item.get("title") or "").strip()
        if not job_id or not title:
            return None

        shortcode = str(item.get("shortcode") or job_id)
        job_url = str(
            item.get("url")
            or item.get("application_url")
            or f"https://apply.workable.com/{source.adapter_tenant}/j/{shortcode}/"
        )
        apply_url = str(item.get("application_url") or job_url)

        locations: list[str] = []
        city = item.get("city")
        state = item.get("state")
        country = item.get("country")
        location = ", ".join(str(part) for part in (city, state, country) if part)
        if location:
            locations = [location]
        elif isinstance(item.get("locations"), list):
            for entry in item["locations"]:
                if isinstance(entry, dict):
                    label = entry.get("city") or entry.get("location") or entry.get("country")
                    if label:
                        locations.append(str(label))
                elif isinstance(entry, str) and entry.strip():
                    locations.append(entry.strip())

        description = item.get("description") or item.get("full_description")
        description_text = (
            html_to_plaintext(description) or None if isinstance(description, str) else None
        )

        employment = item.get("employment_type") or item.get("department")
        return RawJob(
            source_job_id=str(job_id),
            title=title,
            job_url=job_url,
            apply_url=apply_url,
            locations_raw=locations,
            description_text=description_text,
            summary=None,
            employment_type=str(employment) if employment else None,
            department=str(item.get("department")) if item.get("department") else None,
            posted_at=_parse_datetime(item.get("published_on") or item.get("created_at")),
            updated_at=_parse_datetime(item.get("updated_at")),
            metadata={
                "company_name": source.company_name,
                "workable_shortcode": shortcode,
            },
        )

    async def fetch_jobs(self, source: Source, client: SafeHTTPClient) -> AdapterFetchResult:
        api_url = self.build_api_url(source.adapter_tenant)
        response = await client.get(api_url)
        if response.status_code != 200:
            return AdapterFetchResult(
                status="error",
                message=f"Workable API returned HTTP {response.status_code}",
            )
        try:
            payload = json.loads(response.content)
        except json.JSONDecodeError as exc:
            return AdapterFetchResult(
                status="error",
                message=f"Invalid JSON from Workable API: {exc}",
            )
        jobs = self.parse_payload(payload, source)
        return AdapterFetchResult(jobs=jobs, status="ok", metadata={"job_count": len(jobs)})


workable_adapter = register_adapter(WorkableAdapter())
