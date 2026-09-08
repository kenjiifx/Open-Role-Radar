# OpenRoleRadar

First-party early-career roles (internships, co-ops, new grad) scraped from employer ATS boards and published as a searchable static site.

[![CI](https://github.com/kenjiifx/Open-Role-Radar/actions/workflows/ci.yml/badge.svg)](https://github.com/kenjiifx/Open-Role-Radar/actions/workflows/ci.yml)
[![Sync](https://github.com/kenjiifx/Open-Role-Radar/actions/workflows/sync.yml/badge.svg)](https://github.com/kenjiifx/Open-Role-Radar/actions/workflows/sync.yml)

**Live:** https://kenjiifx.github.io/Open-Role-Radar/

## What it does

- Polls Greenhouse, Lever, Ashby, SmartRecruiters, and JSON-LD career pages (no LinkedIn/Indeed)
- Classifies early-career roles and extracts mobility signals (visa, relocation)
- Exports static JSON + Atom feeds and deploys to GitHub Pages on a schedule

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
| `openroleradar discover` | Find new ATS boards |
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
