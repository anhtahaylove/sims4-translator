param(
    [switch]$SkipTests,
    [switch]$SkipBuild,
    [switch]$KeepSpec,
    [int]$StartupSeconds = 6
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$BuildVenv = Join-Path $env:TEMP 'sims4-translator-build-venv'
$BuildPrefs = Join-Path $env:TEMP 'sims4-translator-build-prefs'
$BuildUserConfig = Join-Path $env:TEMP 'sims4-translator-build-user-config'
$BuildSmokeCwd = Join-Path $env:TEMP 'sims4-translator-build-smoke-cwd'
$AppName = 'The Sims 4 Translator Plus'
$ExePath = Join-Path $RepoRoot "dist\$AppName\$AppName.exe"
$DistDir = Split-Path $ExePath

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
    if (-not $SkipTests) {
        Invoke-Step 'Run clean-checkout fast checks' {
            & (Join-Path $PSScriptRoot 'check_fast.ps1')
        }
    }

    if ($SkipBuild) {
        Write-Host 'Build skipped.'
        exit 0
    }

    if (-not (Test-Path (Join-Path $BuildVenv 'Scripts\python.exe'))) {
        Invoke-Step 'Create temporary build venv' {
            python -m venv $BuildVenv
        }
    }

    $BuildPython = Join-Path $BuildVenv 'Scripts\python.exe'

    Invoke-Step 'Install build dependencies in temporary venv' {
        & $BuildPython -m pip install --upgrade pip
        & $BuildPython -m pip install -r requirements-dev.txt -c constraints.txt
    }

    Invoke-Step 'Prepare distributable prefs without local config' {
        if (Test-Path $BuildPrefs) {
            Remove-Item -LiteralPath $BuildPrefs -Recurse -Force
        }
        New-Item -ItemType Directory -Force -Path $BuildPrefs | Out-Null
        Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'prefs') | Where-Object {
            $_.Name -ne 'config.xml'
        } | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $BuildPrefs -Recurse -Force
        }
        if (Test-Path (Join-Path $BuildPrefs 'config.xml')) {
            throw 'Build prefs bundle must not include local prefs\config.xml.'
        }
    }

    Invoke-Step 'Build Windows app with PyInstaller' {
        & $BuildPython -m PyInstaller `
            --noconfirm `
            --clean `
            --windowed `
            --noupx `
            --contents-directory . `
            --name $AppName `
            --icon resources\logo.ico `
            --exclude-module tkinter `
            --exclude-module unittest `
            --exclude-module pytest `
            --exclude-module IPython `
            --exclude-module notebook `
            --exclude-module matplotlib `
            --add-data "$BuildPrefs;prefs" `
            --add-data 'fonts;fonts' `
            main.py
    }

    if (-not $KeepSpec) {
        $SpecPath = Join-Path $RepoRoot "$AppName.spec"
        if (Test-Path $SpecPath) {
            Remove-Item -LiteralPath $SpecPath
        }
    }

    Invoke-Step 'Verify build output layout' {
        if (-not (Test-Path $ExePath)) {
            throw "Built executable missing: $ExePath"
        }
        if (-not (Test-Path (Join-Path $DistDir 'prefs\languages.xml'))) {
            throw 'Bundled prefs\languages.xml missing beside executable.'
        }
        if (Test-Path (Join-Path $DistDir 'prefs\config.xml')) {
            throw 'Bundled prefs\config.xml must not be shipped; it is a local user preference file.'
        }
        if (-not (Test-Path (Join-Path $DistDir 'fonts\RobotoRegular.ttf'))) {
            throw 'Bundled fonts\RobotoRegular.ttf missing beside executable.'
        }
    }

    Invoke-Step 'Verify executable icon when available' {
        try {
            Add-Type -AssemblyName System.Drawing
            $Icon = [System.Drawing.Icon]::ExtractAssociatedIcon($ExePath)
            if ($null -eq $Icon) {
                throw 'Associated executable icon could not be extracted.'
            }
        } catch {
            Write-Warning "Icon extraction check skipped: $($_.Exception.Message)"
        }
    }

    Invoke-Step 'Smoke start built app' {
        if (Test-Path $BuildUserConfig) {
            Remove-Item -LiteralPath $BuildUserConfig -Recurse -Force
        }
        if (Test-Path $BuildSmokeCwd) {
            Remove-Item -LiteralPath $BuildSmokeCwd -Recurse -Force
        }
        New-Item -ItemType Directory -Force -Path $BuildUserConfig | Out-Null
        New-Item -ItemType Directory -Force -Path $BuildSmokeCwd | Out-Null

        $OldConfigDir = $env:SIMS4_TRANSLATOR_CONFIG_DIR
        $env:SIMS4_TRANSLATOR_CONFIG_DIR = $BuildUserConfig
        try {
            $Process = Start-Process -FilePath $ExePath -WorkingDirectory $BuildSmokeCwd -WindowStyle Hidden -PassThru
            Start-Sleep -Seconds $StartupSeconds
            if ($Process.HasExited) {
                throw "Built app exited early with code $($Process.ExitCode)."
            }
            Stop-Process -Id $Process.Id -Force
        } finally {
            $env:SIMS4_TRANSLATOR_CONFIG_DIR = $OldConfigDir
        }

        if (-not (Test-Path (Join-Path $BuildUserConfig 'config.xml'))) {
            throw 'Built app did not create a user config in the isolated build config directory.'
        }

        if (Test-Path (Join-Path $DistDir 'prefs\config.xml')) {
            throw 'Built app must not write prefs\config.xml beside the executable.'
        }
    }

    Invoke-Step 'Verify synthetic package-only smoke after build' {
        python scripts\verify_synthetic_smoke.py --directory build\synthetic
    }

    Write-Host "Build succeeded: $ExePath"
} finally {
    Pop-Location
}
