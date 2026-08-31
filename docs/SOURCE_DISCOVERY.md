# Source Discovery

OpenRoleRadar expands beyond the human-maintained seed list (`config/sources.yml`) using automated discovery pipelines. All candidates must pass validation before promotion.

## Discovery channels

### 1. Seed list (manual)

Contributors open PRs editing `config/sources.yml`. The `validate-sources` workflow runs `scripts/validate-sources.py` on every PR touching the file.

Requirements:

- First-party corporate domain
- Supported adapter (`greenhouse`, `lever`, `ashby`, `smartrecruiters`, `workday`, `json_ld`)
- Valid tenant slug
- Domain not on aggregator denylist
- No SSRF/private IP resolution

### 2. GitHub code search

`engine/src/openroleradar/discovery/github_search.py` searches public repositories for known ATS URL patterns listed in `config/ats-hosts.yml` (`discovery_patterns`).

Configuration (`config/project.yml`):

```yaml
discovery:
  github_search_per_run: 30
  promotion_min_confidence: 0.75
```

Runs daily via `.github/workflows/discover.yml`. Uses `GITHUB_TOKEN` with public search scope only on the default branch.

### 3. Common Crawl

`engine/src/openroleradar/discovery/common_crawl.py` queries the Common Crawl index for URLs matching ATS host patterns.

Limits per run: `common_crawl_per_run` (default 100). Respects the same validation pipeline as GitHub hits.

### 4. Career site inspection

For seed domains, `inspect_career_site` fetches the corporate careers page and detects embedded ATS boards or JSON-LD `JobPosting` blocks.

## Validation pipeline

`engine/src/openroleradar/discovery/validate.py` scores and accepts or quarantines candidates.

### Checks

1. **Scheme** — `http` or `https` only
2. **Hostname** — present and not resolving to private/reserved IPs
3. **Denylist** — reject aggregator/mirror domains (`config/aggregators-denylist.yml`)
4. **ATS detection** — `ats_detect.py` matches host patterns from `config/ats-hosts.yml`
5. **Confidence scoring** — boosts for known platform+tenant, HTTPS, JSON-LD
6. **Thresholds** — compare against `promotion_min_confidence` and `quarantine_below_confidence`

### Outcomes

| Result | Action |
| --- | --- |
| `accepted` | Candidate eligible for promotion into live sources |
| `below_promotion_threshold` | Quarantine; retry later |
| `aggregator_denylist` | Permanent reject |
| `low_confidence` | Quarantine |

Quarantined records include `issues[]` for operator review.

## Confidence scoring (summary)

| Signal | Typical boost |
| --- | --- |
| Seed entry | 1.0 (bypass) |
| Platform + tenant detected | ≥ 0.8 |
| Platform only | ≥ 0.65 |
| JSON-LD JobPosting | ≥ 0.7 |
| HTTPS | +0.05 |

## Operator commands

```bash
cd engine
uv run openroleradar discover          # GitHub + career inspection
uv run openroleradar discover --no-github
uv run openroleradar validate            # Report seed + state summary
uv run openroleradar inspect-source <id>
```

## Promotion policy

Automated discovery **does not** silently edit `config/sources.yml`. High-confidence candidates are stored in live state and polled by the sync orchestrator. Seeds remain the human-audited baseline for well-known employers.

To propose a permanent seed entry, use the **Add career source** issue template or open a PR.

## Related documents

- [CRAWLING_POLICY.md](CRAWLING_POLICY.md)
- [OPERATIONS.md](OPERATIONS.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
