# Security Policy

## Reporting a Vulnerability

Please report security issues privately before opening a public issue.

- Use GitHub Security Advisories if available for this repository.
- If advisories are not available, open a minimal issue asking for a private contact path without sharing exploit details.

## Sensitive Data

The app can store local preferences such as a DeepL API key. Do not include API keys,
private package contents, personal file paths, or unreleased mod files in public issues.

When sharing logs or screenshots:

- Remove DeepL API keys and tokens.
- Remove private Windows usernames or personal paths if they matter.
- Share only the minimum package/export context needed to reproduce the problem.
- App logs live under `%APPDATA%\The Sims 4 Translator Plus\logs\app.log`; API keys are redacted before writing, but review the file before posting it publicly.

## Supported Versions

Security fixes target the latest public release and the current `main` branch.

## Project Scope

This project is a community desktop localization tool. It is not affiliated with,
endorsed by, sponsored by, or connected to Electronic Arts, Maxis, or The Sims.
