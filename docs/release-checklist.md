# Release Checklist

Use this checklist before publishing a public fork release.

## Repository

- Repo name: `sims4-translator`
- Public display name: `The Sims 4 Translator Plus`
- Suggested description: `Community-maintained desktop translator for The Sims 4 mod package strings.`
- Suggested topics: `sims4`, `the-sims-4`, `modding`, `translation`, `localization`, `pyside6`, `stbl`, `desktop-app`
- Confirm `origin` points to upstream and `fork` points to `anhtahaylove/sims4-translator`.

## Legal And Attribution

- Keep `LICENSE`.
- Keep `NOTICE.md`.
- Verify README non-affiliation disclaimer is visible near the top.
- Verify font license files are included.
- Do not use official EA, Maxis, or The Sims artwork in generated assets.

## Verification

Run:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q models packer singletons storages themes utils widgets windows tests scripts
python scripts\create_synthetic_package.py
python scripts\verify_synthetic_smoke.py --directory build\synthetic --require-gui-outputs
```

Manual GUI smoke:

- Load `build/synthetic/synthetic_smoke.package`.
- Confirm only `Hello` and `World` appear as unique rows.
- Export STBL, XML, XML-DP, JSON, Binary, and Translation Hub CSV.
- Test Save As and Finalize As.
- Cancel a long-running translation/export where possible.
- Check the TS4 Plus Balanced theme in the main workspace, dialogs, and dictionaries view.
- Check focus rings, disabled buttons, table readability, and Job Drawer logs.

## Release Artifact Hygiene

- Do not track `build/`, `.package`, `.tmp`, `.backup`, or local dictionary files.
- Include `README.md`, `README.vi.md`, `LICENSE`, `NOTICE.md`, and font licenses in binary archives.
- Draft release notes with user-facing changes and known limitations.
- Do not publish until the release branch has been reviewed.
