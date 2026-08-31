#!/usr/bin/env python3
"""Validate config/sources.yml for structure, SSRF safety, and policy compliance."""

from __future__ import annotations

import re
import socket
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config"
SOURCES_PATH = CONFIG_DIR / "sources.yml"
DENYLIST_PATH = CONFIG_DIR / "aggregators-denylist.yml"
ATS_HOSTS_PATH = CONFIG_DIR / "ats-hosts.yml"

SUPPORTED_ADAPTERS = {
    "greenhouse",
    "lever",
    "ashby",
    "smartrecruiters",
    "workday",
    "json_ld",
}

DOMAIN_RE = re.compile(
    r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$"
)
TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def _fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def _warn(message: str) -> None:
    print(f"WARN: {message}", file=sys.stderr)


def load_yaml(path: Path) -> Any:
    if not path.exists():
        _fail(f"Missing required file: {path}")
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_denylist() -> set[str]:
    data = load_yaml(DENYLIST_PATH)
    if not isinstance(data, dict):
        _fail("aggregators-denylist.yml must be a mapping with a domains list")
    domains = data.get("domains", [])
    if not isinstance(domains, list):
        _fail("aggregators-denylist.yml domains must be a list")
    return {str(domain).lower().strip() for domain in domains}


def domain_denied(domain: str, denylist: set[str]) -> bool:
    domain = domain.lower()
    for blocked in denylist:
        if domain == blocked or domain.endswith(f".{blocked}"):
            return True
    return False


def resolves_to_private(hostname: str) -> bool:
    """Best-effort SSRF guard; skipped quietly when DNS is unavailable."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        _warn(f"Could not resolve {hostname}; skipping private-IP check")
        return False
    import ipaddress

    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        try:
            ip = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return True
    return False


def deterministic_id(*parts: str, length: int = 16) -> str:
    import hashlib

    payload = "|".join(part.strip().lower() for part in parts if part)
    return hashlib.sha256(payload.encode()).hexdigest()[:length]


def validate_entry(
    entry: dict[str, Any],
    index: int,
    denylist: set[str],
    seen_source_ids: set[str],
) -> None:
    prefix = f"Entry #{index + 1}"
    company = str(entry.get("company", "")).strip()
    domain = str(entry.get("domain", "")).strip().lower()
    adapter = str(entry.get("adapter", "")).strip().lower()
    tenant = str(entry.get("tenant", "")).strip().lower()

    if not company:
        _fail(f"{prefix}: missing company name")
    if not domain or not DOMAIN_RE.match(domain):
        _fail(f"{prefix}: invalid domain '{domain}'")
    if adapter not in SUPPORTED_ADAPTERS:
        _fail(f"{prefix}: unsupported adapter '{adapter}'")
    if not tenant or not TENANT_RE.match(tenant):
        _fail(f"{prefix}: invalid tenant '{tenant}'")

    if domain_denied(domain, denylist):
        _fail(f"{prefix}: domain '{domain}' is on the aggregator denylist")

    careers_url = f"https://{domain}/careers"
    parsed = urlparse(careers_url)
    hostname = parsed.hostname or domain
    if resolves_to_private(hostname):
        _fail(f"{prefix}: domain '{hostname}' resolves to a private/reserved address")

    source_id = deterministic_id("source", domain, adapter, tenant)
    if source_id in seen_source_ids:
        _fail(f"{prefix}: duplicate source_id {source_id} for {company}")
    seen_source_ids.add(source_id)

    print(f"OK  {company} ({domain}) -> {adapter}/{tenant} [{source_id}]")


def main() -> None:
    print(f"Validating {SOURCES_PATH.relative_to(REPO_ROOT)}")
    denylist = load_denylist()
    raw = load_yaml(SOURCES_PATH)

    if not isinstance(raw, list):
        _fail("sources.yml must contain a YAML list of seed entries")
    if not raw:
        _fail("sources.yml must contain at least one seed entry")

    seen_source_ids: set[str] = set()
    count = 0
    for index, entry in enumerate(raw):
        if entry is None:
            continue
        if not isinstance(entry, dict):
            _fail(f"Entry #{index + 1} must be a mapping")
        validate_entry(entry, index, denylist, seen_source_ids)
        count += 1

    print(f"\nValidated {count} seed source(s).")
    print("No SSRF, denylist, or duplicate issues detected.")


if __name__ == "__main__":
    main()
