"""README statistics section generator with GENERATED_STATS markers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path

from openroleradar.config import ProjectConfig, load_project_config
from openroleradar.models.state import LiveState

START_MARKER = "<!-- GENERATED_STATS:START -->"
END_MARKER = "<!-- GENERATED_STATS:END -->"


@dataclass(frozen=True)
class ReadmeStats:
    """Computed statistics for README rendering."""

    generated_at: str
    open_jobs: int
    total_jobs: int
    companies: int
    sources: int
    healthy_sources: int
    adapters: int


class ReadmeGenerator:
    """Inject or replace auto-generated README statistics."""

    def __init__(self, config: ProjectConfig | None = None) -> None:
        self.config = config or load_project_config()

    def compute_stats(self, state: LiveState) -> ReadmeStats:
        open_jobs = sum(
            1 for job in state.jobs.values() if job.lifecycle.value in {"open", "reopened"}
        )
        healthy_sources = sum(
            1 for source in state.sources.values() if source.health_status == "healthy"
        )
        adapters = len({source.adapter for source in state.sources.values()})
        return ReadmeStats(
            generated_at=state.generated_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC"),
            open_jobs=open_jobs,
            total_jobs=len(state.jobs),
            companies=len(state.companies),
            sources=len(state.sources),
            healthy_sources=healthy_sources,
            adapters=adapters,
        )

    def render_section(self, state: LiveState) -> str:
        stats = self.compute_stats(state)
        return (
            f"{START_MARKER}\n"
            f"## Live Statistics\n\n"
            f"_Last updated: {stats.generated_at}_\n\n"
            f"| Metric | Count |\n"
            f"| --- | ---: |\n"
            f"| Open roles | {stats.open_jobs:,} |\n"
            f"| Total tracked roles | {stats.total_jobs:,} |\n"
            f"| Companies | {stats.companies:,} |\n"
            f"| Sources | {stats.sources:,} |\n"
            f"| Healthy sources | {stats.healthy_sources:,} |\n"
            f"| ATS adapters | {stats.adapters:,} |\n\n"
            f"Published by [{self.config.display_name}]({self.config.website_url}).\n"
            f"{END_MARKER}"
        )

    def update_readme(self, readme_path: Path, state: LiveState) -> str:
        """Replace or append the generated stats block in a README file."""
        section = self.render_section(state)
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
        else:
            content = f"# {self.config.display_name}\n\n"

        pattern = re.compile(
            re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
            flags=re.DOTALL,
        )
        if pattern.search(content):
            updated = pattern.sub(section, content)
        else:
            updated = content.rstrip() + "\n\n" + section + "\n"
        readme_path.write_text(updated, encoding="utf-8")
        return updated

    @staticmethod
    def extract_section(content: str) -> str | None:
        pattern = re.compile(
            re.escape(START_MARKER) + r"(.*?)" + re.escape(END_MARKER),
            flags=re.DOTALL,
        )
        match = pattern.search(content)
        return match.group(1).strip() if match else None
