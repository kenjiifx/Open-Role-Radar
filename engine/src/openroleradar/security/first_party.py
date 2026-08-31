"""First-party URL validation against aggregator denylist configuration."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

from openroleradar.config import config_dir, load_yaml
from openroleradar.http.url import canonicalize_url, extract_hostname


@dataclass(frozen=True, slots=True)
class DenylistMatch:
    """Details about a denylist hit."""

    reason: str
    matched_value: str


@dataclass(frozen=True, slots=True)
class AggregatorDenylist:
    """Loaded aggregator and mirror domain denylist."""

    domains: frozenset[str]
    patterns: tuple[str, ...]

    def match_domain(self, hostname: str) -> DenylistMatch | None:
        host = hostname.lower().strip().rstrip(".")
        bare = host[4:] if host.startswith("www.") else host

        for candidate in (host, bare, f"www.{bare}"):
            if candidate in self.domains:
                return DenylistMatch(reason="domain", matched_value=candidate)
        return None

    def match_url(self, url: str) -> DenylistMatch | None:
        canonical = canonicalize_url(url)
        parsed = urlparse(canonical)
        host_match = self.match_domain(parsed.hostname or "")
        if host_match is not None:
            return host_match

        lower_url = canonical.lower()
        for pattern in self.patterns:
            if pattern.lower() in lower_url:
                return DenylistMatch(reason="pattern", matched_value=pattern)

        query = parse_qsl(parsed.query, keep_blank_values=True)
        for key, value in query:
            fragment = f"{key}={value}".lower()
            for pattern in self.patterns:
                if pattern.lower() in fragment:
                    return DenylistMatch(reason="pattern", matched_value=pattern)
        return None


def load_aggregator_denylist(root: Path | None = None) -> AggregatorDenylist:
    """Load denylist rules from config/aggregators-denylist.yml."""
    path = config_dir(root) / "aggregators-denylist.yml"
    data = load_yaml(path) or {}
    domains = frozenset(str(domain).lower() for domain in data.get("domains", []))
    patterns = tuple(str(pattern) for pattern in data.get("patterns", []))
    return AggregatorDenylist(domains=domains, patterns=patterns)


@lru_cache(maxsize=1)
def _default_denylist() -> AggregatorDenylist:
    return load_aggregator_denylist()


def is_denied_domain(hostname: str, denylist: AggregatorDenylist | None = None) -> bool:
    """Return True when a hostname matches the aggregator denylist."""
    rules = denylist or _default_denylist()
    return rules.match_domain(hostname) is not None


def is_denied_url(url: str, denylist: AggregatorDenylist | None = None) -> bool:
    """Return True when a URL matches the aggregator denylist."""
    rules = denylist or _default_denylist()
    return rules.match_url(url) is not None


def check_first_party_url(
    url: str,
    denylist: AggregatorDenylist | None = None,
) -> DenylistMatch | None:
    """Return denylist match details when a URL is not first-party."""
    rules = denylist or _default_denylist()
    return rules.match_url(url)


def assert_first_party_url(url: str, denylist: AggregatorDenylist | None = None) -> str:
    """Validate that a URL is first-party; return canonical URL or raise."""
    canonical = canonicalize_url(url)
    match = check_first_party_url(canonical, denylist=denylist)
    if match is not None:
        raise ValueError(
            f"URL blocked by aggregator denylist ({match.reason}): {match.matched_value}"
        )
    if not extract_hostname(canonical):
        raise ValueError(f"URL missing hostname: {canonical}")
    return canonical
