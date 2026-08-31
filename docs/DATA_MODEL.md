# Data Model

OpenRoleRadar exports four primary record types, each defined by a JSON Schema in `schemas/` and implemented as Pydantic models in `engine/src/openroleradar/models/`.

## Identifiers

All public IDs are truncated SHA-256 hashes of canonical inputs:

| Entity | Input parts | Example |
| --- | --- | --- |
| `company_id` | `company`, domain | `deterministic_id("company", "stripe.com")` |
| `source_id` | domain, adapter, tenant | `deterministic_id("source", "stripe.com", "greenhouse", "stripe")` |
| `job_id` | source_id, source_job_id | Derived during normalization |

This makes IDs stable across machines and reproducible from `config/sources.yml` seed entries.

## Job

The central record. A `Job` combines listing metadata, classification output, eligibility/mobility enrichment, and provenance.

### Key fields

| Field | Description |
| --- | --- |
| `title`, `summary` | Human-readable listing text |
| `career_level` | Internship, new grad, co-op, etc. |
| `employment_type` | Full-time, internship, contract, … |
| `locations` | Structured geo objects with raw fallback |
| `workplace_type` / `remote_scope` | Onsite, hybrid, remote and geographic limits |
| `compensation` | Parsed pay range when present |
| `education` | Degree level, graduation years, majors |
| `eligibility` | Work authorization and country constraints |
| `mobility` | Visa/relocation evidence claims |
| `provenance` | Adapter, fetch time, content hash |
| `lifecycle` | `open`, `suspected_closed`, `closed`, `reopened`, `quarantined` |

### Evidence claims

Mobility fields use `EvidenceClaim` objects:

```json
{
  "status": "confirmed",
  "confidence": 0.92,
  "extraction_rule": "keyword:visa_sponsorship",
  "evidence_excerpt": "We provide visa sponsorship for eligible candidates."
}
```

Statuses: `confirmed`, `not_available`, `unknown`, `not_applicable`.

### Lifecycle rules

Configured in `config/project.yml`:

- After **N consecutive misses** on sync, a job becomes `suspected_closed`.
- After **M misses**, it becomes `closed`.
- HTTP `404` / `410` on the listing URL can authoritatively close a role.
- Unhealthy sources do not auto-close jobs when `unhealthy_source_never_closes` is true.

## Company

Aggregated employer metadata:

- `canonical_domain` — primary corporate domain
- `careers_urls` — known first-party landing pages
- `ats_sources` — adapters observed for this employer
- `active_job_count` / `historical_job_count` — export-time counters

## Source

A polled ATS endpoint:

| Field | Description |
| --- | --- |
| `adapter` / `adapter_tenant` | Which integration and board slug |
| `discovered_via` | `seed`, `github`, `common_crawl`, `career_site`, `manual` |
| `discovery_confidence` | 0–1 promotion score |
| `poll_tier` | `hot`, `warm`, `cold`, `dormant` |
| `health_status` | `healthy`, `degraded`, `failing`, `blocked`, … |
| `enabled` | Whether sync should poll this source |

Seed sources in `config/sources.yml` are converted to `Source` records with `discovered_via: seed` and confidence `1.0`.

## Event

Append-only lifecycle log entries:

| `event_type` | Meaning |
| --- | --- |
| `OPENED` | First time a job_id appears |
| `UPDATED` | Content hash changed |
| `CLOSED` | Role closed or aged out |
| `REOPENED` | Previously closed role returned |

`changed_fields` lists top-level keys that differ between hashes on `UPDATED` events.

## Schema files

| File | Version key (`project.yml`) |
| --- | --- |
| `schemas/job.schema.json` | `job_schema` |
| `schemas/company.schema.json` | `company_schema` |
| `schemas/source.schema.json` | `source_schema` |
| `schemas/event.schema.json` | `event_schema` |

Validate exported JSON in CI or research notebooks with any Draft 2020-12 validator.

## LiveState container

The on-disk state bundles:

- `jobs: dict[str, Job]`
- `companies: dict[str, Company]`
- `sources: dict[str, Source]`
- `events: list[JobEvent]`
- `generated_at`, `schema_version`

Exporters read `LiveState` and write public artifacts; the site never reads `.local/state` directly in production—only built `site/public/` files.

## Related documents

- [MOBILITY.md](MOBILITY.md)
- [ELIGIBILITY.md](ELIGIBILITY.md)
- [API.md](API.md)
