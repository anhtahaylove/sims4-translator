# Changelog

## Version 2.1.0 - 2026-05-25

- Added Gemini and OpenAI-compatible translation providers with token-preserving prompts and mocked tests.
- Expanded Options into a provider settings panel for DeepL, Gemini, OpenAI-compatible endpoints, and AI character confirmation thresholds.
- Extended translation cache variants and redaction coverage for AI provider keys.

## Version 2.0.6 - 2026-05-25

- Added a persistent translation cache so interrupted or repeated batch translation can reuse exact successful results.
- Added heuristic length/layout warnings to Validate Release for translations that may overflow game UI.
- Added research notes comparing adjacent GitHub translation tools and the ideas worth borrowing.

## Version 2.0.5 - 2026-05-25

- Added a user-friendly crash dialog with copyable, redacted diagnostics.
- Added traceback details to background task errors for better bug reports.
- Added conservative PyInstaller excludes and optional pre-commit contributor checks.

## Version 2.0.4 - 2026-05-25

- Fixed startup resource lookup so bundled fonts load correctly outside the repository working directory.
- Limited the Windows Qt style override to Windows hosts.
- Modernized XML pretty-printing while preserving the existing binary writer contract.

## Version 2.0.3 - 2026-05-22

- Added a clearer first-run onboarding flow in the empty workspace.
- Polished Vietnamese interface wording and added a guard against mojibake regressions.
- Added a short Vietnamese quick-start flow and README demo visual for public sharing.

## Version 2.0.2 - 2026-05-22

- Added GitHub Artifact Attestations for Windows release artifacts.
- Added Sigstore/cosign keyless signature bundles for Windows ZIP releases.
- Added advanced release verification guidance for checksum, provenance, and cosign verification.
- Updated the release workflow so tagged releases are built and published by GitHub Actions.

## Version 2.0.1 - 2026-05-22

- Added a Trust & Safety guide for users and community moderators.
- Added release download verification guidance and a PowerShell verification script.
- Added a GitHub Actions release-artifact workflow for clean-runner Windows ZIP builds.
- Added redacted local app logging under the user data directory.
- Completed Vietnamese interface catalog coverage for the current UI.

## Version 2.0.0 - 2026-05-21

- Rebuilt the public app as a Vietnamese-first Translation Studio for package and STBL localization.
- Added community Vietnamese destination locale `VI_VN` and first-run `ENG_US -> VI_VN` defaults.
- Added a partial Vietnamese interface language with English fallback for untranslated strings.
- Added token highlighting, token safety warnings, and a Token Assistant in the editor.
- Added Pre-release Validation Report with Soft and Strict release profiles.
- Added Workspace Warnings for day-to-day issue scanning.
- Added DeepL key diagnostics, usage checks, batch cost guard, context, glossary ID support, and safer placeholder handling.
- Added a Windows build script for repeatable PyInstaller builds.
- Improved the table-first workspace, Selection Preview, Options, Pack Manager, and release QA documentation.

## Version 1.4 - 2025-08-05

- Resolved issues with Google Translate (It's not perfect, so check the results)
- Added support for MyMemory translator as an alternative to Google Translate
- Added support for translating multiple text selections simultaneously
- Added support for JSON and binary files used by Sims 4 Studio
- Added Danish language
- Added French language
- Added Indonesian language
- Added Ukrainian language

Many changes are taken from other forks, for which special thanks to their authors (TURBODRIVER, EliD-Dev, etc).

## Version 1.3.1 - 2024-08-02

- Added German language
- Fixed working with merged packages
- Variables in curly brackets are no longer translated using translators (such as {0.String}, {0.Number}, etc)

## Version 1.3 - 2024-07-09

- Added light and dark themes
- Added Polish language

## Version 1.2 - 2024-06-18

- Added a visual indicator of translation progress
- Fixed several bugs

## Version 1.2 RC - 2024-06-15

- Added the possibility of automatic translation
- Added DeepL support
- The translation files of this application are placed in separate files
- The Sims 4 language settings are placed in a separate file

## Version 1.1.2 - 2020-12-07

- Fixed translation using Google Translate
- Fixed a bug related to incorrect line selection when editing (Windows 7)
  
## Version 1.1 - 2020-11-18

- The list of extensions is made in a separate file, so that I don't have to upload a new version every time, and you download it (for those who use the dictionaries of the base game and extensions)
- Fixed crash with a large number of dictionaries
  
## Version 1.0.1 - 2020-09-24

- Fixed bug with access to settings
  
## Version 1.0 - 2020-09-24

- Added Chinese language
- Аdded 64-bit version (32-bit version will no longer be supported)
- A lot of fixes that are a bit lazy to list
  
## Version 1.0 RC - 2020-08-24

- Added support for STBL files
- Added support for exporting XML files for the Deaderpool's STBL editor
- Added the ability to insert new record
- Added the ability to set the high-bit for groups
- Added the ability to translate from dictionaries created for other mods
- Improved export
- Fixed an error when starting the program if there are non-Latin characters in the path
  
## Version 0.4 - 2020-07-10

- Added Google Translate
- Trying to get rid of virus warnings in Avast antivirus
  
## Version 0.3 - 2020-07-04

- Added support for import XML files created with Deaderpool's STBL editor
- Attempt to fix some problems in the interface
  
## Version 0.2 - 2020-07-02

- Added support for simplified Chinese (CHS_CN)
