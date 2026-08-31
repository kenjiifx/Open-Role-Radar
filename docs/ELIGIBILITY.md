# Eligibility Signals

Eligibility captures **who may apply** based on work authorization, geography, citizenship, clearance, and language requirements extracted from first-party postings.

## Schema overview

Each `Job` includes an `eligibility` object:

| Field | Description |
| --- | --- |
| `work_authorization` | Free-text summary when structured parsing is insufficient |
| `explicit_allowed_countries` | Countries explicitly welcomed |
| `explicit_excluded_countries` | Countries explicitly excluded |
| `citizenship_requirements` | Citizenship constraints (e.g. "US citizen") |
| `residency_requirements` | Residency or right-to-work requirements |
| `security_clearance` | Clearance level if stated |
| `export_control_restrictions` | ITAR/EAR or similar flags |
| `language_requirements` | Required languages |
| `origin_match` | `explicit_match`, `potential_match`, `unknown`, `explicitly_ineligible` |

See `schemas/job.schema.json` for full types.

## `origin_match` semantics

| Value | Meaning |
| --- | --- |
| `explicit_match` | Posting explicitly allows the user's origin scenario |
| `potential_match` | Soft language ("must be eligible to work") without country lists |
| `unknown` | No eligibility language detected |
| `explicitly_ineligible` | Posting clearly excludes the scenario (e.g. "US citizens only" for a non-US query) |

Client-side filters should treat `unknown` as **requires manual review**, not as eligible.

## Relationship to mobility

| Concept | Question answered |
| --- | --- |
| **Eligibility** | Are you allowed to apply given your current status? |
| **Mobility** | Will the employer help you relocate or obtain authorization? |

A role can be `explicitly_ineligible` for visa holders while still mentioning relocation for domestic candidates—or vice versa.

## Remote scope interaction

`remote_scope` and `remote_allowed_countries` describe **where work may be performed**. Eligibility describes **who may apply**. Both fields are needed for accurate international remote filtering.

Example: "Remote within Canada" + "Must be legally authorized to work in Canada" → align remote and eligibility filters on `CA`.

## Extraction approach

1. Pattern libraries for citizenship, authorization, and country lists
2. ISO country normalization via `pycountry` where possible
3. Negation handling ("not able to sponsor" vs "open to OPT")
4. Confidence rolled into `origin_match` and job-level quarantine decisions

## Limitations

- Legal language is nuanced; automated extraction is not legal advice.
- Postings may defer authorization questions to recruiters.
- Defense contractors often use boilerplate that overlaps export control and citizenship rules.

## Reporting errors

Use the **Report incorrect job** issue template with the official URL and the correct eligibility interpretation.

## Related documents

- [MOBILITY.md](MOBILITY.md)
- [DATA_MODEL.md](DATA_MODEL.md)
- [API.md](API.md)
