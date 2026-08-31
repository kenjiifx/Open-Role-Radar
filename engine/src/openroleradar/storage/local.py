"""Local filesystem persistence with zstd compression, checksums, and atomic writes."""

from __future__ import annotations

import hashlib
import os
import tarfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import zstandard as zstd

from openroleradar.models.state import LiveState
from openroleradar.storage.serialize import deserialize_state, serialize_state

STATE_JSON_NAME = "state.json"
CHECKSUM_SUFFIX = ".sha256"


@dataclass(frozen=True)
class StoredArtifact:
    """Metadata for a persisted state artifact."""

    path: Path
    checksum: str
    compressed_bytes: int
    uncompressed_bytes: int


class LocalStateStore:
    """Read and write LiveState to the local filesystem."""

    def __init__(
        self,
        directory: Path,
        *,
        compression_level: int = 3,
        verify_checksum: bool = True,
    ) -> None:
        self.directory = directory.resolve()
        self.compression_level = compression_level
        self.verify_checksum = verify_checksum
        self._state_path = self.directory / "state.json.zst"
        self._archive_path = self.directory / "state.tar.zst"
        self._checksum_path = self._state_path.with_suffix(
            f"{self._state_path.suffix}{CHECKSUM_SUFFIX}"
        )

    def ensure_directory(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sha256_hex(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _compress(self, data: bytes) -> bytes:
        compressor = zstd.ZstdCompressor(level=self.compression_level)
        return compressor.compress(data)

    def _decompress(self, data: bytes) -> bytes:
        decompressor = zstd.ZstdDecompressor()
        return decompressor.decompress(data)

    def _atomic_write(self, path: Path, data: bytes) -> None:
        self.ensure_directory()
        tmp_path = path.with_suffix(f"{path.suffix}.tmp")
        with tmp_path.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)

    def _write_checksum(self, path: Path, data: bytes) -> str:
        digest = self.sha256_hex(data)
        checksum_path = path.with_suffix(f"{path.suffix}{CHECKSUM_SUFFIX}")
        self._atomic_write(checksum_path, f"{digest}  {path.name}\n".encode())
        return digest

    def _read_checksum(self, path: Path) -> str | None:
        checksum_path = path.with_suffix(f"{path.suffix}{CHECKSUM_SUFFIX}")
        if not checksum_path.exists():
            return None
        line = checksum_path.read_text(encoding="utf-8").strip().split()
        return line[0] if line else None

    def _verify(self, path: Path, data: bytes) -> None:
        if not self.verify_checksum:
            return
        expected = self._read_checksum(path)
        if expected is None:
            return
        actual = self.sha256_hex(data)
        if actual != expected:
            raise ValueError(
                f"Checksum mismatch for {path.name}: expected {expected}, got {actual}"
            )

    def save(self, state: LiveState) -> StoredArtifact:
        """Serialize, compress, checksum, and atomically persist state."""
        raw = serialize_state(state)
        compressed = self._compress(raw)
        self._atomic_write(self._state_path, compressed)
        digest = self._write_checksum(self._state_path, compressed)
        return StoredArtifact(
            path=self._state_path,
            checksum=digest,
            compressed_bytes=len(compressed),
            uncompressed_bytes=len(raw),
        )

    def load(self) -> LiveState:
        """Load and deserialize state from the default compressed path."""
        if not self._state_path.exists():
            raise FileNotFoundError(f"State file not found: {self._state_path}")
        compressed = self._state_path.read_bytes()
        self._verify(self._state_path, compressed)
        raw = self._decompress(compressed)
        return deserialize_state(raw)

    def exists(self) -> bool:
        return self._state_path.exists()

    def save_archive(self, state: LiveState) -> StoredArtifact:
        """Persist state as a tar.zst archive (GitHub release compatible)."""
        raw = serialize_state(state)
        buffer = BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as archive:
            info = tarfile.TarInfo(name=STATE_JSON_NAME)
            info.size = len(raw)
            archive.addfile(info, BytesIO(raw))
        tar_bytes = buffer.getvalue()
        compressed = self._compress(tar_bytes)
        self._atomic_write(self._archive_path, compressed)
        digest = self._write_checksum(self._archive_path, compressed)
        return StoredArtifact(
            path=self._archive_path,
            checksum=digest,
            compressed_bytes=len(compressed),
            uncompressed_bytes=len(tar_bytes),
        )

    def load_archive(self) -> LiveState:
        """Load state from a tar.zst archive."""
        if not self._archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {self._archive_path}")
        compressed = self._archive_path.read_bytes()
        self._verify(self._archive_path, compressed)
        tar_bytes = self._decompress(compressed)
        with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r:") as archive:
            member = archive.getmember(STATE_JSON_NAME)
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"Missing {STATE_JSON_NAME} in archive")
            raw = extracted.read()
        return deserialize_state(raw)

    def build_checksums_file(self, artifacts: list[Path]) -> str:
        """Build SHA256SUMS content for the given artifact paths."""
        lines: list[str] = []
        for artifact in artifacts:
            data = artifact.read_bytes()
            digest = self.sha256_hex(data)
            lines.append(f"{digest}  {artifact.name}")
        return "\n".join(lines) + "\n"
