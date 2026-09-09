# OpenRoleRadar

First-party early-career roles (internships, co-ops, new grad) scraped from public employer ATS boards and published as a searchable static site.

[![CI](https://github.com/kenjiifx/Open-Role-Radar/actions/workflows/ci.yml/badge.svg)](https://github.com/kenjiifx/Open-Role-Radar/actions/workflows/ci.yml)
[![Sync](https://github.com/kenjiifx/Open-Role-Radar/actions/workflows/sync.yml/badge.svg)](https://github.com/kenjiifx/Open-Role-Radar/actions/workflows/sync.yml)

**Live:** https://kenjiifx.github.io/Open-Role-Radar/

<!-- GENERATED_STATS:START -->
## Live Statistics

_Last updated: 2026-09-09 10:03 UTC_

| Metric | Count |
| --- | ---: |
| Public early-career roles | 1,599 |
| Total tracked roles | 47,904 |
| Companies | 514 |
| Sources | 595 |
| Healthy sources | 491 |
| ATS adapters | 5 |

Published by [OpenRoleRadar](https://kenjiifx.github.io/Open-Role-Radar/).
<!-- GENERATED_STATS:END -->

## What it does

- Polls **public** Greenhouse, Lever, Ashby, Workday, Workable, and SmartRecruiters boards on a GitHub Actions schedule
- Classifies early-career titles (intern / co-op / new-grad / junior / engineer I / campus, plus ATS metadata tags)
- Exports static JSON + Atom feeds; browser refresh reads a live-feed branch so Pages CDN lag doesn’t hide new syncs

## What it does not do

- Scrape LinkedIn or Indeed (aggregator noise; we only use first-party ATS APIs)
- Cover every employer on earth — boards still need a public API we can poll
- Guarantee sub-minute latency — sync runs every few minutes, then live-feed updates

## Repo layout

| Path | Role |
| --- | --- |
| `engine/` | Python sync, classify, export |
| `site/` | Astro search UI |
| `config/` | Seed companies, taxonomy |
| `docs/` | Architecture and ops |

## Local setup

Needs Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 22+, pnpm.

```powershell
./scripts/bootstrap.ps1
```

```bash
./scripts/bootstrap.sh
cd engine && uv run openroleradar sync --sample
cd ../site && pnpm dev
```

Optional: copy `.env.example` → `.env`.

## CLI

| Command | Description |
| --- | --- |
| `openroleradar sync` | Poll sources and update state |
| `openroleradar build-data` | Export API, feeds, site shards |
| `openroleradar discover` | Find, validate, and promote new ATS boards |
| `openroleradar validate` | Validate seeds / summarize state |

## Add a company

Edit `config/sources.yml`:

```yaml
- company: Acme Corp
  domain: acme.com
  adapter: greenhouse
  tenant: acme
```

Then open a PR. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Docs

- [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [API.md](docs/API.md)
- [OPERATIONS.md](docs/OPERATIONS.md)

## License

MIT — see [LICENSE](LICENSE). Published data: [DATA_LICENSE.md](DATA_LICENSE.md).

OpenRoleRadar is not affiliated with any employer or ATS. Verify details on the official careers page before applying.
