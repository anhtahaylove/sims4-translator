# The Sims 4 Translator Plus

[![Release](https://img.shields.io/github/v/release/anhtahaylove/sims4-translator?sort=semver)](https://github.com/anhtahaylove/sims4-translator/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Windows](https://img.shields.io/badge/Windows-10%2B-32c36c)](https://github.com/anhtahaylove/sims4-translator/releases)

**A Vietnamese-first Translation Studio for The Sims 4 package and STBL localization.**

[Tiếng Việt](README.vi.md) · [Release checklist](docs/release-checklist.md) · [Latest Windows download](https://github.com/anhtahaylove/sims4-translator/releases/latest)

> Community tool notice: this project is not affiliated with Electronic Arts, Maxis, The Sims, or the original upstream maintainer. It does not include official game artwork, logos, fonts, or assets.

## What This App Does

The Sims 4 Translator Plus helps mod translators inspect, translate, validate, and export Sims 4 strings without editing package internals by hand.

- **Vietnamese-first defaults**: first run defaults to `ENG_US -> VI_VN`.
- **Table-first workspace**: built for packages with thousands or hundreds of thousands of strings.
- **Hybrid search**: search by string ID, original text, or translation in one field.
- **Selection Preview**: read long selected strings without opening a separate editor.
- **Translation Studio editor**: edit one string with token highlight, token safety checks, and optional token insertion helpers.
- **DeepL support**: API key diagnostics, usage check, glossary ID, context, and batch cost guard.
- **Validate Release**: scan release output for blank text, token mismatches, duplicates, and risky statuses before writing files.
- **Windows build script**: repeatable PyInstaller packaging for local release builds.

## Download And Run

1. Open the [latest release](https://github.com/anhtahaylove/sims4-translator/releases/latest).
2. Download `The-Sims-4-Translator-Plus-v2.0.0-windows.zip`.
3. Extract the ZIP to a normal folder such as `D:\Tools\The Sims 4 Translator Plus`.
4. Run `The Sims 4 Translator Plus.exe`.

Do not run the app directly from inside the ZIP archive. Extract it first so bundled `prefs` and `fonts` are available beside the executable.

## Recommended Vietnamese Workflow

For full-game or DLC localization, use this safer path:

1. Open **Options**.
2. Confirm **Source** is `ENG_US`.
3. Confirm **Destination** is `VI_VN`.
4. Load one or more `.package` or `.stbl` files.
5. Translate and review strings in the table and Translation Studio editor.
6. Run **Validate Release** before writing release files.
7. Prefer **Save as package** for a Mods-folder release.
8. Test the generated package in:

```text
Documents\Electronic Arts\The Sims 4\Mods
```

Use **Finalize** only when you deliberately want to rewrite a package with destination STBL resources. Keep **Create backup before Finalize** enabled if you use that workflow.

## Supported Formats

| Direction | Formats |
| --- | --- |
| Open / import | `.package`, `.stbl`, XML, JSON, Binary, CSV-style translation data |
| Export | STBL package, XML, XML for Deaderpool's STBL editor, JSON, Binary, Hub CSV |
| Release QA | Text or CSV validation reports |
| Dictionaries | Built from installed Sims 4 pack string resources |

## DeepL Setup

DeepL is optional. Google and MyMemory remain available, but DeepL can produce better results for large batches when configured carefully.

1. Open **Options**.
2. Paste your **DeepL API key**.
3. Click **Test key**. This uses DeepL usage/quota and does not spend translation characters.
4. Click **Check usage** before large batch jobs.
5. Optionally paste a **Glossary ID** if you already created a glossary in DeepL for terms such as `Trait`, `Lot`, `Moodlet`, or pack-specific terminology.

Before a DeepL batch translate job starts, the app estimates the number of source characters that will be sent so you can avoid spending quota accidentally.

## Token Safety

Sims 4 strings often contain placeholders and formatting such as:

```text
{0.SimFirstName}
{1.Money}
\n
<b>...</b>
<i>...</i>
```

The editor highlights these tokens and warns when the translation is missing required tokens, adds extra tokens, changes token order, or changes line-break count. **Approve** and **Needs Review** both show a soft warning when tokens differ; you can continue deliberately if the difference is intentional.

## Validate Release

Use **Validate Release** before publishing a package.

- **Soft release**: good during daily work. Untranslated, Draft, and Needs Review strings are warnings.
- **Strict release**: better before public publishing. Untranslated, Draft, and Needs Review strings are treated as critical.

The report is a safety gate, not a forced blocker. You can go back to fix issues or continue deliberately after reviewing the report.

See [docs/release-checklist.md](docs/release-checklist.md) for the full Vietnamese release checklist.

## Build From Source

Requirements:

- Windows 10 or newer
- Python 3.11 or newer
- Git

Setup:

```powershell
git clone https://github.com/anhtahaylove/sims4-translator.git
cd sims4-translator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

Run verification:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q models packer singletons storages themes utils widgets windows tests scripts main.py
python scripts\create_synthetic_package.py
python scripts\verify_synthetic_smoke.py --directory build\synthetic --require-gui-outputs
git diff --check
```

## Build The Windows App

Use the reviewed build script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

The script uses PyInstaller as a build-only dependency inside a temporary virtual environment. PyInstaller is not a runtime dependency and is not required for normal source usage.

## Troubleshooting

| Problem | What to try |
| --- | --- |
| Destination is not `VI_VN` | Open **Options** and set Destination to `VI_VN`. Public release ZIPs do not ship a local `prefs/config.xml`, so fresh installs default to `ENG_US -> VI_VN`. |
| DeepL key works in the browser but not in the app | Check whether the key is Free or Pro, then use **Test key** in Options. Free keys usually end with `:fx`. |
| Translated text appears blank in game | Run **Validate Release**, check missing tokens, empty translations, duplicate output, and wrong destination locale. |
| The app cannot see Sims packs | In **Options**, set the game install folder that contains `Data`, `EP`, `GP`, `SP`, and `FP` folders. |
| Windows blocks the executable | The release is unsigned. Extract the ZIP, keep the folder together, and use Windows security prompts only if you trust the downloaded file source. |

## Credits

This fork is based on the original [voky1/sims4-translator](https://github.com/voky1/sims4-translator) project and remains licensed under the MIT License.

Special thanks to the Sims modding and localization community for workflow feedback, test packages, and practical translation edge cases.

## License

MIT. See [LICENSE](LICENSE).
