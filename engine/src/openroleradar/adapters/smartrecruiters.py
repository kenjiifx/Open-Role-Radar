"""SmartRecruiters ATS adapter."""

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

SMARTRECRUITERS_HOSTS = frozenset(
    {
        "careers.smartrecruiters.com",
        "api.smartrecruiters.com",
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


class SmartRecruitersAdapter:
    """Adapter for SmartRecruiters public postings API."""

    name: ClassVar[str] = "smartrecruiters"
    supported: ClassVar[bool] = True

    def detect_host(self, hostname: str) -> bool:
        return hostname.lower().rstrip(".") in SMARTRECRUITERS_HOSTS

    def extract_tenant(self, url: str) -> str | None:
        parsed = urlparse(url)
        if not self.detect_host(parsed.hostname or ""):
            return None
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            return None
        if parts[0] == "v1" and len(parts) >= 3 and parts[1] == "companies":
            return parts[2]
        return parts[0]

    def build_api_url(self, tenant: str) -> str:
        return build_url(
            "https",
            "api.smartrecruiters.com",
            f"/v1/companies/{tenant}/postings",
        )

    def parse_payload(self, payload: Any, source: Source) -> list[RawJob]:
        data = orjson.loads(payload) if isinstance(payload, (bytes, str)) else payload

        if not isinstance(data, dict):
            return []

        content = data.get("content", [])
        if not isinstance(content, list):
            return []

        jobs: list[RawJob] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            job = self._parse_job(item, source)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_job(self, item: dict[str, Any], source: Source) -> RawJob | None:
        job_id = item.get("id")
        title = (item.get("name") or item.get("jobAdTitle") or "").strip()
        if not job_id or not title:
            return None

        ref = item.get("ref") or item.get("refNumber")
        location = item.get("location") if isinstance(item.get("location"), dict) else {}
        location_parts = [
            str(location.get(key))
            for key in ("city", "region", "country")
            if isinstance(location, dict) and location.get(key)
        ]
        location_label = ", ".join(location_parts) if location_parts else None

        department = item.get("department")
        if isinstance(department, dict):
            department = department.get("label")

        company_raw = item.get("company")
        company: dict[str, Any] = company_raw if isinstance(company_raw, dict) else {}
        tenant = company.get("identifier") or source.adapter_tenant
        posting_slug = item.get("slug") or item.get("uuid") or job_id
        job_url = item.get("postingUrl") or (
            f"https://careers.smartrecruiters.com/{tenant}/{posting_slug}"
        )
        apply_url = item.get("applyUrl") or job_url

        employment_type = item.get("typeOfEmployment")
        if isinstance(employment_type, dict):
            employment_type = employment_type.get("label")

        released = item.get("releasedDate") or item.get("createdOn")

        return RawJob(
            source_job_id=str(job_id),
            requisition_id=str(ref) if ref else None,
            title=title,
            job_url=str(job_url),
            apply_url=str(apply_url),
            locations_raw=[location_label] if location_label else [],
            employment_type=str(employment_type) if employment_type else None,
            department=str(department) if department else None,
            posted_at=_parse_datetime(str(released) if released else None),
            updated_at=_parse_datetime(item.get("updatedOn")),
            metadata={
                "experience_level": item.get("experienceLevel"),
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
                message=f"SmartRecruiters API returned HTTP {response.status_code}",
            )

        try:
            payload = json.loads(response.content)
        except json.JSONDecodeError as exc:
            return AdapterFetchResult(
                status="error",
                message=f"Invalid JSON from SmartRecruiters API: {exc}",
            )

        jobs = self.parse_payload(payload, source)
        return AdapterFetchResult(
            jobs=jobs,
            etag=response.etag,
            last_modified=response.last_modified,
            metadata={"job_count": len(jobs)},
        )


smartrecruiters_adapter = register_adapter(SmartRecruitersAdapter())
