"""Schema.org JobPosting JSON-LD adapter."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any, ClassVar
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from openroleradar.adapters.base import AdapterFetchResult, register_adapter
from openroleradar.http.client import SafeHTTPClient
from openroleradar.models.job import RawJob, Source

JOB_POSTING_TYPE = "JobPosting"


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


def _strip_html(html: str | None) -> str | None:
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    return text or None


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _location_strings(job_location: Any) -> list[str]:
    locations: list[str] = []
    for entry in _as_list(job_location):
        if isinstance(entry, str):
            locations.append(entry)
            continue
        if not isinstance(entry, dict):
            continue
        if entry.get("@type") == "Place" or "address" in entry:
            address = entry.get("address")
            if isinstance(address, str):
                locations.append(address)
            elif isinstance(address, dict):
                parts = [
                    str(address.get(key))
                    for key in (
                        "streetAddress",
                        "addressLocality",
                        "addressRegion",
                        "addressCountry",
                    )
                    if address.get(key)
                ]
                if parts:
                    locations.append(", ".join(parts))
        if entry.get("name"):
            locations.append(str(entry["name"]))
    return locations


class JsonLdAdapter:
    """Adapter that extracts JobPosting entities from JSON-LD in HTML."""

    name: ClassVar[str] = "json_ld"
    supported: ClassVar[bool] = True

    def detect_host(self, hostname: str) -> bool:
        return bool(hostname)

    def extract_tenant(self, url: str) -> str | None:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            return host or None
        return parts[0]

    def build_api_url(self, tenant: str) -> str:
        if tenant.startswith("http://") or tenant.startswith("https://"):
            return tenant
        return f"https://{tenant}"

    def _extract_json_ld_objects(self, html: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        objects: list[dict[str, Any]] = []
        for script in soup.find_all(
            "script",
            attrs={"type": re.compile(r"application/ld\+json", re.I)},
        ):
            raw = script.string or script.get_text()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                continue
            for item in _as_list(parsed):
                if isinstance(item, dict):
                    objects.append(item)
                    graph = item.get("@graph")
                    if isinstance(graph, list):
                        objects.extend(node for node in graph if isinstance(node, dict))
        return objects

    def _is_job_posting(self, node: dict[str, Any]) -> bool:
        node_type = node.get("@type")
        if isinstance(node_type, str):
            return node_type.casefold() == JOB_POSTING_TYPE.casefold()
        if isinstance(node_type, list):
            return any(
                isinstance(value, str) and value.casefold() == JOB_POSTING_TYPE.casefold()
                for value in node_type
            )
        return False

    def _identifier(self, node: dict[str, Any], fallback_url: str) -> str:
        identifier = node.get("identifier")
        if isinstance(identifier, dict) and identifier.get("value"):
            return str(identifier["value"])
        if identifier:
            return str(identifier)
        if node.get("url"):
            return str(node["url"])
        return fallback_url

    def parse_html(self, html: str, source: Source, *, page_url: str | None = None) -> list[RawJob]:
        base_url = page_url or source.careers_url
        objects = self._extract_json_ld_objects(html)
        jobs: list[RawJob] = []
        for node in objects:
            if not self._is_job_posting(node):
                continue
            job = self._parse_job(node, source, base_url=base_url)
            if job is not None:
                jobs.append(job)
        return jobs

    def parse_payload(self, payload: Any, source: Source) -> list[RawJob]:
        if isinstance(payload, bytes):
            html = payload.decode("utf-8", errors="replace")
        elif isinstance(payload, str):
            html = payload
        elif isinstance(payload, dict) and "html" in payload:
            html = str(payload["html"])
        else:
            return []
        page_url = None
        if isinstance(payload, dict):
            page_url = payload.get("page_url")
        return self.parse_html(html, source, page_url=page_url)

    def _parse_job(
        self,
        node: dict[str, Any],
        source: Source,
        *,
        base_url: str,
    ) -> RawJob | None:
        title = node.get("title")
        if not title:
            return None

        job_url = node.get("url") or base_url
        job_url = urljoin(base_url, str(job_url))
        raw_apply = node.get("directApply")
        apply_url = (
            job_url
            if isinstance(raw_apply, bool) or not raw_apply
            else urljoin(base_url, str(raw_apply))
        )

        description = _strip_html(node.get("description"))
        employment_type = node.get("employmentType")
        if isinstance(employment_type, list):
            employment_type = employment_type[0] if employment_type else None

        hiring_org = node.get("hiringOrganization")
        department = None
        if isinstance(hiring_org, dict):
            department = hiring_org.get("name")

        identifier = self._identifier(node, job_url)
        locations = _location_strings(node.get("jobLocation"))

        return RawJob(
            source_job_id=identifier,
            title=str(title).strip(),
            job_url=job_url,
            apply_url=str(apply_url),
            locations_raw=locations,
            description_text=description,
            summary=(description[:1000] if description else None),
            employment_type=str(employment_type) if employment_type else None,
            department=str(department) if department else None,
            posted_at=_parse_datetime(node.get("datePosted")),
            application_deadline=_parse_datetime(node.get("validThrough")),
            metadata={
                "json_ld_identifier": node.get("identifier"),
                "company_name": source.company_name,
            },
        )

    async def fetch_jobs(self, source: Source, client: SafeHTTPClient) -> AdapterFetchResult:
        page_url = source.careers_url
        response = await client.get(
            page_url,
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
                message=f"JSON-LD page returned HTTP {response.status_code}",
            )

        jobs = self.parse_html(response.text, source, page_url=response.url)
        return AdapterFetchResult(
            jobs=jobs,
            etag=response.etag,
            last_modified=response.last_modified,
            metadata={"job_count": len(jobs)},
        )


json_ld_adapter = register_adapter(JsonLdAdapter())
