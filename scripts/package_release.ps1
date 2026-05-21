param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$AppName = 'The Sims 4 Translator Plus'
$DistDir = Join-Path $RepoRoot "dist\$AppName"
$ExePath = Join-Path $DistDir "$AppName.exe"
$ZipName = "The-Sims-4-Translator-Plus-v$Version-windows.zip"
$ZipPath = Join-Path $RepoRoot $ZipName
$ChecksumPath = "$ZipPath.sha256"

function Assert-Path {
    param(
        [string]$Path,
        [string]$Message
    )
    if (-not (Test-Path $Path)) {
        throw $Message
    }
}

Push-Location $RepoRoot
try {
    Assert-Path $ExePath "Built executable missing: $ExePath"
    Assert-Path (Join-Path $DistDir 'prefs\languages.xml') 'Bundled prefs\languages.xml missing.'
    Assert-Path (Join-Path $DistDir 'fonts\RobotoRegular.ttf') 'Bundled fonts\RobotoRegular.ttf missing.'

    if (Test-Path (Join-Path $DistDir 'prefs\config.xml')) {
        throw 'Release bundle must not include prefs\config.xml.'
    }

    if ((Test-Path $ZipPath) -and -not $Force) {
        throw "Release ZIP already exists: $ZipPath. Pass -Force to overwrite."
    }

    if (Test-Path $ZipPath) {
        Remove-Item -LiteralPath $ZipPath -Force
    }
    if (Test-Path $ChecksumPath) {
        Remove-Item -LiteralPath $ChecksumPath -Force
    }

    Compress-Archive -Path (Join-Path $DistDir '*') -DestinationPath $ZipPath -Force
    $Hash = Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256
    "$($Hash.Hash)  $ZipName" | Set-Content -LiteralPath $ChecksumPath -Encoding ascii

    Assert-Path $ZipPath "Release ZIP missing after packaging: $ZipPath"
    Assert-Path $ChecksumPath "Checksum missing after packaging: $ChecksumPath"

    Write-Host "Packaged release: $ZipPath"
    Write-Host "SHA256: $($Hash.Hash)"
} finally {
    Pop-Location
}
