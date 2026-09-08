"""RSS, Atom, and JSON feed generation."""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import format_datetime
from pathlib import Path
from typing import cast
from xml.etree.ElementTree import Element, SubElement, tostring

import orjson

from openroleradar.config import ProjectConfig, load_project_config
from openroleradar.export.public_filter import is_public_job
from openroleradar.models.job import Job
from openroleradar.models.state import LiveState


@dataclass(frozen=True)
class FeedArtifact:
    """Metadata for a generated feed file."""

    format: str
    path: Path
    item_count: int


class FeedGenerator:
    """Generate syndication feeds from live state."""

    def __init__(self, config: ProjectConfig | None = None) -> None:
        self.config = config or load_project_config()
        self.max_items = int(self.config.feeds.get("max_items", 500))

    def _select_jobs(self, state: LiveState) -> list[Job]:
        jobs = [job for job in state.jobs.values() if is_public_job(job)]
        jobs.sort(key=lambda job: job.first_seen_at, reverse=True)
        return jobs[: self.max_items]

    def _format_dt(self, when: datetime) -> str:
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        return format_datetime(when.astimezone(UTC))

    def generate_json(self, state: LiveState) -> bytes:
        jobs = self._select_jobs(state)
        payload = {
            "version": "https://jsonfeed.org/version/1.1",
            "title": f"{self.config.display_name} — Early-Career Roles",
            "home_page_url": self.config.website_url,
            "feed_url": f"{self.config.website_url.rstrip('/')}/feeds/jobs.json",
            "description": self.config.tagline or self.config.description,
            "items": [
                {
                    "id": job.job_id,
                    "url": job.job_url,
                    "title": job.title,
                    "content_text": job.summary,
                    "date_published": job.first_seen_at.isoformat(),
                    "authors": [{"name": job.company_name}],
                }
                for job in jobs
            ],
        }
        return orjson.dumps(payload, option=orjson.OPT_INDENT_2)

    def generate_atom(self, state: LiveState) -> bytes:
        jobs = self._select_jobs(state)
        feed = Element(
            "feed",
            xmlns="http://www.w3.org/2005/Atom",
        )
        SubElement(feed, "title").text = f"{self.config.display_name} Jobs"
        SubElement(feed, "link", href=self.config.website_url)
        SubElement(feed, "id").text = self.config.website_url
        SubElement(feed, "updated").text = self._format_dt(state.generated_at)

        for job in jobs:
            entry = SubElement(feed, "entry")
            SubElement(entry, "title").text = job.title
            SubElement(entry, "link", href=job.job_url)
            SubElement(entry, "id").text = job.job_id
            SubElement(entry, "updated").text = self._format_dt(job.last_seen_at)
            SubElement(entry, "summary").text = job.summary or ""
            author = SubElement(entry, "author")
            SubElement(author, "name").text = job.company_name

        body = cast(bytes, tostring(feed, encoding="utf-8"))
        return b'<?xml version="1.0" encoding="utf-8"?>\n' + body

    def generate_rss(self, state: LiveState) -> bytes:
        jobs = self._select_jobs(state)
        rss = Element("rss", version="2.0")
        channel = SubElement(rss, "channel")
        SubElement(channel, "title").text = f"{self.config.display_name} Jobs"
        SubElement(channel, "link").text = self.config.website_url
        SubElement(channel, "description").text = self.config.tagline or self.config.description
        SubElement(channel, "lastBuildDate").text = self._format_dt(state.generated_at)

        for job in jobs:
            item = SubElement(channel, "item")
            SubElement(item, "title").text = job.title
            SubElement(item, "link").text = job.job_url
            SubElement(item, "guid", isPermaLink="false").text = job.job_id
            SubElement(item, "pubDate").text = self._format_dt(job.first_seen_at)
            if job.summary:
                SubElement(item, "description").text = html.escape(job.summary)

        body = cast(bytes, tostring(rss, encoding="utf-8"))
        return b'<?xml version="1.0" encoding="utf-8"?>\n' + body

    def write_all(self, state: LiveState, output_dir: Path) -> list[FeedArtifact]:
        """Write JSON, Atom, and RSS feeds to the output directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        jobs = self._select_jobs(state)
        artifacts = [
            FeedArtifact("json", output_dir / "jobs.json", len(jobs)),
            FeedArtifact("atom", output_dir / "jobs.atom", len(jobs)),
            FeedArtifact("rss", output_dir / "jobs.rss", len(jobs)),
        ]
        (output_dir / "jobs.json").write_bytes(self.generate_json(state))
        (output_dir / "jobs.atom").write_bytes(self.generate_atom(state))
        (output_dir / "jobs.rss").write_bytes(self.generate_rss(state))
        return artifacts
