"""GitHub code search for ATS career-board patterns."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from openroleradar.config import ProjectConfig, config_dir, load_project_config, load_yaml
from openroleradar.discovery.ats_detect import detect_ats_from_url

GITHUB_API = "https://api.github.com"


@dataclass(frozen=True)
class GitHubSearchCandidate:
    """A career-board URL discovered via GitHub code search."""

    url: str
    repository: str
    path: str
    platform: str | None
    tenant: str | None
    confidence: float
    discovered_at: datetime


class GitHubRateLimiter:
    """Simple client-side rate limiter using GitHub response headers."""

    def __init__(self) -> None:
        self.remaining: int | None = None
        self.reset_at: float | None = None

    def update_from_headers(self, headers: httpx.Headers) -> None:
        remaining = headers.get("X-RateLimit-Remaining")
        reset = headers.get("X-RateLimit-Reset")
        if remaining is not None:
            self.remaining = int(remaining)
        if reset is not None:
            self.reset_at = float(reset)

    def wait_if_needed(self) -> None:
        if self.remaining is not None and self.remaining > 0:
            return
        if self.reset_at is None:
            return
        sleep_for = max(0.0, self.reset_at - time.time()) + 1.0
        if sleep_for > 0:
            time.sleep(sleep_for)


class GitHubCodeSearch:
    """Search GitHub for ATS URL patterns with rate-limit awareness."""

    def __init__(
        self,
        *,
        token: str | None = None,
        config: ProjectConfig | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.config = config or load_project_config()
        self.token = token
        self._client = client
        self._owns_client = client is None
        self._limiter = GitHubRateLimiter()

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": self.config.user_agent,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                headers=self._headers(),
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> GitHubCodeSearch:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @staticmethod
    def load_discovery_patterns(root: Path | None = None) -> list[str]:
        path = config_dir(root) / "ats-hosts.yml"
        data = load_yaml(path)
        if not isinstance(data, dict):
            return []
        patterns = data.get("discovery_patterns", [])
        if not isinstance(patterns, list):
            return []
        return [str(pattern) for pattern in patterns]

    def search_pattern(self, pattern: str, *, per_page: int = 30) -> list[dict[str, Any]]:
        """Execute a single GitHub code search query."""
        self._limiter.wait_if_needed()
        client = self._get_client()
        response = client.get(
            f"{GITHUB_API}/search/code",
            params={"q": f'"{pattern}" in:file', "per_page": per_page},
        )
        self._limiter.update_from_headers(response.headers)
        if response.status_code == 403:
            self._limiter.wait_if_needed()
            response = client.get(
                f"{GITHUB_API}/search/code",
                params={"q": f'"{pattern}" in:file', "per_page": per_page},
            )
            self._limiter.update_from_headers(response.headers)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return []
        items = payload.get("items", [])
        return items if isinstance(items, list) else []

    def discover(
        self,
        *,
        max_per_run: int | None = None,
        cursor: str | None = None,
    ) -> tuple[list[GitHubSearchCandidate], str | None]:
        """Discover ATS URLs from configured patterns."""
        limit = max_per_run or int(self.config.discovery.get("github_search_per_run", 30))
        patterns = self.load_discovery_patterns()
        if not patterns:
            return [], cursor

        start_index = 0
        if cursor and cursor.startswith("pattern:"):
            try:
                start_index = int(cursor.split(":", 1)[1])
            except ValueError:
                start_index = 0

        candidates: list[GitHubSearchCandidate] = []
        next_cursor: str | None = None
        now = datetime.now(UTC)

        for index, pattern in enumerate(patterns[start_index:], start=start_index):
            if len(candidates) >= limit:
                next_cursor = f"pattern:{index}"
                break
            try:
                items = self.search_pattern(pattern, per_page=min(30, limit - len(candidates)))
            except httpx.HTTPError:
                continue
            for item in items:
                if len(candidates) >= limit:
                    break
                if not isinstance(item, dict):
                    continue
                repo = item.get("repository", {})
                repo_name = repo.get("full_name", "") if isinstance(repo, dict) else ""
                path = str(item.get("path", ""))
                html_url = str(item.get("html_url", ""))
                url = self._extract_url_from_result(pattern, html_url)
                if not url:
                    continue
                detected = detect_ats_from_url(url)
                candidates.append(
                    GitHubSearchCandidate(
                        url=url,
                        repository=str(repo_name),
                        path=path,
                        platform=detected.platform if detected else None,
                        tenant=detected.tenant if detected else None,
                        confidence=detected.confidence if detected else 0.5,
                        discovered_at=now,
                    )
                )
        else:
            next_cursor = None

        return candidates, next_cursor

    @staticmethod
    def _extract_url_from_result(pattern: str, html_url: str) -> str | None:
        if pattern.startswith("http"):
            return f"https://{pattern}" if not pattern.startswith("https://") else pattern
        if "greenhouse.io" in pattern or "lever.co" in pattern or "ashbyhq.com" in pattern:
            tenant_hint = html_url.rsplit("/", 1)[-1].replace(".md", "").replace(".html", "")
            if "greenhouse" in pattern:
                return f"https://boards.greenhouse.io/{tenant_hint}"
            if "lever" in pattern:
                return f"https://jobs.lever.co/{tenant_hint}"
            if "ashby" in pattern:
                return f"https://jobs.ashbyhq.com/{tenant_hint}"
        return f"https://{pattern}"
