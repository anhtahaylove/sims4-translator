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

## Required Checks

Run the full unit suite:

```powershell
python -m unittest discover -s tests -v
```

Run compile checks:

```powershell
python -m compileall -q models packer singletons storages themes utils widgets windows tests scripts
```

Generate and verify a synthetic package:

```powershell
python scripts\create_synthetic_package.py
python scripts\verify_synthetic_smoke.py --directory build\synthetic --require-gui-outputs
```

The verifier requires GUI export artifacts. Run the app, load
`build/synthetic/synthetic_smoke.package`, export the supported formats, then
run the verifier.

## UI Guidelines

- Keep the workspace data-table-first.
- Make loading, disabled, hover, pressed, and focus states obvious.
- Avoid official EA, Maxis, or The Sims artwork and branding assets.
- Keep light and dark themes readable for long translation sessions.
- Preserve keyboard shortcuts and existing workflows unless a change is planned
  and tested.

## Release Notes

For public release work, follow `docs/release-checklist.md`.
