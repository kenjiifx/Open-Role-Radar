# Data License

OpenRoleRadar publishes structured metadata derived from **public** employer career postings. This document clarifies how that data may be used.

## What we publish

- Normalized job titles, locations, URLs, and classification fields
- Employer names and domains
- Evidence excerpts (short quotes) supporting mobility/eligibility signals
- Aggregated statistics and feeds

We do **not** republish full job descriptions, proprietary HTML, or applicant data.

## Source material

Job facts originate from first-party ATS boards and career pages operated by employers. Those materials may be protected by copyright and subject to the employer's terms of use.

OpenRoleRadar:

- Links every job to its canonical `job_url` and `apply_url`
- Stores only short `summary` text (≤1000 characters) and ≤500 character evidence excerpts
- Encourages users to read official postings before applying

## License grant

The **OpenRoleRadar project code** is licensed under the [MIT License](LICENSE).

**Exported JSON datasets, feeds, and archives** produced by this project are made available for:

- Personal job search and alerting
- Academic and journalistic research
- Open-source tools that link back to official postings

Commercial redistribution of bulk datasets (e.g. reselling listings) is discouraged without independent verification against source terms.

## Attribution

When reusing OpenRoleRadar data, please attribute:

> Data aggregated by [OpenRoleRadar](https://github.com/kenjiifx/Open-Role-Radar)

Include `generated_at` from `api/v1/meta.json` when mirroring snapshots.

## Takedown requests

Employers may request source disablement or data correction by contacting maintainers (see [SECURITY.md](SECURITY.md)) or opening a **Broken source** / **Report incorrect job** issue.

## No warranty

Published data is provided **as-is** without guarantee of completeness, accuracy, or timeliness. Always confirm details on the employer's official careers page before applying.
