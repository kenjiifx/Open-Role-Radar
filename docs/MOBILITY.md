# Mobility Signals

OpenRoleRadar extracts **mobility benefits**—visa sponsorship, relocation support, and international candidate friendliness—from job descriptions using rule-based evidence extraction.

## Motivation

Early-career candidates relocating internationally need to know whether an employer sponsors visas or funds relocation. Aggregator sites often omit or bury this information. OpenRoleRadar surfaces it as structured, citeable claims.

## Schema

Mobility data lives on each `Job` under `mobility` (see `schemas/job.schema.json`). Every benefit is an `EvidenceClaim`:

| Field | Description |
| --- | --- |
| `status` | `confirmed`, `not_available`, `unknown`, `not_applicable` |
| `confidence` | 0.0–1.0 model confidence |
| `extraction_rule` | Which rule matched (for debugging) |
| `evidence_excerpt` | ≤500 char quote from the posting |

### Tracked benefits

| Key | Examples in text |
| --- | --- |
| `visa_sponsorship` | "visa sponsorship", "H-1B", "work permit" |
| `immigration_assistance` | "immigration support", "relocation visa" |
| `international_candidates` | "open to international applicants" |
| `relocation_assistance` | "relocation package", "moving assistance" |
| `relocation_stipend` | "relocation bonus" |
| `moving_expenses` | "moving expenses covered" |
| `airfare` | "flight reimbursement" |
| `travel_reimbursement` | "travel expenses" |
| `housing_provided` | "company housing" |
| `housing_stipend` | "housing allowance" |
| `temporary_housing` | "temporary accommodation" |
| `fully_funded_relocation` | "fully funded relocation" |

## Interpretation guide

### `confirmed`

A rule matched with sufficient confidence and an excerpt was captured. **Always verify** against the live posting before making relocation decisions—employers change policies.

### `not_available`

Explicit negative language detected (e.g. "unable to sponsor visa").

### `unknown`

No signal either way. **Does not mean sponsorship is unavailable.**

### `not_applicable`

Role is clearly local-only or internship structure makes the benefit irrelevant (e.g. on-campus co-op).

## Confidence thresholds

Classification settings in `config/project.yml`:

- `early_career_min_confidence` — minimum to treat a role as early-career
- `quarantine_below_confidence` — jobs below this may be quarantined entirely

Mobility claims inherit extraction confidence from pattern strength and context (negation detection, section headers).

## Limitations

- English-centric keyword rules; multilingual postings may be incomplete.
- Benefits may apply only to full-time conversions, not internships—read excerpts carefully.
- Government/defense roles may omit sponsorship details for compliance reasons.

## API consumption

Filter jobs in client code:

```javascript
const sponsored = jobs.filter(
  (j) => j.mobility?.visa_sponsorship?.status === "confirmed"
);
```

Atom feeds include summary text; use the static API for full mobility objects.

## Improving extraction

Open a PR adjusting rules in the classification modules or file a **Report incorrect job** issue with the official posting URL and correct mobility status.

## Related documents

- [DATA_MODEL.md](DATA_MODEL.md)
- [ELIGIBILITY.md](ELIGIBILITY.md)
