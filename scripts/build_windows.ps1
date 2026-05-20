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
        Invoke-Step 'Run unit tests' {
            python -m unittest discover -s tests -v
        }
        Invoke-Step 'Compile Python sources' {
            python -m compileall -q models packer singletons storages themes utils widgets windows tests scripts main.py
        }
        Invoke-Step 'Create synthetic package' {
            python scripts\create_synthetic_package.py
        }
        Invoke-Step 'Verify synthetic smoke outputs' {
            python scripts\verify_synthetic_smoke.py --directory build\synthetic --require-gui-outputs
        }
        Invoke-Step 'Check whitespace in diff' {
            git diff --check
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
        & $BuildPython -m pip install -r requirements.txt pyinstaller
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
            --contents-directory . `
            --name $AppName `
            --icon resources\logo.ico `
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
        $Process = Start-Process -FilePath $ExePath -WorkingDirectory $DistDir -WindowStyle Hidden -PassThru
        Start-Sleep -Seconds $StartupSeconds
        if ($Process.HasExited) {
            throw "Built app exited early with code $($Process.ExitCode)."
        }
        Stop-Process -Id $Process.Id -Force
        $GeneratedConfig = Join-Path $DistDir 'prefs\config.xml'
        if (Test-Path $GeneratedConfig) {
            Remove-Item -LiteralPath $GeneratedConfig -Force
        }
    }

    Invoke-Step 'Verify synthetic smoke after build' {
        python scripts\verify_synthetic_smoke.py --directory build\synthetic --require-gui-outputs
    }

    Write-Host "Build succeeded: $ExePath"
} finally {
    Pop-Location
}
