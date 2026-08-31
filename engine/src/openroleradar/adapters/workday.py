"""Workday ATS detection adapter with graceful unsupported status."""

from __future__ import annotations

from typing import ClassVar
from urllib.parse import urlparse

from openroleradar.adapters.base import AdapterFetchResult, register_adapter
from openroleradar.http.client import SafeHTTPClient
from openroleradar.models.job import RawJob, Source

WORKDAY_HOST_SUFFIXES = (
    "myworkdayjobs.com",
    "myworkdaysite.com",
)


class WorkdayAdapter:
    """Detect Workday career sites and report unsupported status."""

    name: ClassVar[str] = "workday"
    supported: ClassVar[bool] = False

    def detect_host(self, hostname: str) -> bool:
        host = hostname.lower().rstrip(".")
        return any(
            host == suffix or host.endswith(f".{suffix}") for suffix in WORKDAY_HOST_SUFFIXES
        )

    def extract_tenant(self, url: str) -> str | None:
        parsed = urlparse(url)
        if not self.detect_host(parsed.hostname or ""):
            return None
        parts = [part for part in parsed.path.split("/") if part]
        return parts[0] if parts else parsed.hostname

    def build_api_url(self, tenant: str) -> str:
        return f"https://{tenant}.wd5.myworkdayjobs.com/"

    def parse_payload(self, payload: object, source: Source) -> list[RawJob]:
        return []

    async def fetch_jobs(self, source: Source, client: SafeHTTPClient) -> AdapterFetchResult:
        return AdapterFetchResult(
            jobs=[],
            status="unsupported",
            message=(
                "Workday career sites require tenant-specific integration and are not "
                "supported by the public adapter yet."
            ),
            metadata={
                "tenant": source.adapter_tenant,
                "careers_url": source.careers_url,
            },
        )


workday_adapter = register_adapter(WorkdayAdapter())
