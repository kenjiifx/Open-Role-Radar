# Contributing to OpenRoleRadar

Thank you for helping build open, first-party early-career job intelligence. This guide covers the workflows most contributors encounter.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Be respectful and constructive.

## Ways to contribute

1. **Add seed sources** — edit `config/sources.yml` (see below)
2. **Fix adapters or classification** — Python changes in `engine/`
3. **Improve the site** — Astro/React changes in `site/`
4. **Documentation** — `docs/` and README updates
5. **Report data issues** — use GitHub issue templates

## Development setup

### Windows

```powershell
./scripts/bootstrap.ps1
```

### macOS / Linux

```bash
chmod +x scripts/bootstrap.sh scripts/sync.sh
./scripts/bootstrap.sh
```

### Manual setup

```bash
cd engine && uv sync --all-extras --dev
cd ../site && pnpm install
```

## Running checks locally

```bash
# Python
cd engine
uv run ruff check src tests
uv run mypy src
uv run pytest

# Site
cd site
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

## Adding a career source

1. Confirm the employer uses a **first-party** ATS board (not LinkedIn/Indeed).
2. Add an entry to `config/sources.yml`:

```yaml
- company: Example Corp
  domain: example.com
  adapter: greenhouse
  tenant: example
```

3. Validate locally:

```bash
uv run --directory engine python scripts/validate-sources.py
```

4. Open a PR. The `validate-sources` workflow runs automatically with **read-only** permissions—safe for forks.

### Supported adapters

`greenhouse`, `lever`, `ashby`, `smartrecruiters`, `workday`, `json_ld`

## Pull request guidelines

- Fill out the PR template completely.
- Keep changes focused; unrelated refactors belong in separate PRs.
- Do not commit `.local/`, `.env`, or generated API artifacts.
- Ensure CI passes (Python + site jobs).

## Commit messages

Use clear, imperative subjects:

- `source: add Acme Corp greenhouse board`
- `fix: parse Lever location arrays`
- `docs: clarify mobility evidence statuses`

## License

Code contributions are licensed under the [MIT License](LICENSE). Published job metadata is described in [DATA_LICENSE.md](DATA_LICENSE.md).

## Questions

Open a [Feature request](.github/ISSUE_TEMPLATE/feature.yml) or start a discussion in the repository.
