param(
    [ValidatePattern('^v?\d+\.\d+\.\d+$')]
    [string]$Version = '',
    [switch]$Latest,
    [switch]$Reanalyze,
    [int]$WaitSeconds = 120,
    [int]$PollIntervalSeconds = 15,
    [string]$ApiKeyEnvName = 'VT_API_KEY',
    [string]$OutputRoot = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..')) 'build\virustotal')
)

$ErrorActionPreference = 'Stop'

$Repo = 'anhtahaylove/sims4-translator'
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$Headers = @{
    'User-Agent' = 'sims4-translator-virustotal-check'
}

if ($Version -and $Latest) {
    throw 'Use either -Version or -Latest, not both.'
}
if (-not $Version -and -not $Latest) {
    $Latest = $true
}
if ($PollIntervalSeconds -lt 5) {
    throw '-PollIntervalSeconds must be at least 5 seconds.'
}

$ApiKey = [Environment]::GetEnvironmentVariable($ApiKeyEnvName, 'Process')
if (-not $ApiKey) {
    $ApiKey = [Environment]::GetEnvironmentVariable($ApiKeyEnvName, 'User')
}
if (-not $ApiKey) {
    $ApiKey = [Environment]::GetEnvironmentVariable($ApiKeyEnvName, 'Machine')
}
if (-not $ApiKey) {
    throw "VirusTotal API key not found. Set `$env:$ApiKeyEnvName for this PowerShell session, then run again. Do not commit or paste the key into scripts."
}

$VirusTotalHeaders = @{
    'x-apikey' = $ApiKey
    'accept' = 'application/json'
}

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host "==> $Name"
    & $Command
}

function Invoke-VirusTotal {
    param(
        [ValidateSet('GET', 'POST')]
        [string]$Method,
        [string]$Uri
    )

    try {
        return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $VirusTotalHeaders
    } catch {
        $StatusCode = $null
        if ($_.Exception.Response) {
            $StatusCode = [int]$_.Exception.Response.StatusCode
        }
        if ($StatusCode -eq 404) {
            return $null
        }
        throw
    }
}

function Get-Release {
    if ($Latest) {
        return Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -Headers $Headers
    }

    $CleanVersion = $Version.TrimStart('v')
    return Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/tags/v$CleanVersion" -Headers $Headers
}

function Get-ReleaseHashes {
    param([string]$ReleaseVersion)

    $EvidenceHashes = Join-Path $RepoRoot "build\false-positive-evidence\v$ReleaseVersion\hashes.txt"
    if (-not (Test-Path -LiteralPath $EvidenceHashes)) {
        throw "Hash evidence not found: $EvidenceHashes. Run scripts\collect_false_positive_evidence.ps1 -Version $ReleaseVersion first."
    }

    $ZipName = "The-Sims-4-Translator-Plus-v$ReleaseVersion-windows.zip"
    $ExeName = 'The Sims 4 Translator Plus.exe'
    $Hashes = @{}

    foreach ($Line in Get-Content -LiteralPath $EvidenceHashes) {
        $Match = [regex]::Match($Line, '^([A-Fa-f0-9]{64})\s+(.+)$')
        if (-not $Match.Success) {
            continue
        }
        $Hash = $Match.Groups[1].Value.Trim([char]0xFEFF).ToUpperInvariant()
        $Path = $Match.Groups[2].Value
        if ($Path -like "*$ZipName") {
            $Hashes['zip'] = $Hash
        } elseif ($Path -like "*$ExeName") {
            $Hashes['exe'] = $Hash
        }
    }

    foreach ($Required in @('zip', 'exe')) {
        if (-not $Hashes.ContainsKey($Required)) {
            throw "Missing $Required SHA256 in $EvidenceHashes."
        }
    }
    return $Hashes
}

function Convert-UnixSeconds {
    param($Value)

    if (-not $Value) {
        return ''
    }
    return [DateTimeOffset]::FromUnixTimeSeconds([int64]$Value).UtcDateTime.ToString('yyyy-MM-dd HH:mm:ss UTC')
}

function Get-DetectionRows {
    param([object]$Report)

    if (-not $Report -or -not $Report.data -or -not $Report.data.attributes.last_analysis_results) {
        return @()
    }

    $Rows = @()
    $Results = $Report.data.attributes.last_analysis_results.PSObject.Properties
    foreach ($Property in $Results) {
        $Vendor = $Property.Name
        $Result = $Property.Value
        if ($Result.category -in @('malicious', 'suspicious')) {
            $Rows += [pscustomobject]@{
                vendor = $Vendor
                category = $Result.category
                result = $Result.result
                engine_version = $Result.engine_version
                method = $Result.method
            }
        }
    }
    return $Rows
}

function Get-ReportSummary {
    param(
        [string]$Name,
        [string]$Sha256,
        [object]$Report
    )

    if (-not $Report) {
        return [pscustomobject]@{
            name = $Name
            sha256 = $Sha256
            found = $false
            last_analysis_date = ''
            stats = $null
            detections = @()
            gui_url = "https://www.virustotal.com/gui/file/$Sha256"
        }
    }

    return [pscustomobject]@{
        name = $Name
        sha256 = $Sha256
        found = $true
        last_analysis_date = Convert-UnixSeconds $Report.data.attributes.last_analysis_date
        stats = $Report.data.attributes.last_analysis_stats
        detections = @(Get-DetectionRows $Report)
        gui_url = "https://www.virustotal.com/gui/file/$Sha256"
    }
}

function Request-Reanalysis {
    param(
        [string]$Name,
        [string]$Sha256
    )

    $Response = Invoke-VirusTotal -Method POST -Uri "https://www.virustotal.com/api/v3/files/$Sha256/analyse"
    $AnalysisId = ''
    if ($Response -and $Response.data) {
        $AnalysisId = @($Response.data)[0].id
    }
    if (-not $AnalysisId) {
        Write-Warning "VirusTotal did not return an analysis id for $Name. Continuing with the latest available report."
        return [pscustomobject]@{
            name = $Name
            sha256 = $Sha256
            analysis_id = ''
            note = 'VirusTotal did not return an analysis id; report was fetched without waiting for reanalysis.'
        }
    }
    return [pscustomobject]@{
        name = $Name
        sha256 = $Sha256
        analysis_id = $AnalysisId
        note = ''
    }
}

function Wait-Analysis {
    param([object]$Analysis)

    if (-not $Analysis.analysis_id) {
        return $null
    }

    $Deadline = (Get-Date).AddSeconds($WaitSeconds)
    while ((Get-Date) -lt $Deadline) {
        $Response = Invoke-VirusTotal -Method GET -Uri "https://www.virustotal.com/api/v3/analyses/$($Analysis.analysis_id)"
        $Status = $Response.data.attributes.status
        if ($Status -eq 'completed') {
            return $Response
        }
        Write-Host "VirusTotal analysis for $($Analysis.name) is $Status; waiting $PollIntervalSeconds second(s)..."
        Start-Sleep -Seconds $PollIntervalSeconds
    }
    Write-Warning "Timed out waiting for VirusTotal analysis for $($Analysis.name). The report URL may update later."
    return $null
}

function Write-TextReport {
    param(
        [string]$Path,
        [string]$ReleaseVersion,
        [object[]]$Summaries,
        [object[]]$Analyses
    )

    $Lines = @(
        "VirusTotal report for The Sims 4 Translator Plus v$ReleaseVersion",
        "Generated: $((Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss UTC'))",
        '',
        'This report does not prove safety. It records VirusTotal vendor verdicts for release review.',
        ''
    )

    foreach ($Summary in $Summaries) {
        $Stats = $Summary.stats
        $Lines += "[$($Summary.name)]"
        $Lines += "SHA256: $($Summary.sha256)"
        $Lines += "VirusTotal: $($Summary.gui_url)"
        $Lines += "Found: $($Summary.found)"
        $Lines += "Last analysis: $($Summary.last_analysis_date)"
        if ($Stats) {
            $Lines += "Stats: malicious=$($Stats.malicious), suspicious=$($Stats.suspicious), harmless=$($Stats.harmless), undetected=$($Stats.undetected), timeout=$($Stats.timeout)"
        }
        if ($Summary.detections.Count -gt 0) {
            $Lines += 'Detections:'
            foreach ($Detection in $Summary.detections) {
                $Lines += "- $($Detection.vendor): $($Detection.category) / $($Detection.result)"
            }
        } else {
            $Lines += 'Detections: none in malicious/suspicious categories'
        }
        $Lines += ''
    }

    if ($Analyses.Count -gt 0) {
        $Lines += 'Reanalysis requests:'
        foreach ($Analysis in $Analyses) {
            if ($Analysis.analysis_id) {
                $Lines += "- $($Analysis.name): $($Analysis.analysis_id)"
            } else {
                $Lines += "- $($Analysis.name): not returned by VirusTotal"
            }
            if ($Analysis.note) {
                $Lines += "  Note: $($Analysis.note)"
            }
        }
        $Lines += ''
    }

    $Lines | Set-Content -LiteralPath $Path -Encoding utf8
}

$Release = Get-Release
$ReleaseVersion = $Release.tag_name.TrimStart('v')
$OutputDir = Join-Path $OutputRoot "v$ReleaseVersion"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$Hashes = Get-ReleaseHashes -ReleaseVersion $ReleaseVersion
$Targets = @(
    [pscustomobject]@{ name = 'Windows ZIP'; sha256 = $Hashes['zip'] },
    [pscustomobject]@{ name = 'Extracted EXE'; sha256 = $Hashes['exe'] }
)

$Analyses = New-Object System.Collections.ArrayList
if ($Reanalyze) {
    Invoke-Step 'Request VirusTotal reanalysis' {
        foreach ($Target in $Targets) {
            $Analysis = Request-Reanalysis -Name $Target.name -Sha256 $Target.sha256
            [void]$Analyses.Add($Analysis)
        }
    }

    Invoke-Step 'Wait for VirusTotal analysis completion' {
        foreach ($Analysis in $Analyses) {
            $null = Wait-Analysis -Analysis $Analysis
        }
    }
}

$Summaries = New-Object System.Collections.ArrayList
Invoke-Step 'Fetch VirusTotal file reports' {
    foreach ($Target in $Targets) {
        $Report = Invoke-VirusTotal -Method GET -Uri "https://www.virustotal.com/api/v3/files/$($Target.sha256)"
        $Summary = Get-ReportSummary -Name $Target.name -Sha256 $Target.sha256 -Report $Report
        [void]$Summaries.Add($Summary)
    }
}

$JsonPath = Join-Path $OutputDir 'virustotal-report.json'
$TextPath = Join-Path $OutputDir 'virustotal-report.txt'

[pscustomobject]@{
    release = "v$ReleaseVersion"
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss UTC')
    reanalyze_requested = [bool]$Reanalyze
    analyses = @($Analyses)
    reports = @($Summaries)
} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $JsonPath -Encoding utf8

Write-TextReport -Path $TextPath -ReleaseVersion $ReleaseVersion -Summaries @($Summaries) -Analyses @($Analyses)

Get-Content -LiteralPath $TextPath
Write-Host "VirusTotal report written to: $OutputDir"
