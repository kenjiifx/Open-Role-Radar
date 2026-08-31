# OpenRoleRadar

**Global early-career opportunity intelligence** — an autonomous, zero-cost pipeline that discovers first-party internships, co-ops, and new-grad roles from employer ATS boards, normalizes them into structured JSON, and publishes a searchable static site on GitHub Pages.

[![CI](https://github.com/kenjiifx/Open-Role-Radar/actions/workflows/ci.yml/badge.svg)](https://github.com/kenjiifx/Open-Role-Radar/actions/workflows/ci.yml)
[![Sync](https://github.com/kenjiifx/Open-Role-Radar/actions/workflows/sync.yml/badge.svg)](https://github.com/kenjiifx/Open-Role-Radar/actions/workflows/sync.yml)

**Live site:** [kenjiifx.github.io/Open-Role-Radar](https://kenjiifx.github.io/Open-Role-Radar/)

<!-- GENERATED_STATS:START -->
## Live Statistics

_Last updated: 2026-08-31 15:31 UTC_

| Metric | Count |
| --- | ---: |
| Open roles | 1,489 |
| Total tracked roles | 1,489 |
| Companies | 20 |
| Sources | 20 |
| Healthy sources | 20 |
| ATS adapters | 3 |

Published by [OpenRoleRadar](https://kenjiifx.github.io/Open-Role-Radar/).
<!-- GENERATED_STATS:END -->

## Features

- **First-party sources only** — Greenhouse, Lever, Ashby, SmartRecruiters, Workday, and JSON-LD career pages. Aggregators (LinkedIn, Indeed, etc.) are denylisted.
- **Early-career focus** — classifies internships, co-ops, new grad, apprenticeships, fellowships, and student programs.
- **Mobility signals** — visa sponsorship, relocation assistance, and international-candidate hints with evidence excerpts.
- **Eligibility extraction** — work authorization, country allow/deny lists, clearance, and language requirements.
- **Lifecycle tracking** — open, update, close, and reopen events with content hashing.
- **Static JSON API** — shardable, cache-friendly exports under `/api/v1/` (no server required).
- **Atom feeds** — subscribe to early-career listings without an API key.
- **Automated operations** — GitHub Actions sync every 15 minutes, daily discovery, monthly archives.
- **Fork-safe contributions** — propose new companies via `config/sources.yml` with read-only PR validation.

## Architecture

```
config/sources.yml ──► Python engine (adapters, classify, lifecycle)
                              │
                              ▼
                     .local/state (CI cache)
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        api/v1/*.json   feeds/*.atom    README stats
              │
              ▼
        Astro static site ──► GitHub Pages
```

| Component | Path | Role |
| --- | --- | --- |
| Engine | `engine/` | Sync, discovery, normalization, export |
| Site | `site/` | Astro + React search UI |
| Config | `config/` | Seeds, taxonomy, denylist, project settings |
| Schemas | `schemas/` | JSON Schema for public records |
| Docs | `docs/` | Architecture, API, operations |

Deep dive: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Supported ATS adapters

| Adapter | Status |
| --- | --- |
| Greenhouse | Full |
| Lever | Full |
| Ashby | Full |
| SmartRecruiters | Full |
| Workday | Partial |
| JSON-LD | Full |

## Quick start (development)

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 22+
- pnpm 9 (`corepack enable`)

### Bootstrap

**Windows (PowerShell):**

```powershell
./scripts/bootstrap.ps1
```

**macOS / Linux:**

```bash
chmod +x scripts/bootstrap.sh scripts/sync.sh
./scripts/bootstrap.sh
```

### Run a sample sync

```bash
./scripts/sync.sh --sample
# or
cd engine && uv run openroleradar sync --sample
```

### Build exports and site

```bash
cd engine && uv run openroleradar build-data
cd ../site && pnpm build
```

### Local site preview

```bash
cd site && pnpm dev
```

Copy [`.env.example`](.env.example) to `.env` for optional local overrides.

## CLI reference

| Command | Description |
| --- | --- |
| `openroleradar sync` | Poll due sources and update state |
| `openroleradar build-data` | Export API, feeds, and site shards |
| `openroleradar discover` | Run GitHub / career site discovery |
| `openroleradar validate` | Validate seeds and summarize state |
| `openroleradar health` | Adapter success/failure statistics |
| `openroleradar archive` | Write monthly dataset archive |
| `openroleradar update-readme` | Refresh generated stats in this file |
| `openroleradar inspect-job <id>` | Dump a job record |
| `openroleradar inspect-source <id>` | Dump a source record |

## Adding a company

Edit `config/sources.yml`:

```yaml
- company: Acme Corp
  domain: acme.com
  adapter: greenhouse
  tenant: acme
```

Validate and open a PR:

```bash
uv run --directory engine python scripts/validate-sources.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [Add career source](.github/ISSUE_TEMPLATE/add-source.yml) issue template.

## Static API

Base URL: `https://kenjiifx.github.io/Open-Role-Radar/api/v1/`

| Endpoint | Content |
| --- | --- |
| `meta.json` | Dataset metadata and counts |
| `companies.json` | Employer records |
| `sources.json` | Polled ATS endpoints |
| `jobs/index.json` | Open job index |
| `jobs/shard/{bucket}.json` | Full job payloads |

Full reference: [docs/API.md](docs/API.md)

## Personal job watch

Copy [`templates/user-watch/workflow.yml`](templates/user-watch/workflow.yml) into your own repository to get GitHub Issues alerts when new feed entries match your keywords. No API keys required.

## Documentation

| Document | Topic |
| --- | --- |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and data flow |
| [DATA_MODEL.md](docs/DATA_MODEL.md) | Jobs, companies, sources, events |
| [SOURCE_DISCOVERY.md](docs/SOURCE_DISCOVERY.md) | GitHub + Common Crawl discovery |
| [CRAWLING_POLICY.md](docs/CRAWLING_POLICY.md) | Rate limits and robots etiquette |
| [MOBILITY.md](docs/MOBILITY.md) | Visa and relocation signals |
| [ELIGIBILITY.md](docs/ELIGIBILITY.md) | Work authorization signals |
| [API.md](docs/API.md) | Static JSON API |
| [OPERATIONS.md](docs/OPERATIONS.md) | CI/CD runbook |

## GitHub Actions

| Workflow | Schedule | Purpose |
| --- | --- | --- |
| CI | PR / push | Lint, typecheck, test, build |
| Sync | `7,22,37,52 * * * *` | Sync, export, deploy Pages |
| Discover | Daily 04:15 UTC | Find new ATS boards |
| Archive | 1st of month | Monthly dataset export |
| README | Daily 06:45 UTC | Update stats above |
| Security | Weekly + PR | CodeQL, dependency audit |
| Validate sources | PR | SSRF/denylist check on seeds |

## License

- **Code:** [MIT](LICENSE)
- **Published data:** [DATA_LICENSE.md](DATA_LICENSE.md)
- **Conduct:** [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **Security:** [SECURITY.md](SECURITY.md)

## Disclaimer

OpenRoleRadar aggregates publicly available posting metadata for discovery purposes. It is not affiliated with any employer or ATS vendor. Always verify details on the official careers page before applying. Automated eligibility and mobility signals are not legal advice.
