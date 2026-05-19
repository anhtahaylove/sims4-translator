# The Sims 4 Translator Plus

**The Sims 4 Translator Plus** is a community-maintained fork of
[voky1/sims4-translator](https://github.com/voky1/sims4-translator), a desktop
tool for translating The Sims 4 mod package strings.

This fork keeps the original app's package formats and translation workflow,
then adds stability, async job handling, dedupe hardening, synthetic smoke tests,
and a cleaner public release path.

> This project is not affiliated with Electronic Arts, Maxis, The Sims, or the
> upstream maintainer. The Sims 4 is a trademark of its respective owners.

[Vietnamese README](README.vi.md)

## Status

This fork is being prepared as a public open-source release. The current focus is
stabilization and rebrand hygiene before wider distribution.

## What This Tool Does

- Opens The Sims 4 `.package`, `.stbl`, `.xml`, `.json`, and `.binary` translation sources.
- Displays source and translated strings in a desktop workspace.
- Translates from dictionaries and supported online translation engines.
- Saves dictionaries for reuse across mod updates.
- Exports translations as STBL, XML, XML-DP, JSON, Binary, or Translation Hub CSV.
- Saves translated strings as a separate package or finalizes them into a package copy.

## Improvements In This Fork

- Async package loading, dictionary loading, export, save, and finalize workflows.
- UI remains responsive while background jobs run.
- Exact duplicate package strings are skipped instead of imported into the workspace.
- Export/save/finalize paths preserve existing output formats while avoiding duplicate output rows.
- Non-modal job drawer logs for load/import/export/save summaries.
- Synthetic package generator and verifier for GUI smoke testing without real mod files.
- Community Vietnamese destination locale `VI_VN` for Vietnamese fan localization workflows.
- One balanced TS4 Plus desktop theme instead of a split light/dark visual system.
- Regression tests for dedupe, import, translation cancellation, export, save, finalize, and smoke artifacts.

## Install And Run From Source

Requirements:

- Python 3.12+
- Windows is the primary tested desktop target.

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the app:

```powershell
python main.py
```

## Basic Workflow

1. Select source and destination languages in Options. For Vietnamese fan localization, choose `VI_VN` as the destination.
2. Open a mod package or supported translation file.
3. Edit or generate translations.
4. Validate translated rows.
5. Export to the format you need, save a dictionary, save as a new package, or finalize into a package copy.

## Synthetic GUI Smoke Test

If you do not have a real mod package available, generate a deterministic test
package:

```powershell
python scripts\create_synthetic_package.py
```

The package is written to:

```text
build/synthetic/synthetic_smoke.package
```

Open the app, load that package, and confirm the table shows two unique rows:
`Hello` and `World`. Then export the loaded strings as STBL/XML/XML-DP/JSON/Binary/CSV,
and try Save As or Finalize As.

After the manual click-through, verify the generated artifacts:

```powershell
python scripts\verify_synthetic_smoke.py --directory build\synthetic --require-gui-outputs
```

The verifier checks that exports contain only the two unique strings, no duplicate
rows came back, no temporary export files were left behind, and the package still
loads through the normal storage layer with dedupe enabled.

## Development Checks

Run the full regression suite:

```powershell
python -m unittest discover -s tests -v
```

Run compile checks:

```powershell
python -m compileall -q models packer singletons storages themes utils widgets windows tests scripts
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow, test
expectations, and release checklist.

## License And Credits

This fork is distributed under the MIT License. See [LICENSE](LICENSE) and
[NOTICE.md](NOTICE.md).

Original project: [voky1/sims4-translator](https://github.com/voky1/sims4-translator)

The original idea is credited to
[xTranslator](https://www.nexusmods.com/skyrimspecialedition/mods/134).

Fonts:

- [Roboto](https://fonts.google.com/specimen/Roboto), Apache License 2.0.
- [JetBrains Mono](https://www.jetbrains.com/lp/mono/), SIL Open Font License 1.1.
