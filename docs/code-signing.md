# Code Signing Notes

The Windows ZIP is currently unsigned. Windows SmartScreen may warn users when
the project is new or when the executable has low reputation.

## Current Release Model

- Build the app with `scripts\build_windows.ps1`.
- Package the ZIP and checksum with `scripts\package_release.ps1`.
- Publish both the ZIP and `.sha256` file on GitHub Releases.
- Users can verify the ZIP with `Get-FileHash`.

## Future Signing Path

Code signing needs a real certificate owned by the maintainer. Do not commit
private keys, PFX files, passwords, timestamp credentials, or signing tokens.
For open-source releases, SignPath Foundation is a possible free application
path for real Windows code signing. Sigstore/cosign and GitHub Artifact
Attestations are useful provenance checks, but they do not make Windows show a
Verified Publisher or remove SmartScreen reputation warnings.

## SignPath Foundation Checklist

Use this only when the project is ready to apply for real open-source Windows
code signing:

1. Confirm the repository is public and has a clear license.
2. Confirm release builds are created by GitHub Actions from tagged source.
3. Keep ZIP, `.sha256`, and `.sigstore.json` release assets published.
4. Prepare maintainer identity/project information requested by SignPath.
5. Add signing only after a certificate/signing policy is approved.
6. Update README and release notes only after the EXE is actually Authenticode signed.

Until then, describe releases as checksum-verified and provenance-verifiable,
not as signed.

When a certificate is available, add signing as a separate release-only step:

```powershell
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a "dist\The Sims 4 Translator Plus\The Sims 4 Translator Plus.exe"
```

Then rebuild the ZIP and `.sha256` after signing. The checksum must match the
final uploaded ZIP, not a pre-signing artifact.

## Safety Rules

- Signing secrets must live in the local secure store or GitHub Actions secrets.
- Never log certificate passwords.
- Never upload signing keys to Issues, Discussions, or release assets.
- Keep unsigned builds clearly documented until signing is available.
