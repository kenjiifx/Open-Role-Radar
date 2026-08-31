"""Unit tests for storage layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from openroleradar.models.state import LiveState
from openroleradar.storage.local import LocalStateStore
from openroleradar.storage.serialize import deserialize_state, serialize_state


def test_serialize_roundtrip(sample_state: LiveState) -> None:
    raw = serialize_state(sample_state)
    restored = deserialize_state(raw)
    assert restored.schema_version == sample_state.schema_version
    assert set(restored.jobs) == set(sample_state.jobs)
    assert restored.jobs["job-1"].title == "Software Engineer Intern"


def test_local_store_save_load(tmp_path: Path, sample_state: LiveState) -> None:
    store = LocalStateStore(tmp_path)
    artifact = store.save(sample_state)
    assert artifact.path.exists()
    assert artifact.checksum
    loaded = store.load()
    assert loaded.jobs["job-1"].company_name == "Stripe"


def test_local_store_archive_roundtrip(tmp_path: Path, sample_state: LiveState) -> None:
    store = LocalStateStore(tmp_path)
    store.save_archive(sample_state)
    loaded = store.load_archive()
    assert len(loaded.jobs) == 1


def test_local_store_checksum_verification(tmp_path: Path, sample_state: LiveState) -> None:
    store = LocalStateStore(tmp_path)
    store.save(sample_state)
    state_path = tmp_path / "state.json.zst"
    corrupted = bytearray(state_path.read_bytes())
    corrupted[-1] ^= 0xFF
    state_path.write_bytes(bytes(corrupted))
    with pytest.raises(ValueError, match="Checksum mismatch"):
        store.load()


def test_local_store_atomic_write(tmp_path: Path, sample_state: LiveState) -> None:
    store = LocalStateStore(tmp_path)
    store.save(sample_state)
    assert not any(tmp_path.glob("*.tmp"))
    checksums = store.build_checksums_file([store._state_path])
    assert "state.json.zst" in checksums
