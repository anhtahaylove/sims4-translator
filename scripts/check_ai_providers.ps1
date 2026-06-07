param(
    [switch]$DeepL,
    [switch]$Gemini,
    [switch]$OpenAICompatible,
    [switch]$Ollama,
    [switch]$All,
    [string]$EnvFile = (Join-Path $PSScriptRoot '..\.env')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Import-DotEnv {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    foreach ($Line in Get-Content -LiteralPath $Path) {
        if ($Line -notmatch '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
            continue
        }

        $Name = $Matches[1]
        $Value = $Matches[2].Trim()
        if (($Value.StartsWith('"') -and $Value.EndsWith('"')) -or
            ($Value.StartsWith("'") -and $Value.EndsWith("'"))) {
            $Value = $Value.Substring(1, $Value.Length - 2)
        }

        [Environment]::SetEnvironmentVariable($Name, $Value, 'Process')
    }
}

Import-DotEnv -Path $EnvFile

$Targets = @()
if ($All) {
    $Targets = @('DeepL', 'Gemini', 'OpenAI-compatible', 'Ollama')
} elseif (-not $DeepL -and -not $Gemini -and -not $OpenAICompatible -and -not $Ollama) {
    $Targets = @('Gemini', 'OpenAI-compatible')
} else {
    if ($DeepL) {
        $Targets += 'DeepL'
    }
    if ($Gemini) {
        $Targets += 'Gemini'
    }
    if ($OpenAICompatible) {
        $Targets += 'OpenAI-compatible'
    }
    if ($Ollama) {
        $Targets += 'Ollama'
    }
}

$env:SIMS4_AI_PROVIDER_SMOKE_TARGETS = ($Targets -join ',')

@'
import os
import sys

from singletons.config import config
from singletons.translator import ai_engine_available, deepl_usage, translator
from utils.app_logging import redact_sensitive


def env_first(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value.strip()
    return ''


deepl_key = env_first('DEEPL_API_KEY', 'DEEPL_AUTH_KEY')
if deepl_key:
    config.set_value('api', 'deepl_key', deepl_key)

gemini_key = env_first('GEMINI_API_KEY', 'GOOGLE_API_KEY')
if gemini_key:
    config.set_value('api', 'gemini_key', gemini_key)

gemini_model = env_first('GEMINI_MODEL')
if gemini_model:
    config.set_value('api', 'gemini_model', gemini_model)

openai_key = env_first('OPENAI_API_KEY')
if openai_key:
    config.set_value('api', 'openai_key', openai_key)

openai_base_url = env_first('OPENAI_BASE_URL')
if openai_base_url:
    config.set_value('api', 'openai_base_url', openai_base_url)

openai_model = env_first('OPENAI_MODEL')
if openai_model:
    config.set_value('api', 'openai_model', openai_model)

ollama_base_url = env_first('OLLAMA_BASE_URL')
if ollama_base_url:
    config.set_value('api', 'ollama_base_url', ollama_base_url)

ollama_model = env_first('OLLAMA_MODEL')
if ollama_model:
    config.set_value('api', 'ollama_model', ollama_model)

if 'Ollama' in os.environ.get('SIMS4_AI_PROVIDER_SMOKE_TARGETS', ''):
    config.set_value('api', 'ollama_enabled', True)

config.set_value('translation', 'source', config.value('translation', 'source') or 'ENG_US')
config.set_value('translation', 'destination', config.value('translation', 'destination') or 'VI_VN')

targets = [item.strip() for item in os.environ.get('SIMS4_AI_PROVIDER_SMOKE_TARGETS', '').split(',') if item.strip()]
sample = 'Hello, Simmer! Keep <b>tags</b> and {0.String}.'
failures = 0
ran = 0

print('AI provider smoke uses process env/.env first, then app user config. It does not save keys.')
for engine in targets:
    print(f'== {engine} ==')
    if not ai_engine_available(engine):
        print('SKIP: provider is not configured')
        continue

    ran += 1
    if engine == 'DeepL':
        usage = deepl_usage(timeout=20)
        if usage.status_code != 200:
            failures += 1
            print('FAIL: status=' + str(usage.status_code) + ' message=' + redact_sensitive(usage.message or ''))
            continue
        print('PASS: DeepL usage endpoint accepted the key without spending translation characters')
        print('usage=' + str(usage.character_count) + '/' + str(usage.character_limit))
        continue

    try:
        response = translator.translate(engine, sample)
    except Exception as exc:
        failures += 1
        print('FAIL: ' + redact_sensitive(str(exc)))
        continue

    if response.status_code != 200:
        failures += 1
        print('FAIL: status=' + str(response.status_code) + ' message=' + redact_sensitive(response.text or ''))
        continue

    output = response.text or ''
    missing = [token for token in ('<b>', '</b>', '{0.String}') if token not in output]
    if missing:
        failures += 1
        print('FAIL: response did not preserve token(s): ' + ', '.join(missing))
        continue

    print('PASS: real API call returned text and preserved tokens')
    print('chars=' + str(len(output)))

if ran == 0:
    print('No configured provider was available for smoke testing.')
    sys.exit(2)

sys.exit(1 if failures else 0)
'@ | python -

exit $LASTEXITCODE
