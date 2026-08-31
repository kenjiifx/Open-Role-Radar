# Crawling Policy

OpenRoleRadar fetches **public** employer career data with conservative rate limits and clear identification. This document describes how the engine behaves and what contributors must respect.

## Scope

We crawl:

- Public ATS job board APIs and HTML pages linked from corporate domains
- URLs discovered through GitHub public search and Common Crawl indexes
- JSON-LD `JobPosting` blocks on first-party career sites

We do **not** crawl:

- Logged-in or paywalled areas
- Job aggregators (LinkedIn, Indeed, Glassdoor, etc.)
- Personal data, applicant tracking internals, or non-job endpoints

## Identification

Every request sends the User-Agent from `config/project.yml`:

```
OpenRoleRadar/1.0 (+https://github.com/kenjiifx/Open-Role-Radar)
```

## Rate limiting

HTTP settings (`config/project.yml` → `http`):

| Setting | Default | Purpose |
| --- | --- | --- |
| `global_concurrency` | 20 | Max parallel requests |
| `per_host_concurrency` | 3 | Per-host fairness |
| `timeout_seconds` | 30 | Hard request timeout |
| `max_redirects` | 5 | Redirect cap |
| `max_response_bytes` | 10 MB | Response size limit |
| `retry_max_attempts` | 3 | Exponential backoff retries |

Poll tiers (`polling.tiers`) space out repeat visits:

| Tier | Interval |
| --- | --- |
| hot | 15 minutes |
| warm | 60 minutes |
| cold | 6 hours |
| dormant | 24 hours |

`max_sources_per_sync` (200) and `max_sync_runtime_minutes` (45) prevent runaway CI jobs.

## Conditional requests

Sources store `etag` and `last_modified` when adapters support them, reducing bandwidth on unchanged boards.

## Robots and terms

- Prefer official ATS APIs where available (Greenhouse, Lever, Ashby public boards).
- Do not circumvent authentication, CAPTCHAs, or explicit `noindex` signals on non-API pages.
- If an employer requests removal, disable the source (`enabled: false`) and open an issue documenting the request.

## Error handling

| HTTP code | Behavior |
| --- | --- |
| 2xx | Parse and normalize |
| 404 / 410 on job URL | Authoritative close (see `closure.authoritative_status_codes`) |
| 429 / 503 | Back off, mark source `degraded` |
| Repeated failures | Increment `consecutive_failures`, downgrade health, eventually `failing` |

Unhealthy sources do not automatically close existing jobs when `lifecycle.unhealthy_source_never_closes` is enabled—preventing mass false closures during outages.

## SSRF protection

Validation resolves hostnames and rejects private, loopback, link-local, and reserved addresses before any seed is accepted. PR validation runs the same checks in `scripts/validate-sources.py`.

## Data retention

- Live state rotates through CI cache; not committed to git.
- Monthly archives compress historical snapshots for research (see `archive.yml`).
- Published site/API only includes normalized job JSON—never raw HTML dumps.

## Reporting abuse

If you operate a careers site and want OpenRoleRadar to adjust crawl behavior, email the maintainers via the security contact in [SECURITY.md](../SECURITY.md) or open a **Broken source** issue.

## Related documents

- [SOURCE_DISCOVERY.md](SOURCE_DISCOVERY.md)
- [OPERATIONS.md](OPERATIONS.md)
