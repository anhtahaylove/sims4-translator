param(
    [ValidatePattern('^v?\d+\.\d+\.\d+$')]
    [string]$Version = '',
    [switch]$Latest,
    [int]$StartupSeconds = 6,
    [string]$WorkDirectory = (Join-Path $env:TEMP 'sims4-translator-release-verify')
)

$ErrorActionPreference = 'Stop'

$Repo = 'anhtahaylove/sims4-translator'
$AppName = 'The Sims 4 Translator Plus'
$Headers = @{
    'User-Agent' = 'sims4-translator-release-verifier'
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

function Get-AssetUrl {
    param(
        [object]$Release,
        [string]$Name
    )

    $Asset = $Release.assets | Where-Object { $_.name -eq $Name } | Select-Object -First 1
    if (-not $Asset) {
        throw "Release asset not found: $Name"
    }
    return $Asset.browser_download_url
}

$Release = Get-Release
$ReleaseVersion = $Release.tag_name.TrimStart('v')
$ZipName = "The-Sims-4-Translator-Plus-v$ReleaseVersion-windows.zip"
$ChecksumName = "$ZipName.sha256"
$RunDir = Join-Path $WorkDirectory "v$ReleaseVersion"
$ExtractDir = Join-Path $RunDir 'app'
$DownloadZip = Join-Path $RunDir $ZipName
$DownloadChecksum = Join-Path $RunDir $ChecksumName

if (Test-Path $RunDir) {
    Remove-Item -LiteralPath $RunDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

Invoke-Step "Download $ZipName and checksum" {
    Invoke-WebRequest -Uri (Get-AssetUrl $Release $ZipName) -OutFile $DownloadZip -Headers $Headers
    Invoke-WebRequest -Uri (Get-AssetUrl $Release $ChecksumName) -OutFile $DownloadChecksum -Headers $Headers
}

Invoke-Step 'Verify SHA256 checksum' {
    $ExpectedText = Get-Content -LiteralPath $DownloadChecksum -Raw
    $ExpectedHash = [regex]::Match($ExpectedText, '[A-Fa-f0-9]{64}').Value.ToUpperInvariant()
    if (-not $ExpectedHash) {
        throw "Checksum file does not contain a SHA256 hash: $DownloadChecksum"
    }

    $ActualHash = (Get-FileHash -LiteralPath $DownloadZip -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($ActualHash -ne $ExpectedHash) {
        throw "Checksum mismatch. Expected $ExpectedHash, got $ActualHash"
    }
    Write-Host "SHA256 OK: $ActualHash"
}

Invoke-Step 'Extract release ZIP' {
    Expand-Archive -LiteralPath $DownloadZip -DestinationPath $ExtractDir -Force
}

Invoke-Step 'Verify release layout' {
    $ExePath = Join-Path $ExtractDir "$AppName.exe"
    $LanguagesPath = Join-Path $ExtractDir 'prefs\languages.xml'
    $FontPath = Join-Path $ExtractDir 'fonts\RobotoRegular.ttf'
    $BundledConfig = Join-Path $ExtractDir 'prefs\config.xml'

    foreach ($Path in @($ExePath, $LanguagesPath, $FontPath)) {
        if (-not (Test-Path -LiteralPath $Path)) {
            throw "Missing expected file: $Path"
        }
    }
    if (Test-Path -LiteralPath $BundledConfig) {
        throw 'Release ZIP must not include prefs\config.xml.'
    }
}

Invoke-Step 'Smoke start app' {
    $ExePath = Join-Path $ExtractDir "$AppName.exe"
    $UserConfig = Join-Path $RunDir 'user-config'
    New-Item -ItemType Directory -Force -Path $UserConfig | Out-Null

    $OldConfigDir = $env:SIMS4_TRANSLATOR_CONFIG_DIR
    $env:SIMS4_TRANSLATOR_CONFIG_DIR = $UserConfig
    try {
        $Process = Start-Process -FilePath $ExePath -WorkingDirectory $ExtractDir -WindowStyle Hidden -PassThru
        Start-Sleep -Seconds $StartupSeconds
        if ($Process.HasExited) {
            throw "Release app exited early with code $($Process.ExitCode)."
        }
        Stop-Process -Id $Process.Id -Force
    } finally {
        $env:SIMS4_TRANSLATOR_CONFIG_DIR = $OldConfigDir
    }

    $ConfigPath = Join-Path $UserConfig 'config.xml'
    if (-not (Test-Path -LiteralPath $ConfigPath)) {
        throw "App did not create a user config file: $ConfigPath"
    }
}

Write-Host "Release verification passed: $($Release.tag_name)"
Write-Host "Verified files are in: $RunDir"
