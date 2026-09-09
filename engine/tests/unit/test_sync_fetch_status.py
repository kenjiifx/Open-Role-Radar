"""Tests for adapter fetch status handling in sync."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from openroleradar.adapters.base import AdapterFetchResult
from openroleradar.config import find_repo_root
from openroleradar.models.job import Company, Source
from openroleradar.models.state import LiveState
from openroleradar.sync import SyncOrchestrator


@pytest.mark.asyncio
async def test_fetch_source_treats_adapter_error_as_failure(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    orchestrator = SyncOrchestrator(root=find_repo_root(), state_dir=tmp_path / "state")
    now = datetime.now(UTC)
    source = Source(
        source_id="src1",
        company_id="co1",
        company_name="Acme",
        company_domain="acme.com",
        careers_url="https://acme.com/careers",
        adapter="greenhouse",
        adapter_tenant="acme",
        first_discovered_at=now,
        last_validated_at=now,
        health_status="healthy",
        enabled=True,
    )
    state = LiveState(
        companies={
            "co1": Company(
                company_id="co1",
                name="Acme",
                normalized_name="acme",
                canonical_domain="acme.com",
                first_seen_at=now,
                last_seen_at=now,
            )
        },
        sources={"src1": source},
    )

    adapter = MagicMock()
    adapter.supported = True
    adapter.fetch_jobs = AsyncMock(
        return_value=AdapterFetchResult(status="error", message="HTTP 404", jobs=[])
    )
    monkeypatch.setattr("openroleradar.sync.get_adapter", lambda _name: adapter)

    result = await orchestrator._fetch_source(MagicMock(), source, state)

    assert result["status"] == "error"
    assert result["jobs"] == []
    assert source.consecutive_failures == 1
    assert source.last_success_at is None
