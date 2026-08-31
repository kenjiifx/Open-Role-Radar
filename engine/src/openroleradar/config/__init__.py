from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import BaseModel, Field


class PollingTiers(BaseModel):
    hot_minutes: int = 15
    warm_minutes: int = 60
    cold_minutes: int = 360
    dormant_minutes: int = 1440


class LiveStateConfig(BaseModel):
    release_tag: str = "live-state"
    asset_name: str = "state.tar.zst"
    manifest_name: str = "manifest.json"
    checksums_name: str = "SHA256SUMS"


class ProjectVersions(BaseModel):
    state_format: int = 1
    static_api: int = 1
    job_schema: int = 1
    company_schema: int = 1
    source_schema: int = 1
    event_schema: int = 1
    parser: str = "1.0.0"
    classification: str = "1.0.0"


class ProjectConfig(BaseModel):
    name: str = "OpenRoleRadar"
    slug: str = "openroleradar"
    display_name: str = "OpenRoleRadar"
    tagline: str = ""
    description: str = ""
    repository: str = ""
    website_url: str = ""
    user_agent: str = "OpenRoleRadar/1.0"
    versions: ProjectVersions = Field(default_factory=ProjectVersions)
    live_state: LiveStateConfig = Field(default_factory=LiveStateConfig)
    polling: dict[str, Any] = Field(default_factory=dict)
    http: dict[str, Any] = Field(default_factory=dict)
    lifecycle: dict[str, Any] = Field(default_factory=dict)
    closure: dict[str, Any] = Field(default_factory=dict)
    sharding: dict[str, Any] = Field(default_factory=dict)
    feeds: dict[str, Any] = Field(default_factory=dict)
    discovery: dict[str, Any] = Field(default_factory=dict)
    health: dict[str, Any] = Field(default_factory=dict)
    archive: dict[str, Any] = Field(default_factory=dict)
    classification: dict[str, Any] = Field(default_factory=dict)


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / "config" / "project.yml").exists():
            return parent
    raise FileNotFoundError("Could not locate repository root (config/project.yml)")


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_project_config(root: Path | None = None) -> ProjectConfig:
    repo = root or find_repo_root()
    data = load_yaml(repo / "config" / "project.yml")
    return ProjectConfig.model_validate(data)


def config_dir(root: Path | None = None) -> Path:
    return (root or find_repo_root()) / "config"


def load_taxonomy(root: Path | None = None) -> dict[str, Any]:
    data = load_yaml(config_dir(root) / "taxonomy.yml")
    return cast(dict[str, Any], data)


def load_skills_config(root: Path | None = None) -> dict[str, Any]:
    data = load_yaml(config_dir(root) / "skills.yml")
    return cast(dict[str, Any], data)
