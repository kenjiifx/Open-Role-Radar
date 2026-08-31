# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| `main` branch | Yes |
| Tagged releases | Yes |
| Older forks | Best effort |

## Reporting a vulnerability

**Please do not open public GitHub issues for security vulnerabilities.**

Email maintainers with:

1. Description of the issue and impact
2. Steps to reproduce (proof-of-concept if available)
3. Affected components (engine, site, workflows)
4. Your contact information for follow-up

We aim to acknowledge reports within **5 business days** and provide a remediation timeline when confirmed.

## Scope

In scope:

- SSRF or request smuggling in the HTTP client
- Secrets committed to the repository
- GitHub Actions permission escalation
- Unsafe deserialization or code execution in the engine
- XSS or injection in the static site

Out of scope:

- Individual job posting content (report via **Report incorrect job** template)
- Third-party ATS availability or rate limits
- Social engineering

## Safe harbor

We support good-faith security research that:

- Avoids privacy violations and data destruction
- Limits testing to your own accounts or clearly identified test sources
- Follows [CRAWLING_POLICY.md](docs/CRAWLING_POLICY.md)

## Automated scanning

This repository runs CodeQL and dependency review on pull requests. See `.github/workflows/security.yml`.

## Dependency updates

Dependabot opens weekly PRs for Python, npm, and GitHub Actions dependencies.
