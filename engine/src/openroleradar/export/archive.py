"""Monthly archive exporter for historical snapshots."""

from __future__ import annotations

import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import orjson
import zstandard as zstd

from openroleradar.config import ProjectConfig, load_project_config
from openroleradar.models.state import LiveState
from openroleradar.storage.serialize import serialize_state


@dataclass(frozen=True)
class ArchiveArtifact:
    """Metadata for a generated monthly archive."""

    month: str
    path: Path
    job_count: int
    company_count: int
    byte_size: int


class ArchiveExporter:
    """Export monthly compressed archives of live state."""

    def __init__(self, config: ProjectConfig | None = None) -> None:
        self.config = config or load_project_config()
        self.prefix = str(self.config.archive.get("prefix", "dataset"))

    @staticmethod
    def month_key(when: datetime | None = None) -> str:
        timestamp = when or datetime.now(UTC)
        return timestamp.strftime("%Y-%m")

    def _build_archive_bytes(self, state: LiveState, month: str) -> bytes:
        state_bytes = serialize_state(state)
        summary: dict[str, Any] = {
            "month": month,
            "generated_at": state.generated_at.isoformat(),
            "job_count": len(state.jobs),
            "company_count": len(state.companies),
            "source_count": len(state.sources),
            "schema_version": state.schema_version,
        }
        summary_bytes = orjson.dumps(summary, option=orjson.OPT_INDENT_2)

        buffer = BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as archive:
            for name, payload in (
                ("state.json", state_bytes),
                ("summary.json", summary_bytes),
            ):
                info = tarfile.TarInfo(name=name)
                info.size = len(payload)
                archive.addfile(info, BytesIO(payload))
        tar_bytes = buffer.getvalue()
        return zstd.ZstdCompressor(level=5).compress(tar_bytes)

    def export(
        self, state: LiveState, output_dir: Path, *, month: str | None = None
    ) -> ArchiveArtifact:
        """Write a monthly archive file and return artifact metadata."""
        month = month or self.month_key(state.generated_at)
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{self.prefix}-{month}.tar.zst"
        path = output_dir / filename
        compressed = self._build_archive_bytes(state, month)
        path.write_bytes(compressed)
        return ArchiveArtifact(
            month=month,
            path=path,
            job_count=len(state.jobs),
            company_count=len(state.companies),
            byte_size=len(compressed),
        )

    def list_archives(self, output_dir: Path) -> list[ArchiveArtifact]:
        """List existing archive artifacts in a directory."""
        artifacts: list[ArchiveArtifact] = []
        pattern = f"{self.prefix}-*.tar.zst"
        for path in sorted(output_dir.glob(pattern)):
            month = path.stem.removeprefix(f"{self.prefix}-").removesuffix(".tar")
            artifacts.append(
                ArchiveArtifact(
                    month=month,
                    path=path,
                    job_count=0,
                    company_count=0,
                    byte_size=path.stat().st_size,
                )
            )
        return artifacts
