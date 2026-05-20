# The Sims 4 Translator Plus

**The Sims 4 Translator Plus** is a community-maintained Windows desktop app for
translating The Sims 4 mod and package strings. It is based on
[voky1/sims4-translator](https://github.com/voky1/sims4-translator) and keeps the
same package/export workflow while adding a rebranded Life Studio Green interface,
Vietnamese localization support, release validation, safer background jobs, and
repeatable Windows builds.

[README tiếng Việt](README.vi.md)

> This project is not affiliated with Electronic Arts, Maxis, The Sims, or the
> upstream maintainer. The Sims 4 is a trademark of its respective owner. This
> fork uses original community assets and does not ship official EA, Maxis, or
> The Sims artwork, logos, fonts, or UI assets.

## Highlights

- Table-first translation workspace designed for large packages.
- Community Vietnamese destination locale: `VI_VN`.
- Default localization workflow: `ENG_US -> VI_VN`.
- Hybrid search across ID, original text, and translated text.
- Selection Preview for reading long strings without opening the editor.
- Focus Studio editor with token highlighting and soft-confirm token warnings.
- Batch translate with DeepL cost guard and API usage diagnostics.
- Pre-release Validation Report with Soft and Strict release profiles.
- Save as package, Finalize, and export flows preserve existing file formats.
- Life Studio Green visual system with a single rebranded resource set.
- Windows build script using PyInstaller as a build-only dependency.

## Supported Inputs And Outputs

The app can open and work with:

- `.package`
- `.stbl`
- `.xml`
- `.json`
- `.binary`

The app can export or save translations as:

- STBL
- XML
- XML-DP for Deaderpool's STBL editor
- JSON
- Binary
- Translation Hub CSV
- A translated `.package`

## Download And Run

For normal users, download the Windows ZIP from the
[Releases](https://github.com/anhtahaylove/sims4-translator/releases) page,
extract it, and run:

```text
The Sims 4 Translator Plus.exe
```

The app stores local preferences in `prefs/config.xml` beside the app when run
from source or from the extracted build. That local config is intentionally not
tracked by git.

## Vietnamese Workflow

Recommended settings for Vietnamese localization:

- Source: `ENG_US`
- Destination: `VI_VN`
- Interface Language: `Vietnamese` or `English`
- Create backup before Finalize: enabled
- Use conflict-free save mode: disabled unless you are testing a copied package

Recommended release path:

1. Open or add one or more `.package` files.
2. Search, filter, edit, translate, and approve strings.
3. Run `Validate Release...`.
4. Use `Save as package` for a Mods-folder release.
5. Test the generated package in `Documents\Electronic Arts\The Sims 4\Mods`.
6. Use `Finalize` only when you deliberately want to rewrite a package copy.

`VI_VN` is a community/fan locale for Vietnamese localization workflows. It is
not presented as an official EA locale.

## DeepL Setup

DeepL is optional. To use it:

1. Open `Options`.
2. Paste your DeepL API key.
3. Use `Test key` to verify the key without spending translation characters.
4. Use `Check usage` before large batch jobs.
5. Choose DeepL in the editor or Batch Translate dialog.

The optional DeepL glossary ID is only needed if you already created a glossary
in DeepL and want terms such as `Trait`, `Lot`, or `Moodlet` translated
consistently. Batch Translate estimates source characters before sending a DeepL
job so you can avoid spending quota accidentally.

## Pre-release Validation

Use `Validate Release...` before publishing a translation package.

- **Soft release**: good during normal work. Untranslated, Draft, and Needs
  review records are warnings.
- **Strict release**: good before public release. Untranslated, Draft, and Needs
  review records are critical.

The report checks for blank-text risks, missing Sims tokens, line-break/tag
issues, duplicate output conflicts, and destination locale conversion problems.
It is a safety gate, not a destructive fixer: you can go back to fix issues or
continue deliberately.

## Run From Source

Requirements:

- Windows
- Python 3.12+

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the app:

```powershell
python main.py
```

## Development Verification

Run the normal source checks:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q models packer singletons storages themes utils widgets windows tests scripts main.py
python scripts\create_synthetic_package.py
python scripts\verify_synthetic_smoke.py --directory build\synthetic --require-gui-outputs
git diff --check
```

## Windows Build

The build script creates a temporary build venv under `%TEMP%`, installs
PyInstaller there, runs verification, and builds the Windows app:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

PyInstaller is a build-only dependency. It is not required at runtime and is not
listed in `requirements.txt`.

Build outputs are local release artifacts and should not be committed:

- `build/`
- `dist/`
- generated `.spec`
- generated `.package`
- local dictionaries
- `prefs/config.xml`

## Release Checklist

See [docs/release-checklist.md](docs/release-checklist.md) for the Vietnamese
release workflow, large-package QA checklist, DeepL notes, and release hygiene.

## License And Credits

This fork is distributed under the MIT License. See [LICENSE](LICENSE) and
[NOTICE.md](NOTICE.md).

Original project:
[voky1/sims4-translator](https://github.com/voky1/sims4-translator)

The original idea is credited to
[xTranslator](https://www.nexusmods.com/skyrimspecialedition/mods/134).

Bundled fonts:

- [Roboto](https://fonts.google.com/specimen/Roboto), Apache License 2.0.
- [JetBrains Mono](https://www.jetbrains.com/lp/mono/), SIL Open Font License 1.1.
