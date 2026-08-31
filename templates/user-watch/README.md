# OpenRoleRadar Personal Watch

Run your own lightweight job alert using the **public** OpenRoleRadar Atom feed—no API keys required.

## Quick start

1. Copy `workflow.yml` into your repository at `.github/workflows/openroleradar-watch.yml`.
2. (Optional) Add repository variables under **Settings → Secrets and variables → Actions → Variables**:
   - `ORR_FEED_URL` — defaults to `https://kenjiifx.github.io/Open-Role-Radar/feeds/early-career.atom`
   - `ORR_KEYWORDS` — comma-separated terms, e.g. `backend,python,remote`
   - `ORR_LOCATIONS` — comma-separated location hints, e.g. `london,berlin,remote`
3. Create a label named `openroleradar-watch` (or edit the workflow).
4. Adjust the `schedule` cron expression to your preferred frequency.

## How it works

The workflow downloads the published Atom feed, filters entries locally in a short Python script, and opens a GitHub issue when matches are found. It uses **read-only** `contents` permission plus `issues: write` to notify you.

## Privacy and security

- No OpenRoleRadar secrets are needed.
- The workflow only reads public feed URLs.
- Forks of OpenRoleRadar itself do not execute this template automatically.

## Customization ideas

- Send matches to Slack or email using your own secrets.
- Diff against a cached `last_seen.txt` artifact to report only new roles.
- Combine with GitHub's `workflow_dispatch` for manual checks before interviews.

See also: [docs/OPERATIONS.md](../../docs/OPERATIONS.md) and the reference template at [.github/workflows/user-watch-template.yml](../../.github/workflows/user-watch-template.yml).
