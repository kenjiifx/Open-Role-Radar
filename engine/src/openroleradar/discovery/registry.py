"""Seed source loading from config/sources.yml with deterministic IDs."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from openroleradar.config import config_dir, load_yaml
from openroleradar.models.job import Company, Source


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered)
    return slug.strip("-")


def deterministic_id(*parts: str, length: int = 16) -> str:
    """Derive a stable hex identifier from ordered parts."""
    payload = "|".join(part.strip().lower() for part in parts if part)
    return hashlib.sha256(payload.encode()).hexdigest()[:length]


@dataclass(frozen=True)
class SeedSource:
    """A human-maintained seed entry from sources.yml."""

    company: str
    domain: str
    adapter: str
    tenant: str

    @property
    def company_id(self) -> str:
        return deterministic_id("company", self.domain)

    @property
    def source_id(self) -> str:
        return deterministic_id("source", self.domain, self.adapter, self.tenant)

    @property
    def careers_url(self) -> str:
        return f"https://{self.domain}/careers"


def load_seed_sources(root: Path | None = None) -> list[SeedSource]:
    """Load and validate seed sources from config/sources.yml."""
    path = config_dir(root) / "sources.yml"
    raw = load_yaml(path)
    if not isinstance(raw, list):
        raise ValueError("sources.yml must contain a list of seed entries")

    seeds: list[SeedSource] = []
    seen_ids: set[str] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        company = str(entry.get("company", "")).strip()
        domain = str(entry.get("domain", "")).strip().lower()
        adapter = str(entry.get("adapter", "")).strip().lower()
        tenant = str(entry.get("tenant", "")).strip().lower()
        if not all([company, domain, adapter, tenant]):
            continue
        seed = SeedSource(company=company, domain=domain, adapter=adapter, tenant=tenant)
        if seed.source_id in seen_ids:
            raise ValueError(f"Duplicate source_id derived for {company} ({seed.source_id})")
        seen_ids.add(seed.source_id)
        seeds.append(seed)
    return seeds


def seed_to_company(seed: SeedSource, *, now: datetime | None = None) -> Company:
    """Convert a seed entry into a Company record."""
    timestamp = now or datetime.now(UTC)
    normalized = _slugify(seed.company)
    return Company(
        company_id=seed.company_id,
        name=seed.company,
        normalized_name=normalized,
        canonical_domain=seed.domain,
        careers_urls=[seed.careers_url],
        ats_sources=[seed.adapter],
        first_seen_at=timestamp,
        last_seen_at=timestamp,
    )


def seed_to_source(seed: SeedSource, *, now: datetime | None = None) -> Source:
    """Convert a seed entry into a Source record."""
    timestamp = now or datetime.now(UTC)
    return Source(
        source_id=seed.source_id,
        company_id=seed.company_id,
        company_name=seed.company,
        company_domain=seed.domain,
        careers_url=seed.careers_url,
        adapter=seed.adapter,
        adapter_tenant=seed.tenant,
        discovered_via="seed",
        discovery_confidence=1.0,
        first_discovered_at=timestamp,
        last_validated_at=timestamp,
        health_status="healthy",
        enabled=True,
    )
