# Static API

OpenRoleRadar publishes a **read-only static JSON API** on GitHub Pages. No authentication is required. Data is regenerated on each successful sync workflow.

**Base URL:** `https://kenjiifx.github.io/Open-Role-Radar/api/v1/`

Local paths after `openroleradar build-data`: `site/public/api/v1/`

## Versioning

| Artifact | Version field |
| --- | --- |
| API layout | `config/project.yml` → `versions.static_api` |
| Job records | `versions.job_schema` |
| Export manifest | `meta.json` → `schema_version` |

Breaking changes increment schema versions and are documented in release notes.

## Endpoints

### `GET /api/v1/meta.json`

Dataset metadata and counts.

```json
{
  "schema_version": 1,
  "generated_at": "2026-08-31T12:00:00+00:00",
  "job_count": 1240,
  "company_count": 42,
  "source_count": 48,
  "event_count": 3500,
  "project": {
    "name": "OpenRoleRadar",
    "slug": "openroleradar",
    "website_url": "https://kenjiifx.github.io/Open-Role-Radar/"
  },
  "versions": { "job_schema": 1, "company_schema": 1 }
}
```

### `GET /api/v1/companies.json`

Map of `company_id` → [Company](DATA_MODEL.md#company) record.

### `GET /api/v1/sources.json`

Map of `source_id` → [Source](DATA_MODEL.md#source) record.

### `GET /api/v1/jobs/index.json`

Array of lightweight index entries for open/reopened jobs:

```json
[
  {
    "job_id": "abc123...",
    "company_id": "def456...",
    "title": "Software Engineering Intern",
    "career_level": "internship",
    "bucket": "07"
  }
]
```

### `GET /api/v1/jobs/shard/{bucket}.json`

Hashed job shards containing full [Job](DATA_MODEL.md#job) objects. Bucket IDs are zero-padded two-digit hex (`00`–`1f` by default, 32 buckets).

Sharding limits individual file size (`config/project.yml` → `sharding.max_shard_bytes`, `max_shard_jobs`).

### `GET /api/v1/events.json` (when exported)

Recent lifecycle [events](DATA_MODEL.md#event). May be truncated in public builds.

## Feeds

Atom and RSS feeds are published under `/feeds/`:

| Feed | Path |
| --- | --- |
| Early-career (all) | `/feeds/early-career.atom` |
| New listings | `/feeds/new.atom` |

Configure `feeds.max_items` in `project.yml` (default 500).

## CORS and caching

GitHub Pages serves files with public cache headers. Consumers should:

- Poll `meta.json` for `generated_at` before full re-downloads
- Cache shards by bucket locally
- Use ETag support from your HTTP client when re-fetching

## JSON Schema validation

Validate records against files in `schemas/`:

```bash
pip install check-jsonschema
check-jsonschema --schemafile schemas/job.schema.json site/public/api/v1/jobs/shard/00.json
```

## Example: fetch a job by ID

```python
import json
import urllib.request

META = "https://kenjiifx.github.io/Open-Role-Radar/api/v1/meta.json"
INDEX = "https://kenjiifx.github.io/Open-Role-Radar/api/v1/jobs/index.json"

index = json.load(urllib.request.urlopen(INDEX))
entry = next(j for j in index if j["job_id"] == TARGET_ID)
shard_url = f"https://kenjiifx.github.io/Open-Role-Radar/api/v1/jobs/shard/{entry['bucket']}.json"
shard = json.load(urllib.request.urlopen(shard_url))
job = shard[TARGET_ID]
```

## Rate limits

There is no API key. Please cache responses and avoid hammering Pages during sync windows (every 15 minutes, offset). For high-volume use, mirror the static files to your own storage.

## Related documents

- [DATA_MODEL.md](DATA_MODEL.md)
- [OPERATIONS.md](OPERATIONS.md)
