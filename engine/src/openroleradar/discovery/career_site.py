"""Career site inspection for /careers paths, sitemaps, and JSON-LD."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from openroleradar.config import ProjectConfig, load_project_config
from openroleradar.discovery.ats_detect import AtsMatch, detect_ats


@dataclass
class CareerSiteInspection:
    """Results from inspecting a company career site."""

    domain: str
    careers_urls: list[str] = field(default_factory=list)
    sitemap_urls: list[str] = field(default_factory=list)
    has_json_ld_jobs: bool = False
    ats_match: AtsMatch | None = None
    confidence: float = 0.0
    errors: list[str] = field(default_factory=list)


CAREER_PATHS = (
    "/careers",
    "/jobs",
    "/join-us",
    "/work-with-us",
    "/company/careers",
)


class CareerSiteInspector:
    """Probe company domains for career pages and ATS signals."""

    def __init__(
        self,
        *,
        config: ProjectConfig | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.config = config or load_project_config()
        timeout = float(self.config.http.get("timeout_seconds", 30))
        self._client = client
        self._owns_client = client is None
        self._timeout = timeout

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=httpx.Timeout(self._timeout, connect=10.0),
                follow_redirects=True,
                headers={"User-Agent": self.config.user_agent},
            )
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> CareerSiteInspector:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _fetch(self, url: str) -> tuple[str | None, str | None]:
        try:
            response = self._get_client().get(url)
            if response.status_code >= 400:
                return None, f"HTTP {response.status_code} for {url}"
            return response.text, None
        except httpx.HTTPError as exc:
            return None, str(exc)

    @staticmethod
    def _has_job_posting_json_ld(html: str) -> bool:
        soup = BeautifulSoup(html, "lxml")
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = script.string or script.get_text()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    continue
                schema_type = item.get("@type", "")
                if isinstance(schema_type, list):
                    types = {str(value).lower() for value in schema_type}
                else:
                    types = {str(schema_type).lower()}
                if "jobposting" in types:
                    return True
        return False

    def _extract_sitemap_urls(self, domain: str) -> list[str]:
        candidates = [
            f"https://{domain}/sitemap.xml",
            f"https://{domain}/sitemap_index.xml",
            f"https://www.{domain}/sitemap.xml",
        ]
        found: list[str] = []
        for url in candidates:
            html, _ = self._fetch(url)
            if not html:
                continue
            locs = re.findall(r"<loc>([^<]+)</loc>", html, flags=re.IGNORECASE)
            career_locs = [
                loc
                for loc in locs
                if any(token in loc.lower() for token in ("career", "job", "join"))
            ]
            found.extend(career_locs[:10])
        return list(dict.fromkeys(found))

    def inspect(self, domain: str) -> CareerSiteInspection:
        """Inspect a domain for career-related endpoints and ATS signals."""
        domain = domain.lower().strip()
        result = CareerSiteInspection(domain=domain)
        best_confidence = 0.0
        best_match: AtsMatch | None = None

        for path in CAREER_PATHS:
            url = f"https://{domain}{path}"
            html, error = self._fetch(url)
            if error:
                result.errors.append(error)
                continue
            if html:
                result.careers_urls.append(url)
                if self._has_job_posting_json_ld(html):
                    result.has_json_ld_jobs = True
                    best_confidence = max(best_confidence, 0.65)
                match = detect_ats(url=url, html=html)
                if match and match.confidence > best_confidence:
                    best_match = match
                    best_confidence = match.confidence

        result.sitemap_urls = self._extract_sitemap_urls(domain)
        for sitemap_url in result.sitemap_urls[:5]:
            html, _ = self._fetch(sitemap_url)
            if not html:
                continue
            result.careers_urls.append(sitemap_url)
            match = detect_ats(url=sitemap_url, html=html)
            if match and match.confidence > best_confidence:
                best_match = match
                best_confidence = match.confidence

        if result.has_json_ld_jobs and best_match is None:
            best_match = AtsMatch(platform="json_ld", tenant=None, confidence=0.65)

        result.ats_match = best_match
        result.confidence = best_confidence
        if result.careers_urls:
            result.confidence = max(result.confidence, 0.5)
        result.careers_urls = list(dict.fromkeys(result.careers_urls))
        return result

    def resolve_careers_url(self, domain: str) -> str | None:
        """Return the best careers URL for a domain, if found."""
        inspection = self.inspect(domain)
        if inspection.ats_match and inspection.ats_match.careers_url:
            return inspection.ats_match.careers_url
        return inspection.careers_urls[0] if inspection.careers_urls else None

    @staticmethod
    def normalize_domain(url: str) -> str:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host = parsed.hostname or ""
        return host.lower().removeprefix("www.")

    @staticmethod
    def absolutize(base: str, href: str) -> str:
        return urljoin(base, href)
