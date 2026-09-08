"""OpenRoleRadar command-line interface."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from openroleradar.config import find_repo_root, load_project_config
from openroleradar.discovery.career_site import CareerSiteInspector
from openroleradar.discovery.github_search import GitHubCodeSearch
from openroleradar.discovery.registry import load_seed_sources
from openroleradar.export.archive import ArchiveExporter
from openroleradar.export.readme import ReadmeGenerator
from openroleradar.health.monitor import HealthMonitor
from openroleradar.storage.local import LocalStateStore
from openroleradar.sync import SyncOrchestrator

app = typer.Typer(
    name="openroleradar",
    help="OpenRoleRadar — global early-career opportunity intelligence",
    no_args_is_help=True,
)
console = Console()


def _repo_root() -> Path:
    try:
        return find_repo_root()
    except FileNotFoundError:
        console.print("[red]Could not find repository root (config/project.yml)[/red]")
        raise typer.Exit(1) from None


def _state_store(root: Path) -> LocalStateStore:
    store = LocalStateStore(root / ".local" / "state")
    store.ensure_directory()
    return store


@app.command()
def sync(
    sample: Annotated[bool, typer.Option("--sample", help="Sync only a few sources")] = False,
) -> None:
    """Poll due sources, normalize jobs, update lifecycle state."""
    root = _repo_root()
    orchestrator = SyncOrchestrator(root=root)
    restored = orchestrator.restore_live_state_release()
    if restored:
        console.print("[cyan]Restored live state from GitHub Release[/cyan]")
    console.print("[bold]Starting synchronization...[/bold]")
    summary = asyncio.run(orchestrator.run_sync(sample=sample))
    table = Table(title="Sync Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    for key, value in summary.items():
        table.add_row(str(key), str(value))
    console.print(table)
    if summary.get("failures", 0) > 0 and summary.get("fetched", 0) == 0:
        raise typer.Exit(1)


@app.command("publish-state")
def publish_state() -> None:
    """Publish local live-state to the durable GitHub Release."""
    root = _repo_root()
    result = SyncOrchestrator(root=root).publish_live_state_release()
    console.print_json(json.dumps(result, indent=2))


@app.command("build-data")
def build_data() -> None:
    """Export static API, site data shards, and feeds."""
    root = _repo_root()
    result = SyncOrchestrator(root=root).build_exports()
    console.print_json(json.dumps(result, indent=2))


@app.command("build-site-data")
def build_site_data() -> None:
    """Alias for site data export portion of build-data."""
    build_data()


@app.command()
def discover(
    github: Annotated[bool, typer.Option("--github/--no-github")] = True,
) -> None:
    """Run source discovery (GitHub code search, career site inspection)."""
    root = _repo_root()
    config = load_project_config(root)
    store = _state_store(root)
    state = store.load() if store.exists() else SyncOrchestrator(root=root).bootstrap_state()

    counts = {"github": 0, "career": 0}
    if github:
        with GitHubCodeSearch(config=config) as search:
            candidates, _cursor = search.discover()
            counts["github"] = len(candidates)
    with CareerSiteInspector(config=config) as inspector:
        for seed in load_seed_sources(root)[:5]:
            result = inspector.inspect(seed.domain)
            if result.ats_match is not None:
                counts["career"] += 1

    store.save(state)
    console.print(f"Discovery complete: {counts}")


@app.command()
def validate() -> None:
    """Validate seed sources and current state."""
    root = _repo_root()
    seeds = load_seed_sources(root)
    console.print(f"[green]Validated {len(seeds)} seed sources[/green]")
    store = _state_store(root)
    if store.exists():
        state = store.load()
        console.print(f"State: {len(state.jobs)} jobs, {len(state.sources)} sources")
    else:
        console.print("[yellow]No local state found — run sync first[/yellow]")


@app.command()
def archive(
    month: Annotated[str | None, typer.Option(help="YYYY-MM")] = None,
) -> None:
    """Create monthly historical dataset archive."""
    root = _repo_root()
    store = _state_store(root)
    if not store.exists():
        console.print("[red]No state to archive[/red]")
        raise typer.Exit(1)
    state = store.load()
    out = root / ".local" / "archives"
    out.mkdir(parents=True, exist_ok=True)
    path = ArchiveExporter(config=load_project_config(root)).export(state, out, month=month)
    console.print(f"Archive written: {path.path}")


@app.command()
def health() -> None:
    """Show adapter and source health statistics."""
    root = _repo_root()
    store = _state_store(root)
    if not store.exists():
        console.print("[yellow]No state — run sync first[/yellow]")
        raise typer.Exit(0)
    state = store.load()
    monitor = HealthMonitor(load_project_config(root))
    regressions = monitor.analyze(state).regressions
    table = Table(title="Adapter Health")
    table.add_column("Adapter")
    table.add_column("Success")
    table.add_column("Failure")
    table.add_column("Rate")
    for name, stats in state.adapter_health.items():
        total = stats.success_count + stats.failure_count
        rate = stats.success_count / total if total else 0
        table.add_row(name, str(stats.success_count), str(stats.failure_count), f"{rate:.1%}")
    console.print(table)
    if regressions:
        console.print(f"[red]{len(regressions)} adapter regression(s) detected[/red]")


@app.command("inspect-source")
def inspect_source(source_id: str) -> None:
    """Inspect a source by ID."""
    root = _repo_root()
    store = _state_store(root)
    if not store.exists():
        raise typer.Exit(1)
    state = store.load()
    source = state.sources.get(source_id)
    if source is None:
        console.print(f"[red]Source not found: {source_id}[/red]")
        raise typer.Exit(1)
    console.print_json(source.model_dump_json(indent=2))


@app.command("inspect-job")
def inspect_job(job_id: str) -> None:
    """Inspect a job by ID."""
    root = _repo_root()
    store = _state_store(root)
    if not store.exists():
        raise typer.Exit(1)
    state = store.load()
    job = state.jobs.get(job_id)
    if job is None:
        console.print(f"[red]Job not found: {job_id}[/red]")
        raise typer.Exit(1)
    console.print_json(job.model_dump_json(indent=2))


@app.command("update-readme")
def update_readme() -> None:
    """Update generated README stats section."""
    root = _repo_root()
    store = _state_store(root)
    state = store.load() if store.exists() else SyncOrchestrator(root=root).bootstrap_state()
    readme = root / "README.md"
    ReadmeGenerator(load_project_config(root)).update_readme(readme, state)
    console.print("[green]README stats updated[/green]")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
