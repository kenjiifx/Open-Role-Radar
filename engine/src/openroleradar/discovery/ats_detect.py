"""ATS platform detection from URLs and HTML."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from openroleradar.config import config_dir, load_yaml


@dataclass(frozen=True)
class AtsMatch:
    """Detected ATS platform match."""

    platform: str
    tenant: str | None
    confidence: float
    careers_url: str | None = None
    api_url: str | None = None
    supported: bool = True


def load_ats_hosts(root: Path | None = None) -> dict[str, dict[str, object]]:
    """Load ATS host configuration from config/ats-hosts.yml."""
    path = config_dir(root) / "ats-hosts.yml"
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError("ats-hosts.yml must be a mapping")
    platforms = data.get("platforms", {})
    if not isinstance(platforms, dict):
        raise ValueError("ats-hosts.yml platforms must be a mapping")
    return platforms


def _host_matches(hostname: str, hosts: list[str]) -> bool:
    hostname = hostname.lower()
    return any(hostname == host or hostname.endswith(f".{host}") for host in hosts)


def _extract_tenant_from_path(platform: str, path: str) -> str | None:
    segments = [segment for segment in path.strip("/").split("/") if segment]
    if not segments:
        return None
    if platform in {"greenhouse", "lever", "ashby", "smartrecruiters"}:
        return segments[0].lower()
    if platform == "workable" and len(segments) >= 2 and segments[0] == "api":
        return segments[1].lower()
    return segments[0].lower()


def detect_ats_from_url(
    url: str, platforms: dict[str, dict[str, object]] | None = None
) -> AtsMatch | None:
    """Detect ATS platform from a URL hostname and path."""
    platforms = platforms or load_ats_hosts()
    parsed = urlparse(url)
    if not parsed.hostname:
        return None
    hostname = parsed.hostname.lower()
    for name, config in platforms.items():
        hosts_raw = config.get("hosts", [])
        if not isinstance(hosts_raw, list):
            continue
        hosts = [str(host).lower() for host in hosts_raw]
        if not _host_matches(hostname, hosts):
            continue
        tenant = _extract_tenant_from_path(name, parsed.path)
        supported = config.get("supported", True) is True
        api_pattern = config.get("api_pattern")
        board_pattern = config.get("board_pattern")
        api_url = None
        careers_url = None
        if isinstance(api_pattern, str) and tenant:
            api_url = api_pattern.format(tenant=tenant)
        if isinstance(board_pattern, str) and tenant:
            careers_url = board_pattern.format(tenant=tenant)
        confidence = 0.95 if tenant else 0.7
        return AtsMatch(
            platform=name,
            tenant=tenant,
            confidence=confidence,
            careers_url=careers_url,
            api_url=api_url,
            supported=supported,
        )
    return None


def detect_ats_from_html(html: str, base_url: str | None = None) -> AtsMatch | None:
    """Detect ATS platform from HTML content via embedded URLs and JSON-LD."""
    lowered = html.lower()
    platforms = load_ats_hosts()

    url_pattern = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
    for match in url_pattern.finditer(html):
        candidate = match.group(0).rstrip(".,)")
        detected = detect_ats_from_url(candidate, platforms)
        if detected is not None:
            return detected

    if '"@type"' in lowered and "jobposting" in lowered:
        return AtsMatch(platform="json_ld", tenant=None, confidence=0.6, supported=True)

    if base_url:
        return detect_ats_from_url(base_url, platforms)
    return None


def detect_ats(url: str | None = None, html: str | None = None) -> AtsMatch | None:
    """Detect ATS from URL and/or HTML, preferring URL matches."""
    if url:
        match = detect_ats_from_url(url)
        if match is not None:
            return match
    if html:
        return detect_ats_from_html(html, base_url=url)
    return None
