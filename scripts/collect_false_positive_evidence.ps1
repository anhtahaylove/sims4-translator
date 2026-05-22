param(
    [ValidatePattern('^v?\d+\.\d+\.\d+$')]
    [string]$Version = '',
    [switch]$Latest,
    [string]$OutputRoot = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..')) 'build\false-positive-evidence'),
    [string]$VirusTotalZipUrl = '',
    [string]$VirusTotalExeUrl = ''
)

$ErrorActionPreference = 'Stop'

$Repo = 'anhtahaylove/sims4-translator'
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$Headers = @{
    'User-Agent' = 'sims4-translator-false-positive-evidence'
}

if ($Version -and $Latest) {
    throw 'Use either -Version or -Latest, not both.'
}
if (-not $Version -and -not $Latest) {
    $Latest = $true
}

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host "==> $Name"
    & $Command
}

function Get-Release {
    if ($Latest) {
        return Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -Headers $Headers
    }

    $CleanVersion = $Version.TrimStart('v')
    return Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/tags/v$CleanVersion" -Headers $Headers
}

function Write-Utf8 {
    param(
        [string]$Path,
        [string]$Content
    )

    $Content | Set-Content -LiteralPath $Path -Encoding utf8
}

function Invoke-ExternalCapture {
    param(
        [string]$Path,
        [string]$FilePath,
        [string[]]$ArgumentList
    )

    $StdOut = "$Path.stdout.tmp"
    $StdErr = "$Path.stderr.tmp"
    Remove-Item -LiteralPath $StdOut, $StdErr -Force -ErrorAction SilentlyContinue

    $Process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -NoNewWindow `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $StdOut `
        -RedirectStandardError $StdErr

    $Output = @()
    if (Test-Path -LiteralPath $StdOut) {
        $Output += Get-Content -LiteralPath $StdOut
    }
    if (Test-Path -LiteralPath $StdErr) {
        $Output += Get-Content -LiteralPath $StdErr
    }
    Write-Utf8 $Path ($Output -join "`n")

    Remove-Item -LiteralPath $StdOut, $StdErr -Force -ErrorAction SilentlyContinue

    if ($Process.ExitCode -ne 0) {
        throw "$FilePath failed with exit code $($Process.ExitCode). See $Path."
    }
}

$Release = Get-Release
$ReleaseVersion = $Release.tag_name.TrimStart('v')
$OutputDir = Join-Path $OutputRoot "v$ReleaseVersion"
$VerifyWorkDir = Join-Path $OutputDir 'download'

if (Test-Path $OutputDir) {
    Remove-Item -LiteralPath $OutputDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Invoke-Step 'Write release metadata' {
    $Release | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $OutputDir 'release.json') -Encoding utf8

    $AssetLines = @(
        "Repository: https://github.com/$Repo",
        "Release: $($Release.html_url)",
        "Tag: $($Release.tag_name)",
        '',
        'Assets:'
    )
    foreach ($Asset in $Release.assets) {
        $AssetLines += "- $($Asset.name)"
        $AssetLines += "  URL: $($Asset.browser_download_url)"
        $AssetLines += "  Size: $($Asset.size)"
        if ($Asset.digest) {
            $AssetLines += "  Digest: $($Asset.digest)"
        }
    }
    Write-Utf8 (Join-Path $OutputDir 'release-assets.txt') ($AssetLines -join "`n")
}

Invoke-Step 'Run provenance release verifier' {
    $VerifyScript = Join-Path $PSScriptRoot 'verify_release_download.ps1'
    Invoke-ExternalCapture `
        -Path (Join-Path $OutputDir 'verify-release-download.txt') `
        -FilePath 'powershell' `
        -ArgumentList @(
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            $VerifyScript,
            '-Version',
            $ReleaseVersion,
            '-VerifyProvenance',
            '-WorkDirectory',
            $VerifyWorkDir
        )
}

Invoke-Step 'Write file hashes' {
    $RunDir = Join-Path $VerifyWorkDir "v$ReleaseVersion"
    $AppDir = Join-Path $RunDir 'app'
    $Candidates = @(
        (Join-Path $RunDir "The-Sims-4-Translator-Plus-v$ReleaseVersion-windows.zip"),
        (Join-Path $RunDir "The-Sims-4-Translator-Plus-v$ReleaseVersion-windows.zip.sha256"),
        (Join-Path $RunDir "The-Sims-4-Translator-Plus-v$ReleaseVersion-windows.zip.sigstore.json"),
        (Join-Path $AppDir 'The Sims 4 Translator Plus.exe')
    )

    $HashLines = @()
    foreach ($Path in $Candidates) {
        if (Test-Path -LiteralPath $Path) {
            $Hash = Get-FileHash -LiteralPath $Path -Algorithm SHA256
            $RelativePath = Resolve-Path -LiteralPath $Path -Relative
            $HashLines += "$($Hash.Hash)  $RelativePath"
        }
    }
    Write-Utf8 (Join-Path $OutputDir 'hashes.txt') ($HashLines -join "`n")
}

Invoke-Step 'Write vendor submission template' {
    $ZipName = "The-Sims-4-Translator-Plus-v$ReleaseVersion-windows.zip"
    $ZipHashLine = Get-Content -LiteralPath (Join-Path $OutputDir 'hashes.txt') | Where-Object { $_ -like "*$ZipName" } | Select-Object -First 1
    if (-not $ZipHashLine) {
        throw "Could not find SHA256 entry for $ZipName."
    }
    $ZipHash = ($ZipHashLine -split '\s+')[0]
    $ZipVirusTotal = if ($VirusTotalZipUrl) { $VirusTotalZipUrl } else { '[paste ZIP VirusTotal URL here]' }
    $ExeVirusTotal = if ($VirusTotalExeUrl) { $VirusTotalExeUrl } else { '[paste EXE VirusTotal URL here]' }

    $Template = @"
Subject: False positive review request for The Sims 4 Translator Plus

Hello,

This appears to be a false positive for an open-source Windows desktop app.

Project:
https://github.com/$Repo

Release:
$($Release.html_url)

File:
$ZipName

SHA256:
$ZipHash

VirusTotal:
ZIP: $ZipVirusTotal
EXE: $ExeVirusTotal

Build and provenance:
- The app is built from public source code using GitHub Actions.
- The release includes SHA256 checksum, GitHub Artifact Attestation, and Sigstore/cosign keyless provenance bundle.
- The app is packaged with PyInstaller in one-directory mode and is not Authenticode code-signed yet, which can trigger static ML/heuristic false positives.

Verification commands:
gh attestation verify .\$ZipName --repo $Repo
cosign verify-blob --bundle .\$ZipName.sigstore.json --certificate-identity "https://github.com/$Repo/.github/workflows/release-build.yml@refs/tags/v$ReleaseVersion" --certificate-oidc-issuer "https://token.actions.githubusercontent.com" .\$ZipName

Please review and reclassify if appropriate.
"@
    Write-Utf8 (Join-Path $OutputDir 'vendor-submission-template.txt') $Template.Trim()
}

Invoke-Step 'Write README' {
    $Readme = @"
False positive evidence pack for The Sims 4 Translator Plus v$ReleaseVersion

This folder is generated under build/ and should not be committed.

Files:
- release.json: GitHub release metadata.
- release-assets.txt: human-readable release and asset list.
- verify-release-download.txt: checksum, GitHub attestation, cosign, layout, and startup-smoke verifier output.
- hashes.txt: SHA256 hashes for downloaded release files and extracted EXE when available.
- vendor-submission-template.txt: text to paste into vendor false-positive forms.

This pack does not upload files, does not call the VirusTotal API, and should not contain API keys.
"@
    Write-Utf8 (Join-Path $OutputDir 'README.txt') $Readme.Trim()
}

Write-Host "False positive evidence pack written to: $OutputDir"
