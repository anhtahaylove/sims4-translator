# False Positive Submission Guide

This guide prepares evidence for antivirus or security vendors when a public
release is flagged by a small number of static or machine-learning engines.

It does not claim that any file is automatically safe. It gives reviewers the
information they need to verify the release source, build provenance, checksum,
and packaging model.

## When To Use This

Use this guide when a release ZIP or extracted EXE is flagged by a small number
of vendors while most other engines report no detection. Recent review targets
have included Yandex, SentinelOne, Cylance, Microsoft, SecureAge/APEX, and other
static ML engines depending on the VirusTotal result for that release.

Do not submit a vendor review when the vendor already reports `Undetected`. For
example, an `Undetected` Acronis result does not need a false-positive request.

## Important Context

- The Windows app is packaged with PyInstaller in one-directory mode.
- The EXE is not Authenticode code-signed yet, so static ML engines and
  reputation systems can be stricter than they are for signed software.
- GitHub release artifacts include a ZIP, `.sha256` checksum, and
  `.zip.sigstore.json` cosign provenance bundle.
- Immutable releases also show a GitHub-generated `Release attestation (json)`.
  That file binds the release tag, commit, and asset list; it is separate from
  the uploaded cosign bundle.
- GitHub Artifact Attestations and Sigstore/cosign verify provenance, but they
  do not replace Windows code signing.
- VirusTotal aggregates vendor results. If a detection is wrong, the vendor
  that produced the detection is the party that can reclassify it.

Useful links:

- VirusTotal false-positive guidance: <https://docs.virustotal.com/docs/false-positive>
- Microsoft file submission portal: <https://www.microsoft.com/en-us/wdsi/filesubmission>
- Microsoft submission guidance: <https://learn.microsoft.com/en-us/unified-secops-platform/submission-guide>
- SecureAge false-positive form: <https://www.secureage.com/support/report-false-positive>
- VirusTotal contributors list: <https://docs.virustotal.com/docs/contributors>
- BlackBerry support resources for Cylance: <https://www.blackberry.com/us/en/support/overview>
- Palo Alto false-positive triage guidance: <https://knowledgebase.paloaltonetworks.com/articles/en_US/Knowledge/Triage-and-Resolution-of-False-Positives-in-Palo-Alto-Networks-Antivirus-Profiles>
- SignPath Foundation: <https://signpath.org/>

Some vendors do not expose a public unauthenticated false-positive form. If no
public form is available, use the vendor's official support path or the contact
information shown on VirusTotal's contributor pages.

## Generate An Evidence Pack

From a clean source checkout:

The examples below use `2.3.4`; replace it with the release version you are
checking.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\collect_false_positive_evidence.ps1 -Version 2.3.4
```

To include VirusTotal report links in the generated vendor template manually:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\collect_false_positive_evidence.ps1 -Version 2.3.4 -VirusTotalZipUrl "https://www.virustotal.com/gui/file/..." -VirusTotalExeUrl "https://www.virustotal.com/gui/file/..."
```

The script writes files under:

```text
build\false-positive-evidence\v2.3.4\
```

That folder is a local artifact and should not be committed.

Expected files:

| File | Purpose |
| --- | --- |
| `release.json` | GitHub release metadata for the selected version. |
| `release-assets.txt` | Human-readable release URL and asset list. |
| `verify-release-download.txt` | Output from checksum, attestation, cosign, layout, and startup-smoke checks. |
| `hashes.txt` | SHA256 hashes for the ZIP, checksum, provenance bundle, and extracted EXE when available. |
| `vendor-submission-template.txt` | Paste-ready text for vendor false-positive forms. |
| `README.txt` | Short explanation of the generated pack. |

The script does not upload files, does not call the VirusTotal API, and does
not store API keys.

## Optional VirusTotal API Check

If you have a VirusTotal API key, you can query the current ZIP and EXE reports
without uploading files:

```powershell
$env:VT_API_KEY = "<your VirusTotal API key>"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_virustotal_release.ps1 -Version 2.3.4
```

The script also accepts a local ignored `.env` file containing either:

```text
VT_API_KEY=your_key_here
```

or just the raw key on a single line. This is only for local convenience; never
commit or paste the key into tracked files.

To query VirusTotal and automatically write the ZIP/EXE report URLs back into
the generated vendor template:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_virustotal_release.ps1 -Version 2.3.4 -UpdateEvidencePack
```

To request a fresh reanalysis for files that VirusTotal already knows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_virustotal_release.ps1 -Version 2.3.4 -Reanalyze
```

The script writes local reports under:

```text
build\virustotal\v2.3.4\
```

It reads the API key from `VT_API_KEY` or the ignored local `.env`, does not
print the key, does not upload files, and does not commit the report output.
Reanalysis is useful for checking whether vendors have updated signatures after
a false-positive submission, but it does not guarantee reclassification.

## Vendor Submission Template

Use the generated `vendor-submission-template.txt` first. If you need a manual
template, use this:

```text
Subject: False positive review request for The Sims 4 Translator Plus

Hello,

This appears to be a false positive for an open-source Windows desktop app.

Project:
https://github.com/anhtahaylove/sims4-translator

Release:
https://github.com/anhtahaylove/sims4-translator/releases/tag/vX.Y.Z

File:
The-Sims-4-Translator-Plus-vX.Y.Z-windows.zip

SHA256:
[paste SHA256 from .sha256 or hashes.txt]

VirusTotal:
ZIP: [paste ZIP VirusTotal URL]
EXE: [paste EXE VirusTotal URL]

Build and provenance:
- The app is built from public source code using GitHub Actions.
- The release includes SHA256 checksum, GitHub Artifact Attestation, and a
  Sigstore/cosign keyless provenance bundle.
- The app is packaged with PyInstaller in one-directory mode.
- The executable is not Authenticode code-signed yet, which can trigger static
  ML or heuristic detections.

Verification commands:
gh attestation verify .\The-Sims-4-Translator-Plus-vX.Y.Z-windows.zip --repo anhtahaylove/sims4-translator
cosign verify-blob --bundle .\The-Sims-4-Translator-Plus-vX.Y.Z-windows.zip.sigstore.json --certificate-identity "https://github.com/anhtahaylove/sims4-translator/.github/workflows/release-build.yml@refs/tags/vX.Y.Z" --certificate-oidc-issuer "https://token.actions.githubusercontent.com" .\The-Sims-4-Translator-Plus-vX.Y.Z-windows.zip

Please review and reclassify if appropriate.
```

## Per-Vendor Notes

| Vendor | Recommended action |
| --- | --- |
| Yandex | Use Yandex Browser/support or the VirusTotal contributor contact path if available. Include the ZIP and EXE VirusTotal URLs plus SHA256 hashes. |
| SentinelOne | Use the official customer/support path or VirusTotal contributor contact information, then include the evidence template. |
| Cylance | Use BlackBerry/Cylance support or VirusTotal contributor contact information, then include the evidence template. If the portal asks for product context, describe the app as an unsigned PyInstaller desktop utility with public GitHub Actions provenance. |
| Microsoft Defender | Use the Microsoft Security Intelligence file submission portal. Choose the false-positive or incorrectly detected file path, include the EXE SHA256, VirusTotal URL, release URL, and provenance verification commands. Microsoft also supports file/hash submissions through Defender/XDR submission workflows for eligible accounts. |
| APEX | APEX is commonly associated with SecureAge on VirusTotal; use the SecureAge false-positive form and include the evidence template. SecureAge asks for a ZIP archive protected with password `infected`; include the generated evidence text in the description. |
| Acronis | No action needed when the result is `Undetected`. |

## Current v2.3.0 Review Targets

The v2.3.0 VirusTotal check showed the Windows ZIP with no malicious or
suspicious categories, while the extracted EXE still had three heuristic/static
detections: Cylance, Microsoft Defender, and APEX. Use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\collect_false_positive_evidence.ps1 -Version 2.3.0
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_virustotal_release.ps1 -Version 2.3.0 -UpdateEvidencePack
```

Then submit the EXE hash/report through the vendor-specific paths above. The
evidence pack for that release is generated at:

```text
build\false-positive-evidence\v2.3.0\
```

## What Not To Say

Avoid language that overclaims safety:

- Do not say "VirusTotal proves the app is clean."
- Do not say "cosign means Windows should trust the EXE."
- Do not ask users to disable antivirus.
- Do not claim the EXE is signed until Authenticode signing is actually in use.

Preferred wording:

```text
This release is open source and provenance-verifiable. A small number of static
or ML engines may flag unsigned PyInstaller apps. Users can verify the checksum,
GitHub Artifact Attestation, and Sigstore/cosign bundle before running it.
```
