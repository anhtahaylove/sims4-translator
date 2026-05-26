param(
    [switch]$SkipLint
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
    Invoke-Step 'Run unit tests' {
        python -m unittest discover -s tests -v
    }

    Invoke-Step 'Compile Python sources' {
        python -m compileall -q models packer singletons storages themes utils widgets windows tests scripts main.py
    }

    if (-not $SkipLint) {
        Invoke-Step 'Run focused Ruff checks when available' {
            $RuffVersion = & python -m ruff --version 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host $RuffVersion
                python -m ruff check . --select E9,F63,F7,F82
            } else {
                Write-Warning 'Ruff is not installed; install requirements-dev.txt to enable focused lint checks.'
            }
        }
    }

    Invoke-Step 'Create synthetic package' {
        python scripts\create_synthetic_package.py
    }

    Invoke-Step 'Verify synthetic package-only smoke' {
        python scripts\verify_synthetic_smoke.py --directory build\synthetic
    }

    Invoke-Step 'Verify version references' {
        python scripts\verify_version_sync.py --version 2.2.14
    }

    Invoke-Step 'Verify interface coverage' {
        python scripts\verify_interface_i18n.py --all --version 2.2.14 --strict-empty --strict-missing
    }

    Invoke-Step 'Check Markdown links and images' {
        @'
from pathlib import Path
import re

files = [
    Path("README.md"),
    Path("README.vi.md"),
    Path("docs/README.md"),
    Path("docs/release-checklist.md"),
    Path("CONTRIBUTING.md"),
    Path("NOTICE.md"),
    Path("SECURITY.md"),
]
missing = []
for md in files:
    if not md.exists():
        continue
    text = md.read_text(encoding="utf-8")
    for target in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', text):
        if target.startswith(("http://", "https://")):
            continue
        clean = target.split("#")[0]
        if clean and not (md.parent / clean).exists():
            missing.append(f"{md}: {target}")
    for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', text):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        clean = target.split("#")[0]
        if clean and not (md.parent / clean).exists():
            missing.append(f"{md}: {target}")
if missing:
    raise SystemExit("\n".join(missing))
print("Markdown links and images OK")
'@ | python -
    }

    Invoke-Step 'Check whitespace in diff' {
        git diff --check
    }
} finally {
    Pop-Location
}
