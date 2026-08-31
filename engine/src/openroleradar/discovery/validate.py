"""Candidate validation, confidence scoring, and quarantine."""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from openroleradar.config import ProjectConfig, config_dir, load_project_config, load_yaml
from openroleradar.discovery.ats_detect import detect_ats
from openroleradar.discovery.registry import deterministic_id


@dataclass
class ValidationResult:
    """Outcome of validating a discovery candidate."""

    accepted: bool
    confidence: float
    reason: str
    source_id: str | None = None
    company_domain: str | None = None
    adapter: str | None = None
    tenant: str | None = None
    careers_url: str | None = None
    quarantine: bool = False
    issues: list[str] = field(default_factory=list)

    def to_quarantine_record(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "company_domain": self.company_domain,
            "adapter": self.adapter,
            "tenant": self.tenant,
            "careers_url": self.careers_url,
            "confidence": self.confidence,
            "reason": self.reason,
            "issues": self.issues,
            "quarantined_at": datetime.now(UTC).isoformat(),
        }


def load_aggregator_denylist(root: Path | None = None) -> set[str]:
    path = config_dir(root) / "aggregators-denylist.yml"
    data = load_yaml(path)
    if not isinstance(data, dict):
        return set()
    domains = data.get("domains", [])
    if not isinstance(domains, list):
        return set()
    return {str(domain).lower().strip() for domain in domains}


def _is_private_ip(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return True
    return False


def _domain_allowed(domain: str, denylist: set[str]) -> bool:
    domain = domain.lower()
    return all(not (domain == blocked or domain.endswith(f".{blocked}")) for blocked in denylist)


def score_candidate(
    *,
    url: str,
    platform: str | None = None,
    tenant: str | None = None,
    base_confidence: float = 0.5,
    has_json_ld: bool = False,
    is_seed: bool = False,
) -> float:
    """Compute a normalized confidence score for a discovery candidate."""
    score = base_confidence
    if is_seed:
        return 1.0
    if platform and tenant:
        score = max(score, 0.8)
    elif platform:
        score = max(score, 0.65)
    if has_json_ld:
        score = max(score, 0.7)
    parsed = urlparse(url)
    if parsed.scheme == "https":
        score += 0.05
    return min(1.0, round(score, 3))


def validate_candidate(
    *,
    url: str,
    company_domain: str | None = None,
    platform: str | None = None,
    tenant: str | None = None,
    base_confidence: float = 0.5,
    has_json_ld: bool = False,
    is_seed: bool = False,
    config: ProjectConfig | None = None,
    root: Path | None = None,
) -> ValidationResult:
    """Validate a candidate source URL and decide acceptance or quarantine."""
    config = config or load_project_config(root)
    denylist = load_aggregator_denylist(root)
    issues: list[str] = []

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return ValidationResult(
            accepted=False,
            confidence=0.0,
            reason="invalid_scheme",
            careers_url=url,
            quarantine=True,
            issues=["URL must use http or https"],
        )

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return ValidationResult(
            accepted=False,
            confidence=0.0,
            reason="missing_hostname",
            careers_url=url,
            quarantine=True,
            issues=["URL missing hostname"],
        )

    if _is_private_ip(hostname):
        issues.append("hostname resolves to private/reserved address")

    if not _domain_allowed(hostname, denylist):
        return ValidationResult(
            accepted=False,
            confidence=0.0,
            reason="aggregator_denylist",
            company_domain=company_domain or hostname,
            careers_url=url,
            quarantine=True,
            issues=[f"Domain {hostname} is denylisted"],
        )

    detected = detect_ats(url=url)
    adapter = platform or (detected.platform if detected else None)
    resolved_tenant = tenant or (detected.tenant if detected else None)
    resolved_domain = company_domain or hostname

    confidence = score_candidate(
        url=url,
        platform=adapter,
        tenant=resolved_tenant,
        base_confidence=base_confidence,
        has_json_ld=has_json_ld,
        is_seed=is_seed,
    )

    if detected and not detected.supported:
        issues.append(f"ATS platform {detected.platform} is not fully supported")
        confidence = min(confidence, 0.5)

    promotion_min = float(config.discovery.get("promotion_min_confidence", 0.75))
    quarantine_below = float(config.classification.get("quarantine_below_confidence", 0.4))

    source_id = None
    if adapter and resolved_tenant:
        source_id = deterministic_id("source", resolved_domain, adapter, resolved_tenant)

    if confidence < quarantine_below:
        return ValidationResult(
            accepted=False,
            confidence=confidence,
            reason="low_confidence",
            source_id=source_id,
            company_domain=resolved_domain,
            adapter=adapter,
            tenant=resolved_tenant,
            careers_url=url,
            quarantine=True,
            issues=issues or ["Confidence below quarantine threshold"],
        )

    if confidence < promotion_min:
        return ValidationResult(
            accepted=False,
            confidence=confidence,
            reason="below_promotion_threshold",
            source_id=source_id,
            company_domain=resolved_domain,
            adapter=adapter,
            tenant=resolved_tenant,
            careers_url=url,
            quarantine=True,
            issues=issues or ["Confidence below promotion threshold"],
        )

    if issues:
        return ValidationResult(
            accepted=False,
            confidence=confidence,
            reason="validation_warnings",
            source_id=source_id,
            company_domain=resolved_domain,
            adapter=adapter,
            tenant=resolved_tenant,
            careers_url=url,
            quarantine=True,
            issues=issues,
        )

    return ValidationResult(
        accepted=True,
        confidence=confidence,
        reason="accepted",
        source_id=source_id,
        company_domain=resolved_domain,
        adapter=adapter,
        tenant=resolved_tenant,
        careers_url=url,
        quarantine=False,
        issues=[],
    )
