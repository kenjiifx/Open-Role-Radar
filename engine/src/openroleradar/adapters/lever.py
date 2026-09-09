"""Lever ATS adapter."""

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

LEVER_HOSTS = frozenset({"jobs.lever.co", "api.lever.co"})


def _parse_epoch_ms(value: int | float | str | None) -> datetime | None:
    if value is None:
        return None
    try:
        millis = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(millis / 1000, tz=UTC)


class LeverAdapter:
    """Adapter for Lever public postings API."""

    name: ClassVar[str] = "lever"
    supported: ClassVar[bool] = True

    def detect_host(self, hostname: str) -> bool:
        return hostname.lower().rstrip(".") in LEVER_HOSTS

    def extract_tenant(self, url: str) -> str | None:
        parsed = urlparse(url)
        if not self.detect_host(parsed.hostname or ""):
            return None
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            return None
        if parts[0] == "v0" and len(parts) >= 3 and parts[1] == "postings":
            return parts[2]
        return parts[0]

    def build_api_url(self, tenant: str) -> str:
        return build_url(
            "https",
            "api.lever.co",
            f"/v0/postings/{tenant}",
            query={"mode": "json"},
        )

    def parse_payload(self, payload: Any, source: Source) -> list[RawJob]:
        data = orjson.loads(payload) if isinstance(payload, (bytes, str)) else payload

        if not isinstance(data, list):
            return []

        jobs: list[RawJob] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            job = self._parse_job(item, source)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_job(self, item: dict[str, Any], source: Source) -> RawJob | None:
        job_id = item.get("id")
        title = item.get("text")
        hosted_url = item.get("hostedUrl")
        if not job_id or not title or not hosted_url:
            return None

        categories = item.get("categories") if isinstance(item.get("categories"), dict) else {}
        location = categories.get("location") if isinstance(categories, dict) else None
        department = categories.get("department") if isinstance(categories, dict) else None
        commitment = categories.get("commitment") if isinstance(categories, dict) else None

        chunks: list[str] = []
        for key in (
            "descriptionPlain",
            "descriptionBodyPlain",
            "openingPlain",
            "additionalPlain",
            "description",
        ):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                chunks.append(html_to_plaintext(value))
        lists = item.get("lists")
        if isinstance(lists, list):
            for entry in lists:
                if not isinstance(entry, dict):
                    continue
                heading = entry.get("text") if isinstance(entry.get("text"), str) else None
                content = entry.get("content") if isinstance(entry.get("content"), str) else None
                plain = html_to_plaintext("\n".join(part for part in (heading, content) if part))
                if plain:
                    chunks.append(plain)
        # Deduplicate while preserving order.
        seen: set[str] = set()
        ordered: list[str] = []
        for chunk in chunks:
            if chunk and chunk not in seen:
                seen.add(chunk)
                ordered.append(chunk)
        description_text = "\n\n".join(ordered) or None

        apply_url = item.get("applyUrl") or hosted_url

        return RawJob(
            source_job_id=str(job_id),
            title=str(title).strip(),
            job_url=str(hosted_url),
            apply_url=str(apply_url),
            locations_raw=[str(location)] if location else [],
            description_text=description_text,
            summary=None,
            employment_type=str(commitment) if commitment else None,
            department=str(department) if department else None,
            posted_at=_parse_epoch_ms(item.get("createdAt")),
            updated_at=_parse_epoch_ms(item.get("updatedAt")),
            metadata={
                "team": categories.get("team") if isinstance(categories, dict) else None,
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
                message=f"Lever API returned HTTP {response.status_code}",
            )

        try:
            payload = json.loads(response.content)
        except json.JSONDecodeError as exc:
            return AdapterFetchResult(
                status="error",
                message=f"Invalid JSON from Lever API: {exc}",
            )

        jobs = self.parse_payload(payload, source)
        return AdapterFetchResult(
            jobs=jobs,
            etag=response.etag,
            last_modified=response.last_modified,
            metadata={"job_count": len(jobs)},
        )


lever_adapter = register_adapter(LeverAdapter())
