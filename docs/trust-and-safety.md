# Trust & Safety

This page helps users and community moderators verify that a download really
comes from this open-source project.

## What This App Does

- Opens local Sims 4 `.package` / STBL translation data.
- Lets users edit, validate, and export translation packages.
- Supports optional online translation providers such as DeepL, Google, and MyMemory.
- Stores user preferences locally under the user data directory.

## What This App Does Not Do

- It does not include official EA, Maxis, or The Sims artwork, fonts, game files, characters, or screenshots.
- It does not collect telemetry.
- It does not upload your package files automatically.
- It does not require a DeepL key unless you choose to use DeepL.
- It is not affiliated with, endorsed by, sponsored by, or connected to Electronic Arts, Maxis, or The Sims.

## How To Verify A Download

Use only the official GitHub repository and Releases page:

- Repository: `https://github.com/anhtahaylove/sims4-translator`
- Releases: `https://github.com/anhtahaylove/sims4-translator/releases/latest`

Each Windows release should include:

- `The-Sims-4-Translator-Plus-vX.Y.Z-windows.zip`
- `The-Sims-4-Translator-Plus-vX.Y.Z-windows.zip.sha256`

After downloading both files, run:

```powershell
Get-FileHash .\The-Sims-4-Translator-Plus-vX.Y.Z-windows.zip -Algorithm SHA256
```

The displayed hash must match the `.sha256` file attached to the same GitHub
Release. If it does not match, do not run the ZIP.

Source users can also run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_release_download.ps1 -Latest
```

That script downloads the release ZIP and checksum from GitHub, verifies the
hash, extracts to a temporary folder, checks the expected release layout, and
starts the app briefly to confirm it does not exit immediately.

## How Admins Can Check A Link Before Approving

1. Confirm the link domain is `github.com`.
2. Confirm the repository owner/name is `anhtahaylove/sims4-translator`.
3. Open the release and check that both ZIP and `.sha256` assets exist.
4. Check the repository Actions tab or CI badge. The latest `main` CI should be passing.
5. Check that release notes do not ask users to disable antivirus, run unknown scripts, or download from mirrors.

## Windows SmartScreen

The Windows executable is currently unsigned. SmartScreen can warn about new or
unsigned apps even when the source is public and the checksum is correct. This
project documents that status instead of pretending the app is signed.

Code signing is planned only when a real maintainer-owned certificate is
available. See [code-signing.md](code-signing.md).

## Privacy Notes

- DeepL keys are stored in local user config, not in the release ZIP.
- Release builds must not include `prefs/config.xml`.
- App logs are written to `%APPDATA%\The Sims 4 Translator Plus\logs\app.log`.
- Logs redact API keys before writing, but users should still review logs before posting them publicly.

## Ghi Chú Cho Cộng Đồng Việt Nam

Trang này giúp admin và người dùng tự kiểm chứng link tải thay vì chỉ tin vào
lời giới thiệu.

- Chỉ duyệt link từ `github.com/anhtahaylove/sims4-translator`.
- Mỗi bản Windows nên có cả file ZIP và file `.sha256`.
- Người dùng có thể kiểm checksum bằng PowerShell.
- Source code public nên cộng đồng có thể xem app làm gì.
- App chưa code-sign, nên SmartScreen có thể cảnh báo. Đây là hạn chế minh bạch hiện tại, không phải bằng chứng rằng file có mã độc.

Nếu một bài đăng dùng link rút gọn, mirror lạ, file ZIP không có checksum, hoặc
yêu cầu tắt antivirus, không nên duyệt.
