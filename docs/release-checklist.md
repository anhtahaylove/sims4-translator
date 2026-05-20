# Vietnamese Release Checklist

Use this checklist before publishing a Vietnamese package or a public app build.

## Recommended VI_VN Workflow

- Keep source language as `ENG_US` and destination as `VI_VN`.
- Work from copied packages or workspace files. Do not write directly into the game/DLC install folders.
- For a Mods-folder release, prefer `Save as package` and place the generated package in `Documents\Electronic Arts\The Sims 4\Mods` for in-game testing.
- Use `Finalize` only when you deliberately want to rewrite a package with destination STBL resources. Keep `Create backup before Finalize` enabled.

## Conflict-Free Save Mode

Leave `Use conflict-free save mode (experimental)` off by default for full game/DLC Vietnamese releases.

That mode creates alternate output resources to avoid collisions. It can be useful for isolated compatibility testing, but a full translation release usually needs predictable destination STBL resources. With millions of strings and instances, alternate resources can make it harder to reason about load order and blank-text failures.

## DeepL Setup

- Add the DeepL API key in Options.
- Use `Test key` before translating. It calls DeepL usage/quota and does not spend translation characters.
- Use `Check usage` before large batch jobs.
- Optional glossary ID is only needed if you created a glossary in DeepL and want terms such as `Trait`, `Lot`, or `Moodlet` translated consistently.
- Batch Translate with DeepL should show the estimated character count before starting.

## Pre-release Validation Report

Run `Validate Release...` before publishing and review the report.

- `Soft release`: good for normal workflow checks. Untranslated, Draft, and Needs review records are warnings.
- `Strict release`: good for public release checks. Untranslated, Draft, and Needs review records are critical.
- Critical token issues can still be continued deliberately, but should normally be fixed before publishing.
- Export the report as `.txt` or `.csv` if the release needs a QA record.

## Large Package Manual QA

Use a real large package/DLC when available. If not available, use an ignored temporary package under `build\visual-qa`.

Create the fallback package from the repo root:

```powershell
python scripts\create_visual_qa_package.py --records 100000 --resources 4
```

Pass criteria:

- Loading a large package finishes and table rows remain visible after resize.
- Hybrid `Open` adds a second package when one is already loaded.
- Search finds records by ID, Original, or Translated text.
- Filters show correct counts for `All`, `Untranslated`, `Approved`, and `Needs review`.
- `Package`, `Instance`, `Modified only`, and `Clear filters` do not reset unexpectedly.
- Selection Preview shows long Vietnamese text and Sims tokens without overlapping controls.
- Editor token highlighting and soft-confirm warning work for Approve and Needs Review.
- Batch Translate shows the DeepL cost guard before sending a large job.
- Pre-release Validation Report remains readable and does not freeze the app for large inputs.
- Activity Dock visible/hidden/expanded state persists after restart.
- Export, Save as package, and Finalize still run the validation gate before writing.

Fail criteria:

- Blank table after load or resize.
- Lost selection/filter state after resize.
- Clipped primary buttons or unreadable contrast.
- Validation cancellation still opens a report or starts a write.
- Export/Save/Finalize writes files before validation completes.

## Build Verification

Run the release build script from the repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

The script should verify tests, compileall, synthetic smoke, PyInstaller output layout, startup smoke, and generated package outputs. Do not commit `build/`, `dist/`, generated `.package` files, local dictionaries, or generated `.spec` files.

## Repository Release Hygiene

- Keep `LICENSE`, `NOTICE.md`, font licenses, and non-affiliation disclaimer.
- Do not use official EA, Maxis, or The Sims artwork, logos, fonts, or copied UI assets.
- Commit only reviewed source, resource, docs, and test changes.
- Exclude `.understand-anything/*`, `graphify-out/*`, `build/*`, and `dist/*` from release commits unless a future batch explicitly scopes those artifacts.
