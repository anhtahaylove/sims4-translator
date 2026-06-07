param(
    [string]$Version = '2.3.4',
    [switch]$SkipBuild,
    [switch]$SkipPackage
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host "==> $Name"
    & $Command
}

Push-Location $RepoRoot
try {
    Invoke-Step 'Run fast repository checks' {
        & (Join-Path $PSScriptRoot 'check_fast.ps1')
    }

    Invoke-Step 'Verify GUI smoke outputs for release' {
        python scripts\verify_synthetic_smoke.py --directory build\synthetic --require-gui-outputs
    }

    Invoke-Step 'Verify interface localization health' {
        python scripts\verify_interface_i18n.py --all --version $Version --strict-empty --strict-missing
    }

    Invoke-Step 'Verify release notes exist' {
        python scripts\collect_release_notes.py --version $Version --check
    }

    Invoke-Step 'Run visual i18n layout smoke' {
        python scripts\visual_i18n_smoke.py --languages english german russian ukrainian brasil chinese vietnamese --version $Version --strict-layout --no-screenshots
    }

    if (-not $SkipBuild) {
        Invoke-Step 'Build Windows executable' {
            & (Join-Path $PSScriptRoot 'build_windows.ps1') -SkipTests
        }
    }

    if (-not $SkipPackage) {
        Invoke-Step 'Package Windows release ZIP and checksum' {
            & (Join-Path $PSScriptRoot 'package_release.ps1') -Version $Version -Force
        }
    }
} finally {
    Pop-Location
}
