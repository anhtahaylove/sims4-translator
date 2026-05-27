# Release Notes Workflow

This project uses a small changeset-inspired workflow for public releases. It
does not use the Node.js `changesets` package because this is a single Python
desktop app, not an npm monorepo.

## Add A Changeset

For every release-worthy change, add a Markdown file under `changes/`:

```md
Version: 2.2.19
Category: Changed

- Explain why this release exists and what users or maintainers gain.
```

Use a filename that starts with the target version, for example:

```text
changes/v2.2.19-release-notes.md
```

Allowed categories are:

- `Added`: new user-facing capability.
- `Changed`: changed behavior, workflow, or UI.
- `Fixed`: bug fix or regression fix.
- `Security`: trust, signing, provenance, or vulnerability-relevant change.
- `Docs`: documentation-only release reason.
- `Build`: release engineering, CI, packaging, or verification change.

## Prepare A Release

Before tagging, generate the changelog section and release notes:

```powershell
python scripts\collect_release_notes.py --version 2.2.19 --write-changelog --output build\release-notes\v2.2.19.md
```

This command updates `CHANGELOG.md`, writes a GitHub-ready release notes file,
and archives active changesets to `changes/archive/v2.2.19/`.

## Release Guard

The release workflow and `scripts\check_release.ps1` fail if no changeset exists
for the target version. GitHub Release notes are generated from the committed
changesets and then combined with the standard checksum, immutable release
attestation, GitHub artifact attestation, and cosign verification guidance.
