"""Adapter health monitoring and regression detection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from openroleradar.config import ProjectConfig, load_project_config
from openroleradar.models.enums import SourceHealth
from openroleradar.models.state import AdapterHealthStats, LiveState


@dataclass(frozen=True)
class HealthRegression:
    """Detected adapter health regression."""

    adapter: str
    failure_rate: float
    success_count: int
    failure_count: int
    severity: str
    message: str


@dataclass(frozen=True)
class HealthReport:
    """Summary of adapter health across the live state."""

    generated_at: datetime
    regressions: list[HealthRegression]
    adapter_stats: dict[str, AdapterHealthStats]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "regression_count": len(self.regressions),
            "regressions": [
                {
                    "adapter": item.adapter,
                    "failure_rate": item.failure_rate,
                    "success_count": item.success_count,
                    "failure_count": item.failure_count,
                    "severity": item.severity,
                    "message": item.message,
                }
                for item in self.regressions
            ],
        }


class HealthMonitor:
    """Detect adapter health regressions from live state metrics."""

    def __init__(self, config: ProjectConfig | None = None) -> None:
        self.config = config or load_project_config()
        self.failure_threshold = float(self.config.health.get("adapter_failure_threshold", 0.5))
        self.min_samples = int(self.config.health.get("adapter_min_samples", 10))

    def failure_rate(self, stats: AdapterHealthStats) -> float:
        total = stats.success_count + stats.failure_count
        if total == 0:
            return 0.0
        return stats.failure_count / total

    def detect_regression(self, stats: AdapterHealthStats) -> HealthRegression | None:
        total = stats.success_count + stats.failure_count
        if total < self.min_samples:
            return None
        rate = self.failure_rate(stats)
        if rate < self.failure_threshold:
            return None
        severity = "critical" if rate >= 0.8 else "warning"
        return HealthRegression(
            adapter=stats.adapter,
            failure_rate=round(rate, 3),
            success_count=stats.success_count,
            failure_count=stats.failure_count,
            severity=severity,
            message=(
                f"Adapter {stats.adapter} failure rate {rate:.1%} "
                f"exceeds threshold {self.failure_threshold:.1%}"
            ),
        )

    def analyze(self, state: LiveState) -> HealthReport:
        """Analyze adapter health and return regression report."""
        regressions: list[HealthRegression] = []
        for stats in state.adapter_health.values():
            regression = self.detect_regression(stats)
            if regression is not None:
                regressions.append(regression)
        return HealthReport(
            generated_at=datetime.now(UTC),
            regressions=regressions,
            adapter_stats=dict(state.adapter_health),
        )

    def apply_source_health(self, state: LiveState) -> LiveState:
        """Update source health_status based on adapter regressions."""
        report = self.analyze(state)
        failing_adapters = {item.adapter for item in report.regressions}
        updated_sources = {}
        for source_id, source in state.sources.items():
            if source.adapter in failing_adapters:
                updated = source.model_copy(update={"health_status": SourceHealth.DEGRADED.value})
                updated_sources[source_id] = updated
            else:
                updated_sources[source_id] = source
        return state.model_copy(update={"sources": updated_sources})

    def record_success(self, state: LiveState, adapter: str) -> LiveState:
        stats = state.adapter_health.get(
            adapter,
            AdapterHealthStats(adapter=adapter),
        )
        updated_stats = stats.model_copy(update={"success_count": stats.success_count + 1})
        health = dict(state.adapter_health)
        health[adapter] = updated_stats
        return state.model_copy(update={"adapter_health": health})

    def record_failure(
        self,
        state: LiveState,
        adapter: str,
        error: str | None = None,
    ) -> LiveState:
        stats = state.adapter_health.get(
            adapter,
            AdapterHealthStats(adapter=adapter),
        )
        samples = list(stats.sample_errors)
        if error:
            samples.append(error[:500])
            samples = samples[-5:]
        updated_stats = stats.model_copy(
            update={
                "failure_count": stats.failure_count + 1,
                "last_failure_at": datetime.now(UTC),
                "sample_errors": samples,
            }
        )
        health = dict(state.adapter_health)
        health[adapter] = updated_stats
        return state.model_copy(update={"adapter_health": health})
