"""ATS adapter protocol, shared types, and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Protocol, runtime_checkable

from openroleradar.http.client import SafeHTTPClient
from openroleradar.models.job import RawJob, Source


@dataclass(slots=True)
class AdapterFetchResult:
    """Outcome of an adapter fetch operation."""

    jobs: list[RawJob] = field(default_factory=list)
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False
    status: str = "ok"
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ATSAdapter(Protocol):
    """Protocol implemented by all ATS source adapters."""

    name: ClassVar[str]
    supported: ClassVar[bool]

    def detect_host(self, hostname: str) -> bool:
        """Return True when the hostname belongs to this ATS."""

    def extract_tenant(self, url: str) -> str | None:
        """Extract tenant slug from a careers board URL."""

    def build_api_url(self, tenant: str) -> str:
        """Build the API endpoint for a tenant."""

    def parse_payload(self, payload: Any, source: Source) -> list[RawJob]:
        """Parse a fetched payload into normalized raw jobs."""

    async def fetch_jobs(self, source: Source, client: SafeHTTPClient) -> AdapterFetchResult:
        """Fetch and parse jobs for a configured source."""


_ADAPTER_REGISTRY: dict[str, ATSAdapter] = {}


def register_adapter(adapter: ATSAdapter) -> ATSAdapter:
    """Register an adapter instance by name."""
    _ADAPTER_REGISTRY[adapter.name] = adapter
    return adapter


def get_adapter(name: str) -> ATSAdapter:
    """Return a registered adapter by name."""
    try:
        return _ADAPTER_REGISTRY[name]
    except KeyError as exc:
        known = ", ".join(sorted(_ADAPTER_REGISTRY)) or "(none)"
        raise KeyError(f"Unknown adapter '{name}'. Known adapters: {known}") from exc


def list_adapters() -> list[str]:
    """Return registered adapter names."""
    return sorted(_ADAPTER_REGISTRY)


def clear_adapter_registry() -> None:
    """Clear registry — intended for tests."""
    _ADAPTER_REGISTRY.clear()
