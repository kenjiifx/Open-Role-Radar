"""GitHub release storage for live-state artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import zstandard as zstd

from openroleradar.config import ProjectConfig, load_project_config
from openroleradar.models.state import LiveState
from openroleradar.storage.local import STATE_JSON_NAME, LocalStateStore
from openroleradar.storage.serialize import deserialize_state, serialize_state

GITHUB_API = "https://api.github.com"


@dataclass(frozen=True)
class ReleaseManifest:
    """Manifest describing a published live-state release."""

    schema_version: int
    generated_at: str
    release_tag: str
    asset_name: str
    checksums_name: str
    job_count: int
    company_count: int
    source_count: int
    state_format_version: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "release_tag": self.release_tag,
            "asset_name": self.asset_name,
            "checksums_name": self.checksums_name,
            "job_count": self.job_count,
            "company_count": self.company_count,
            "source_count": self.source_count,
            "state_format_version": self.state_format_version,
            "sha256": self.sha256,
        }


class GitHubReleaseStore:
    """Load and save LiveState via GitHub releases."""

    def __init__(
        self,
        *,
        token: str | None = None,
        config: ProjectConfig | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.config = config or load_project_config()
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        if not self.config.repository:
            raise ValueError("project.repository must be configured")
        self.owner, self.repo = self.config.repository.split("/", 1)
        self._client = client
        self._owns_client = client is None
        self._local = LocalStateStore(Path.cwd() / ".openroleradar" / "cache")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": self.config.user_agent,
        }

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                headers=self._headers(),
                timeout=httpx.Timeout(60.0, connect=15.0),
            )
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> GitHubReleaseStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @staticmethod
    def bootstrap_empty_state() -> LiveState:
        """Create a fresh empty LiveState ready for first publication."""
        return LiveState(
            schema_version=1,
            generated_at=datetime.now(UTC),
            metadata={"bootstrapped": True},
        )

    def _release_url(self, tag: str | None = None) -> str:
        tag = tag or self.config.live_state.release_tag
        encoded = quote(tag, safe="")
        return f"{GITHUB_API}/repos/{self.owner}/{self.repo}/releases/tags/{encoded}"

    def _get_release(self, tag: str | None = None) -> dict[str, Any] | None:
        client = self._get_client()
        response = client.get(self._release_url(tag))
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected GitHub release response")
        return payload

    def _create_release(self, tag: str) -> dict[str, Any]:
        client = self._get_client()
        response = client.post(
            f"{GITHUB_API}/repos/{self.owner}/{self.repo}/releases",
            json={
                "tag_name": tag,
                "name": tag,
                "body": "OpenRoleRadar live state snapshot",
                "draft": False,
                "prerelease": False,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected GitHub release response")
        return payload

    def _ensure_release(self, tag: str) -> dict[str, Any]:
        existing = self._get_release(tag)
        if existing is not None:
            return existing
        return self._create_release(tag)

    def _find_asset(self, release: dict[str, Any], name: str) -> dict[str, Any] | None:
        assets = release.get("assets", [])
        if not isinstance(assets, list):
            return None
        for asset in assets:
            if isinstance(asset, dict) and asset.get("name") == name:
                return asset
        return None

    def _download_asset(self, asset: dict[str, Any]) -> bytes:
        url = asset.get("browser_download_url")
        if not isinstance(url, str):
            raise ValueError("Asset missing browser_download_url")
        client = self._get_client()
        response = client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.content

    def _delete_asset(self, asset_id: int) -> None:
        client = self._get_client()
        response = client.delete(
            f"{GITHUB_API}/repos/{self.owner}/{self.repo}/releases/assets/{asset_id}"
        )
        if response.status_code not in (204, 404):
            response.raise_for_status()

    def _upload_asset(self, release_id: int, name: str, data: bytes, content_type: str) -> None:
        client = self._get_client()
        encoded_name = quote(name, safe="")
        response = client.post(
            f"{GITHUB_API}/repos/{self.owner}/{self.repo}/releases/{release_id}/assets",
            params={"name": encoded_name},
            content=data,
            headers={"Content-Type": content_type},
        )
        response.raise_for_status()

    @staticmethod
    def _build_tar_zst(state: LiveState, level: int = 3) -> bytes:
        raw = serialize_state(state)
        buffer = BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as archive:
            info = tarfile.TarInfo(name=STATE_JSON_NAME)
            info.size = len(raw)
            archive.addfile(info, BytesIO(raw))
        tar_bytes = buffer.getvalue()
        return zstd.ZstdCompressor(level=level).compress(tar_bytes)

    @staticmethod
    def _extract_state_from_tar_zst(data: bytes) -> LiveState:
        tar_bytes = zstd.ZstdDecompressor().decompress(data)
        with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r:") as archive:
            member = archive.getmember(STATE_JSON_NAME)
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"Missing {STATE_JSON_NAME} in archive")
            return deserialize_state(extracted.read())

    def _build_manifest(self, state: LiveState, sha256: str) -> ReleaseManifest:
        ls = self.config.live_state
        return ReleaseManifest(
            schema_version=1,
            generated_at=state.generated_at.isoformat(),
            release_tag=ls.release_tag,
            asset_name=ls.asset_name,
            checksums_name=ls.checksums_name,
            job_count=len(state.jobs),
            company_count=len(state.companies),
            source_count=len(state.sources),
            state_format_version=state.schema_version,
            sha256=sha256,
        )

    def load(self) -> LiveState:
        """Download and deserialize the current live-state release."""
        release = self._get_release()
        if release is None:
            return self.bootstrap_empty_state()
        asset_name = self.config.live_state.asset_name
        asset = self._find_asset(release, asset_name)
        if asset is None:
            return self.bootstrap_empty_state()
        data = self._download_asset(asset)
        manifest_asset = self._find_asset(release, self.config.live_state.manifest_name)
        if manifest_asset is not None:
            manifest_raw = self._download_asset(manifest_asset)
            manifest = json.loads(manifest_raw)
            expected = manifest.get("sha256")
            actual = hashlib.sha256(data).hexdigest()
            if isinstance(expected, str) and expected != actual:
                raise ValueError("Manifest SHA256 does not match downloaded asset")
        return self._extract_state_from_tar_zst(data)

    def save(self, state: LiveState) -> ReleaseManifest:
        """Publish state to the configured GitHub release."""
        tag = self.config.live_state.release_tag
        release = self._ensure_release(tag)
        release_id = release["id"]
        if not isinstance(release_id, int):
            raise ValueError("Release ID missing from GitHub response")

        state = state.model_copy(update={"generated_at": datetime.now(UTC)})
        asset_bytes = self._build_tar_zst(state)
        sha256 = hashlib.sha256(asset_bytes).hexdigest()
        manifest = self._build_manifest(state, sha256)

        asset_name = self.config.live_state.asset_name
        manifest_name = self.config.live_state.manifest_name
        checksums_name = self.config.live_state.checksums_name

        checksums_content = f"{sha256}  {asset_name}\n".encode()
        manifest_bytes = json.dumps(manifest.to_dict(), indent=2).encode()

        for name in (asset_name, manifest_name, checksums_name):
            existing = self._find_asset(release, name)
            if existing is not None and isinstance(existing.get("id"), int):
                self._delete_asset(existing["id"])

        self._upload_asset(release_id, asset_name, asset_bytes, "application/octet-stream")
        self._upload_asset(release_id, manifest_name, manifest_bytes, "application/json")
        self._upload_asset(release_id, checksums_name, checksums_content, "text/plain")
        return manifest
