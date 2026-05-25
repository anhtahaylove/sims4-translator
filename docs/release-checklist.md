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

## Community Tester Feedback

Before a public app announcement, ask 2-3 testers to try a copied real package and record:

- Whether the first-run flow is clear: Open package, Translate, Validate Release, Save as package.
- Any Vietnamese UI wording that feels awkward, unclear, or too technical.
- Any clipped text, overlapping controls, or unreadable warnings at 900px, 1366x768, and fullscreen.
- Whether Editor token warnings make sense before Approve or Needs Review.
- Whether Validate Release and Save as package are easy to find without reading the full README.

## Build Verification

Run the fast clean-checkout verification from the repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_fast.ps1
```

Run the release build script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

The build script must work from a clean checkout. It verifies tests, compileall,
package-only synthetic smoke, PyInstaller output layout, and startup smoke. It
must not require GUI export artifacts before it can build.

For strict release QA after manual GUI exports exist, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_release.ps1 -Version 2.2.2
```

Do not commit `build/`, `dist/`, generated `.package` files, local dictionaries,
generated `.spec` files, release ZIPs, or checksum files.

GitHub Actions can also build release artifacts from a clean runner. Use the
`Release Build` workflow manually with a version such as `2.2.2`, or push a
`vX.Y.Z` tag. The workflow uploads the Windows ZIP, `.sha256`, and
`.sigstore.json` as workflow artifacts. For tags, it also publishes those
assets to the matching GitHub Release.

## Documentation And Asset Checks

- Confirm `README.md` and `README.vi.md` still describe the same core workflow.
- Check all relative Markdown links and image paths before publishing.
- Check English/Vietnamese screenshot parity: same feature order, localized app screenshots where available, shared diagrams where language-specific diagrams would add maintenance risk.
- Keep evergreen download instructions pointed at the latest release instead of a hard-coded ZIP version.
- Confirm README screenshots use generated/synthetic app data only, not official game screenshots or artwork.
- Confirm screenshots contain no private paths, API keys, real user data, or real mod/package names that should not be public.
- Confirm generated or AI-assisted visuals are documented in `docs/assets/readme/IMAGE-SOURCES.md`.
- Confirm README image file sizes are reasonable for GitHub rendering.
- Confirm the release ZIP name follows `The-Sims-4-Translator-Plus-vX.Y.Z-windows.zip`.

Example image/link check:

```powershell
@'
from pathlib import Path
import re

files = [Path("README.md"), Path("README.vi.md"), Path("docs/README.md"), Path("docs/release-checklist.md")]
missing = []
for md in files:
    text = md.read_text(encoding="utf-8")
    for target in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', text):
        if target.startswith(("http://", "https://")):
            continue
        if not (md.parent / target).resolve().exists():
            missing.append(f"{md}: {target}")
    for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', text):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        clean = target.split("#")[0]
        if clean and not (md.parent / clean).exists():
            missing.append(f"{md}: {target}")
if missing:
    raise SystemExit("\n".join(missing))
print("Markdown links and images OK")
'@ | python -
```

## Release ZIP Checksums

Publish a SHA256 checksum beside the Windows ZIP. After building, package the
release artifact and checksum with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\package_release.ps1 -Version 2.2.2 -Force
```

Maintainer example:

```powershell
Get-FileHash .\The-Sims-4-Translator-Plus-vX.Y.Z-windows.zip -Algorithm SHA256
```

User verification example after download:

```powershell
Get-FileHash .\The-Sims-4-Translator-Plus-vX.Y.Z-windows.zip -Algorithm SHA256
```

Compare the displayed hash with the published `.sha256` file.

Source checkout verification:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_release_download.ps1 -Latest
```

Advanced provenance verification for GitHub Actions-built releases:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_release_download.ps1 -Latest -VerifyProvenance
```

For public user and moderator-facing verification guidance, keep
[trust-and-safety.md](trust-and-safety.md) linked from the README files.

## Antivirus False-Positive Review

If a release is flagged by a small number of static or ML antivirus engines,
prepare evidence before contacting vendors:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\collect_false_positive_evidence.ps1 -Version 2.2.2
```

Attach or paste the generated `vendor-submission-template.txt` content into
vendor review forms. Do not upload the local evidence folder to git, and do not
store VirusTotal API keys in the repo.

See [false-positive-submissions.md](false-positive-submissions.md) for wording,
vendor notes, and what not to claim.

## Windows Signing

The executable is currently unsigned, so Windows SmartScreen may warn users on
first run. Do not block release on signing unless a trusted certificate is
available. When signing is added, sign the built EXE before packaging, then
generate the final ZIP and `.sha256` after signing.

See [code-signing.md](code-signing.md) for the safe signing path and secret
handling rules.

## CI And Release Guards

- Windows CI should run `scripts\check_fast.ps1` on Python 3.12.
- The `Release Build` workflow should produce a ZIP and `.sha256` artifact from a clean runner.
- The `Release Build` workflow should generate GitHub Artifact Attestations and a cosign `.sigstore.json` bundle.
- `scripts\verify_version_sync.py --version 2.2.2` should pass before tagging.
- `scripts\verify_interface_i18n.py --language vi_VN --version 2.2.2` should pass before release packaging.
- GitHub release assets should include the Windows ZIP, matching `.sha256`, and matching `.sigstore.json`.
- GitHub issue templates and `SECURITY.md` should remain present before public release.

## Repository Release Hygiene

- Keep `LICENSE`, `NOTICE.md`, font licenses, and non-affiliation disclaimer.
- Do not use official EA, Maxis, or The Sims artwork, logos, fonts, or copied UI assets.
- Commit only reviewed source, resource, docs, and test changes.
- Exclude `.understand-anything/*`, `graphify-out/*`, `build/*`, and `dist/*` from release commits unless a future batch explicitly scopes those artifacts.
- GitHub repository metadata should stay user-friendly:
  - Description: `Desktop translation studio for The Sims 4 package/STBL localization.`
  - Topics: `sims4`, `sims-4`, `the-sims-4`, `ts4`, `translation`, `localization`, `stbl`, `package`, `pyside6`, `modding`.
