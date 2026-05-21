# Contributing

Thanks for improving The Sims 4 Translator Plus.

This fork prioritizes correctness, package-format compatibility, and a stable
desktop translation workflow. Keep changes small, testable, and easy to review.

## Development Workflow

1. Start from a clean branch.
2. Keep behavioral fixes separate from visual/docs changes.
3. Add or update regression tests before changing risky package, export, save,
   finalize, dedupe, import, or async behavior.
4. Do not commit generated `.package` smoke artifacts from `build/`.
5. Do not push release branches until the checks below pass.

Use Python 3.12 for source and release-build work. Install dev/build tools with:

```powershell
python -m pip install -r requirements-dev.txt -c constraints.txt
```

## Required Checks

Run the fast repository check from the repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_fast.ps1
```

That script runs the unit suite, compile checks, focused lint when Ruff is
installed, synthetic package generation, package-only smoke verification,
version-sync checks, Markdown link/image checks, and `git diff --check`.

You can also run individual checks while debugging:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q models packer singletons storages themes utils widgets windows tests scripts main.py
python scripts\create_synthetic_package.py
python scripts\verify_synthetic_smoke.py --directory build\synthetic
python scripts\verify_version_sync.py --version 2.0.0
git diff --check
```

Strict GUI export verification belongs to release preparation. Run the app,
load `build/synthetic/synthetic_smoke.package`, export the supported formats,
then run `scripts\check_release.ps1`.

## UI Guidelines

- Keep the workspace data-table-first.
- Make loading, disabled, hover, pressed, and focus states obvious.
- Avoid official EA, Maxis, or The Sims artwork and branding assets.
- Keep the app readable for long translation sessions.
- Preserve keyboard shortcuts and existing workflows unless a change is planned
  and tested.

## Release Notes

For public release work, follow `docs/release-checklist.md`.
