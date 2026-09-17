"""SimplifyJobs / SWE List public listings adapter.

SWE List emails are alerts for the public SimplifyJobs GitHub repos. We fetch
their ``listings.json`` feeds and keep only active roles whose apply URLs point
at first-party / ATS boards (not LinkedIn/Indeed/etc.).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, ClassVar
from urllib.parse import urlparse

import orjson

from openroleradar.adapters.base import AdapterFetchResult, register_adapter
from openroleradar.http.client import SafeHTTPClient
from openroleradar.models.job import RawJob, Source
from openroleradar.security.first_party import is_denied_url

# Tenant slug -> raw GitHub listings.json
FEED_URLS: dict[str, str] = {
    "summer2026-internships": (
        "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/"
        "dev/.github/scripts/listings.json"
    ),
    "summer2027-internships": (
        "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/"
        "dev/.github/scripts/listings.json"
    ),
    "new-grad-positions": (
        "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/"
        "dev/.github/scripts/listings.json"
    ),
}

CS_CATEGORIES = frozenset(
    {
        "software",
        "software engineering",
        "ai/ml/data",
        "data science, ai & machine learning",
        "quant",
        "hardware",
        "hardware engineering",
        "product",
        "product management",
    }
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_ATS_HOST = re.compile(
    r"greenhouse|lever\.co|ashbyhq|myworkdayjobs|workdayjobs|workable\.com|"
    r"smartrecruiters|icims\.com|ultipro|successfactors|taleo|jobvite|"
    r"bamboohr|recruitee|comeet|myworkday\.com|oraclecloud\.com",
    re.I,
)


def _slugify(value: str) -> str:
    return _SLUG_RE.sub("-", value.strip().lower()).strip("-") or "unknown"


def _parse_unix(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return None
    # Guard against millisecond stamps.
    if seconds > 10_000_000_000:
        seconds //= 1000
    return datetime.fromtimestamp(seconds, tz=UTC)


def company_domain_from_listing(company_name: str, apply_url: str) -> str:
    """Best-effort domain for company records created from a listing."""
    try:
        host = (urlparse(apply_url).hostname or "").lower().removeprefix("www.")
    except Exception:
        host = ""
    if host and not _ATS_HOST.search(host) and "simplify" not in host:
        return host
    return f"{_slugify(company_name)}.com"


def is_cs_category(category: str | None) -> bool:
    if not category:
        return True
    return category.strip().lower() in CS_CATEGORIES


class SimplifyAdapter:
    """Adapter for SimplifyJobs public internship / new-grad listing feeds."""

    name: ClassVar[str] = "simplify"
    supported: ClassVar[bool] = True

    def detect_host(self, hostname: str) -> bool:
        host = hostname.lower().rstrip(".")
        return host in {"raw.githubusercontent.com", "cdn.jsdelivr.net"} or "simplifyjobs" in host

    def extract_tenant(self, url: str) -> str | None:
        lower = url.lower()
        for tenant in FEED_URLS:
            if tenant in lower:
                return tenant
        return None

    def build_api_url(self, tenant: str) -> str:
        key = tenant.strip().lower()
        if key not in FEED_URLS:
            raise ValueError(f"Unknown Simplify feed tenant: {tenant}")
        return FEED_URLS[key]

    def parse_payload(self, payload: Any, source: Source) -> list[RawJob]:
        data = orjson.loads(payload) if isinstance(payload, (bytes, str)) else payload
        if not isinstance(data, list):
            return []

        career_hint = (
            "new_grad"
            if "new-grad" in source.adapter_tenant.lower()
            else "internship"
        )

        jobs: list[RawJob] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            job = self._parse_listing(item, source, career_hint=career_hint)
            if job is not None:
                jobs.append(job)
        return jobs

    def _parse_listing(
        self,
        item: dict[str, Any],
        source: Source,
        *,
        career_hint: str,
    ) -> RawJob | None:
        if item.get("active") is False:
            return None
        if item.get("is_visible") is False:
            return None

        listing_id = item.get("id")
        title = item.get("title")
        company_name = item.get("company_name")
        apply_url = item.get("url")
        if not listing_id or not title or not company_name or not apply_url:
            return None

        apply_url = str(apply_url).strip()
        if not apply_url.startswith("http"):
            return None
        if is_denied_url(apply_url):
            return None
        if "simplify.jobs" in apply_url.lower() or "swelist.com" in apply_url.lower():
            return None
        if not is_cs_category(str(item.get("category") or "")):
            return None

        locations = [
            str(loc).strip()
            for loc in (item.get("locations") or [])
            if isinstance(loc, str) and loc.strip()
        ]
        terms = [
            str(term).strip()
            for term in (item.get("terms") or [])
            if isinstance(term, str) and term.strip()
        ]
        sponsorship = item.get("sponsorship") if isinstance(item.get("sponsorship"), str) else None
        category = item.get("category") if isinstance(item.get("category"), str) else None
        posted_at = _parse_unix(item.get("date_posted"))
        updated_at = _parse_unix(item.get("date_updated"))

        summary_bits = [str(title).strip(), str(company_name).strip()]
        if category:
            summary_bits.append(category)
        if terms:
            summary_bits.append(" · ".join(terms))
        if sponsorship and sponsorship.lower() not in {"other", "n/a", "na", ""}:
            summary_bits.append(sponsorship)

        return RawJob(
            source_job_id=str(listing_id),
            title=str(title).strip(),
            job_url=apply_url,
            apply_url=apply_url,
            locations_raw=locations,
            summary=" — ".join(summary_bits),
            description_text=None,
            employment_type="Internship" if career_hint == "internship" else "Full-time",
            department=category,
            posted_at=posted_at,
            updated_at=updated_at,
            metadata={
                "company_name": str(company_name).strip(),
                "company_domain": company_domain_from_listing(str(company_name), apply_url),
                "simplify_feed": source.adapter_tenant,
                "simplify_category": category,
                "simplify_terms": terms,
                "simplify_sponsorship": sponsorship,
                "simplify_source": item.get("source"),
                "experience_level": (
                    "Internship" if career_hint == "internship" else "New Grad"
                ),
            },
        )

    async def fetch_jobs(self, source: Source, client: SafeHTTPClient) -> AdapterFetchResult:
        try:
            api_url = self.build_api_url(source.adapter_tenant)
        except ValueError as exc:
            return AdapterFetchResult(status="error", message=str(exc))

        headers: dict[str, str] = {"Accept": "application/json"}
        if source.etag:
            headers["If-None-Match"] = source.etag
        if source.last_modified:
            headers["If-Modified-Since"] = source.last_modified

        response = await client.get(api_url, headers=headers)
        if response.is_not_modified:
            return AdapterFetchResult(
                not_modified=True,
                etag=response.etag or source.etag,
                last_modified=response.last_modified or source.last_modified,
            )
        if response.status_code >= 400:
            return AdapterFetchResult(
                status="error",
                message=f"HTTP {response.status_code} fetching Simplify feed",
            )

        jobs = self.parse_payload(response.content, source)
        return AdapterFetchResult(
            jobs=jobs,
            etag=response.etag,
            last_modified=response.last_modified,
            metadata={"count": len(jobs), "feed": source.adapter_tenant},
        )


simplify_adapter = register_adapter(SimplifyAdapter())
