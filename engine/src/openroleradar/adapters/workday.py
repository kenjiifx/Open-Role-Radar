"""Workday public CXS job board adapter."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any, ClassVar
from urllib.parse import urlparse

import orjson

from openroleradar.adapters.base import AdapterFetchResult, register_adapter
from openroleradar.http.client import SafeHTTPClient
from openroleradar.models.job import RawJob, Source

WORKDAY_HOST_SUFFIXES = (
    "myworkdayjobs.com",
    "myworkdaysite.com",
)

# Tenant forms:
#   host/site                 → adobe.wd5.myworkdayjobs.com/external_experienced
#   host/cxs_tenant/site      → salesforce.wd12.myworkdayjobs.com/salesforce/External_Career_Site
_TENANT_RE = re.compile(
    r"^(?P<host>[a-z0-9.-]+\.myworkday(?:jobs|site)\.com)/(?:(?P<cxs>[^/]+)/)?(?P<site>[^/]+)/?$",
    re.I,
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


def parse_workday_tenant(tenant: str) -> tuple[str, str, str] | None:
    """Return (host, cxs_tenant, site) from a configured Workday tenant string."""
    raw = tenant.strip().removeprefix("https://").removeprefix("http://")
    match = _TENANT_RE.match(raw)
    if not match:
        return None
    host = match.group("host").lower()
    site = match.group("site")
    cxs = match.group("cxs") or host.split(".", 1)[0]
    return host, cxs, site


class WorkdayAdapter:
    """Fetch jobs from public Workday CXS career sites."""

    name: ClassVar[str] = "workday"
    supported: ClassVar[bool] = True
    page_size: ClassVar[int] = 20
    max_jobs: ClassVar[int] = 1500

    def detect_host(self, hostname: str) -> bool:
        host = hostname.lower().rstrip(".")
        return any(host == suffix or host.endswith(f".{suffix}") for suffix in WORKDAY_HOST_SUFFIXES)

    def extract_tenant(self, url: str) -> str | None:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if not self.detect_host(host):
            return None
        parts = [part for part in parsed.path.split("/") if part]
        # Skip CXS API path segments when present.
        if len(parts) >= 4 and parts[0] == "wday" and parts[1] == "cxs":
            return f"{host}/{parts[2]}/{parts[3]}"
        if parts:
            return f"{host}/{parts[0]}"
        return host

    def build_api_url(self, tenant: str) -> str:
        parsed = parse_workday_tenant(tenant)
        if parsed is None:
            return f"https://{tenant}"
        host, cxs, site = parsed
        return f"https://{host}/wday/cxs/{cxs}/{site}/jobs"

    def build_job_url(self, tenant: str, external_path: str) -> str:
        parsed = parse_workday_tenant(tenant)
        if parsed is None:
            return external_path
        host, _cxs, site = parsed
        path = external_path if external_path.startswith("/") else f"/{external_path}"
        return f"https://{host}/{site}{path}"

    def parse_payload(self, payload: Any, source: Source) -> list[RawJob]:
        data = orjson.loads(payload) if isinstance(payload, (bytes, str)) else payload
        if not isinstance(data, dict):
            return []
        postings = data.get("jobPostings", [])
        if not isinstance(postings, list):
            return []
        jobs: list[RawJob] = []
        for item in postings:
            if not isinstance(item, dict):
                continue
            job = self._parse_job(item, source)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_job(self, item: dict[str, Any], source: Source) -> RawJob | None:
        title = str(item.get("title") or "").strip()
        external_path = str(item.get("externalPath") or "").strip()
        if not title or not external_path:
            return None

        # Prefer bulletFields / locationsText for location.
        locations: list[str] = []
        locations_text = item.get("locationsText")
        if isinstance(locations_text, str) and locations_text.strip():
            locations = [locations_text.strip()]

        bullet = item.get("bulletFields")
        if isinstance(bullet, list):
            for field in bullet:
                if not isinstance(field, str):
                    continue
                stripped = field.strip()
                # Often includes req id / time type — keep short location-like values.
                if (
                    stripped
                    and stripped not in locations
                    and len(stripped) < 80
                    and any(ch.isalpha() for ch in stripped)
                ):
                    locations.append(stripped)

        posted = (
            item.get("postedOn")
            or item.get("postedDate")
            or item.get("firstSeen")
            or item.get("timePosted")
        )
        # Workday often returns relative strings like "Posted 3 Days Ago" — ignore those.
        posted_at = _parse_datetime(str(posted) if isinstance(posted, str) and "T" in posted else None)

        job_url = self.build_job_url(source.adapter_tenant, external_path)
        source_job_id = external_path.rstrip("/").rsplit("/", 1)[-1] or external_path

        return RawJob(
            source_job_id=source_job_id,
            title=title,
            job_url=job_url,
            apply_url=job_url,
            locations_raw=locations,
            description_text=None,
            summary=None,
            employment_type=None,
            department=None,
            posted_at=posted_at,
            metadata={
                "company_name": source.company_name,
                "workday_external_path": external_path,
            },
        )

    async def fetch_jobs(self, source: Source, client: SafeHTTPClient) -> AdapterFetchResult:
        parsed = parse_workday_tenant(source.adapter_tenant)
        if parsed is None:
            return AdapterFetchResult(
                status="error",
                message=(
                    "Workday tenant must look like "
                    "'company.wd5.myworkdayjobs.com/SiteName' "
                    f"(got {source.adapter_tenant!r})"
                ),
            )

        api_url = self.build_api_url(source.adapter_tenant)
        jobs: list[RawJob] = []
        offset = 0
        total: int | None = None

        while offset < self.max_jobs:
            body = {
                "appliedFacets": {},
                "limit": self.page_size,
                "offset": offset,
                "searchText": "",
            }
            response = await client.post(
                api_url,
                content=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            if response.status_code != 200:
                if offset == 0:
                    return AdapterFetchResult(
                        status="error",
                        message=f"Workday CXS returned HTTP {response.status_code}",
                    )
                break

            try:
                payload = json.loads(response.content)
            except json.JSONDecodeError as exc:
                return AdapterFetchResult(
                    status="error",
                    message=f"Invalid JSON from Workday CXS: {exc}",
                )

            if isinstance(payload, dict) and total is None:
                try:
                    total = int(payload.get("total") or 0)
                except (TypeError, ValueError):
                    total = None

            batch = self.parse_payload(payload, source)
            if not batch:
                break
            jobs.extend(batch)
            offset += len(batch)
            if total is not None and offset >= total:
                break
            if len(batch) < self.page_size:
                break

        return AdapterFetchResult(
            jobs=jobs[: self.max_jobs],
            status="ok",
            metadata={"job_count": len(jobs), "total": total},
        )


workday_adapter = register_adapter(WorkdayAdapter())
