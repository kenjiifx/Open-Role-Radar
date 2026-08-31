# Operations

Runbook for maintainers and advanced contributors operating OpenRoleRadar in GitHub Actions or locally.

## Workflows

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `ci.yml` | PR / push | Ruff, mypy, pytest, site lint/typecheck/test/build |
| `sync.yml` | Every 15 min (offset) + manual | Sync, build-data, deploy Pages |
| `discover.yml` | Daily + manual | GitHub + Common Crawl discovery |
| `archive.yml` | Monthly + manual | Export compressed historical dataset |
| `readme.yml` | Daily + manual | Refresh README `GENERATED_STATS` |
| `security.yml` | Weekly + PR | CodeQL, dependency review, audits |
| `validate-sources.yml` | PR (sources.yml) | Read-only seed validation |

All workflows pin third-party Actions to full commit SHAs with version comments.

## GitHub Pages setup

1. Repository **Settings → Pages → Build and deployment → GitHub Actions**
2. Ensure `sync.yml` has `permissions: pages: write` and `id-token: write`
3. Environment `github-pages` is created automatically on first deploy

## Live state cache

`sync.yml` restores/saves `.local/state` via Actions cache keys `live-state-*`. If state is corrupted:

```bash
# Locally
rm -rf .local/state
cd engine && uv run openroleradar sync --sample
```

In CI, re-run sync with an empty cache by changing the cache key prefix in a maintainer PR (last resort).

## Manual commands

```bash
# Bootstrap (Windows)
./scripts/bootstrap.ps1

# Bootstrap (Unix)
./scripts/bootstrap.sh

# Sync wrapper
./scripts/sync.sh --sample

# Validate sources only
uv run --directory engine python scripts/validate-sources.py

# Full export pipeline
cd engine
uv run openroleradar sync
uv run openroleradar build-data
uv run openroleradar update-readme
uv run openroleradar health
uv run openroleradar archive --month 2026-07
```

## Environment variables

Copy `.env.example` to `.env` for local overrides. **Never commit `.env`.**

| Variable | Used for |
| --- | --- |
| `GITHUB_TOKEN` | Discovery GitHub search (CI provides automatically) |
| `ASTRO_BASE` | Site base path (default `/Open-Role-Radar/`) |
| `ASTRO_SITE` | Canonical site origin for sitemap |

## Monitoring

### Adapter health

```bash
cd engine && uv run openroleradar health
```

Shows per-adapter success/failure rates and regression warnings when `health.adapter_failure_threshold` is exceeded.

### Source failures

Inspect individual sources:

```bash
uv run openroleradar inspect-source <source_id>
```

File **Broken source** issues when `consecutive_failures` climbs or `health_status` is `failing`.

## Incident response

| Symptom | Action |
| --- | --- |
| Sync workflow red | Check adapter logs; run `health`; disable flaky source |
| Empty site/API | Verify `build-data` step; confirm cache restore |
| Mass job closures | Check source health; review `unhealthy_source_never_closes` |
| SSRF validation failure on PR | Reject source; verify domain is public corporate site |
| Rate limited by ATS | Lower poll tier; reduce `max_sources_per_sync` |

## Secrets policy

- Fork PR workflows use read-only `contents` permission.
- `validate-sources.yml` sets `persist-credentials: false`.
- No repository secrets are required for public operation.
- Optional: add `GITHUB_TOKEN` fine-grained permissions only if discovery quotas increase.

## Releases and archives

Monthly archives upload to workflow artifacts (`archive.yml`, 90-day retention). For long-term public datasets, attach releases manually from maintainer machines:

```bash
uv run openroleradar archive --month YYYY-MM
```

## User watch template

Decentralized alerting: copy `templates/user-watch/workflow.yml` to a personal repo. See `templates/user-watch/README.md`.

## Related documents

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [CRAWLING_POLICY.md](CRAWLING_POLICY.md)
- [SECURITY.md](../SECURITY.md)
