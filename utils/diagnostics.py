# -*- coding: utf-8 -*-

import platform
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from PySide6 import __version__ as PYSIDE_VERSION
from PySide6.QtCore import qVersion

from singletons.config import config
from singletons.interface import interface
from singletons.state import app_state
from singletons.translation_cache import translation_cache
from singletons.translation_memory import translation_memory
from singletons.translator import ai_engine_available, deepl_available_for_current_languages
from utils.app_logging import log_file_path, redact_sensitive
from utils.constants import (
    APP_NAME,
    APP_VERSION,
    FLAG_PROGRESS,
    FLAG_REPLACED,
    FLAG_TRANSLATED,
    FLAG_UNVALIDATED,
    FLAG_VALIDATED,
)


@dataclass(frozen=True)
class ProviderHealth:
    name: str
    configured: bool
    enabled: bool
    status: str
    detail: str = ''


STATUS_LABELS = {
    FLAG_UNVALIDATED: 'Untranslated',
    FLAG_PROGRESS: 'Needs review',
    FLAG_VALIDATED: 'Approved',
    FLAG_TRANSLATED: 'Draft',
    FLAG_REPLACED: 'Edited',
}

PRIVATE_FILE_NAME_RE = re.compile(
    r'(?i)(?<![\w.-])[\w .()[\]{}-]{1,160}\.(package|stbl|xml|json|csv|binary)(?![\w.-])'
)


def provider_health_snapshot() -> tuple[ProviderHealth, ...]:
    deepl_key = _config_text('api', 'deepl_key')
    gemini_key = _config_text('api', 'gemini_key')
    gemini_model = _config_text('api', 'gemini_model')
    openai_key = _config_text('api', 'openai_key')
    openai_base_url = _config_text('api', 'openai_base_url')
    openai_model = _config_text('api', 'openai_model')
    ollama_enabled = bool(config.value('api', 'ollama_enabled'))
    ollama_base_url = _config_text('api', 'ollama_base_url')
    ollama_model = _config_text('api', 'ollama_model')
    deepl_enabled = deepl_available_for_current_languages()

    return (
        ProviderHealth(
            'DeepL',
            configured=bool(deepl_key),
            enabled=deepl_enabled,
            status='configured' if deepl_key else 'missing-key',
            detail='Glossary ID set' if _config_text('api', 'deepl_glossary_id') else '',
        ),
        ProviderHealth(
            'Gemini',
            configured=bool(gemini_key and gemini_model),
            enabled=ai_engine_available('Gemini'),
            status=_api_model_status(gemini_key, '', gemini_model),
            detail=_safe_detail(f'Model: {gemini_model}') if gemini_model else '',
        ),
        ProviderHealth(
            'OpenAI-compatible',
            configured=bool(openai_key and openai_base_url and openai_model),
            enabled=ai_engine_available('OpenAI-compatible'),
            status=_api_model_status(openai_key, openai_base_url, openai_model),
            detail=_safe_detail('; '.join(part for part in (
                f'Base URL: {openai_base_url}' if openai_base_url else '',
                f'Model: {openai_model}' if openai_model else '',
            ) if part)),
        ),
        ProviderHealth(
            'Ollama',
            configured=bool(ollama_base_url and ollama_model),
            enabled=ai_engine_available('Ollama'),
            status='enabled' if ollama_enabled and ollama_model else 'disabled',
            detail=_safe_detail('; '.join(part for part in (
                f'Base URL: {ollama_base_url}' if ollama_base_url else '',
                f'Model: {ollama_model}' if ollama_model else '',
            ) if part)),
        ),
    )


def build_diagnostics_text(log_tail_lines: int = 80) -> str:
    lines = [
        f'{APP_NAME} diagnostics',
        f'App version: {APP_VERSION}',
        f'OS: {platform.platform()}',
        f'Python: {sys.version.split()[0]}',
        f'Qt: {qVersion()}',
        f'PySide6: {PYSIDE_VERSION}',
        '',
        'Interface and translation:',
        f'- Interface language: {config.value("interface", "language") or "-"}',
        f'- Interface catalog version: {interface.version or "-"}',
        f'- Source locale: {config.value("translation", "source") or "-"}',
        f'- Destination locale: {config.value("translation", "destination") or "-"}',
        '',
        'Providers:',
    ]

    for provider in provider_health_snapshot():
        detail = f' ({provider.detail})' if provider.detail else ''
        lines.append(
            f'- {provider.name}: configured={_yes_no(provider.configured)}, '
            f'enabled={_yes_no(provider.enabled)}, status={provider.status}{detail}'
        )

    lines.extend(('', 'Translation cache:'))
    try:
        stats = translation_cache.stats()
        lines.append(f'- Enabled: {_yes_no(translation_cache.enabled)}')
        lines.append(f'- Entries: {stats.entries:,}')
        lines.append(f'- Size: {stats.size_bytes:,} bytes')
    except Exception as exc:
        lines.append(f'- Unavailable: {exc}')

    lines.extend(('', 'Translation memory:'))
    try:
        stats = translation_memory.stats()
        lines.append(f'- Enabled: {_yes_no(translation_memory.enabled)}')
        lines.append(f'- Entries: {stats.entries:,}')
        lines.append(f'- Size: {stats.size_bytes:,} bytes')
    except Exception as exc:
        lines.append(f'- Unavailable: {exc}')

    lines.extend(('', 'Workspace:'))
    lines.extend(_workspace_lines())

    lines.extend(('', 'Recent log tail:'))
    lines.extend(_log_tail(log_tail_lines))
    return redact_sensitive('\n'.join(lines))


def _api_model_status(api_key: str, base_url: str, model: str) -> str:
    if not api_key:
        return 'missing-key'
    if base_url == '':
        return 'configured' if model else 'missing-model'
    if not base_url:
        return 'missing-base-url'
    if not model:
        return 'missing-model'
    return 'configured'


def _config_text(section: str, option: str) -> str:
    return str(config.value(section, option) or '').strip()


def _safe_detail(text: str) -> str:
    return redact_sensitive(text)


def _workspace_lines() -> list[str]:
    storage = getattr(app_state, 'packages_storage', None)
    if storage is None or not getattr(storage, 'enabled', False):
        return ['- Loaded: no']

    items = list(getattr(getattr(storage, 'model', None), 'items', ()) or ())
    flags = Counter(STATUS_LABELS.get(item.flag, 'Unknown') for item in items)
    package_count = len(getattr(storage, 'packages', ()) or ())
    current_instance = getattr(app_state, 'current_instance', 0) or 0
    lines = [
        '- Loaded: yes',
        f'- Packages: {package_count:,}',
        f'- Records: {len(items):,}',
        f'- Current instance selected: {"yes" if current_instance else "no"}',
    ]
    for label in ('Approved', 'Draft', 'Needs review', 'Edited', 'Untranslated'):
        lines.append(f'- {label}: {flags.get(label, 0):,}')
    return lines


def _log_tail(line_count: int) -> list[str]:
    path = log_file_path()
    try:
        if not path.exists():
            return ['- No app log file found.']
        lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    except Exception as exc:
        return [f'- Log unavailable: {exc}']

    tail = lines[-max(1, line_count):]
    if not tail:
        return ['- Log file is empty.']
    return [_redact_diagnostics_line(line) for line in tail]


def _yes_no(value: bool) -> str:
    return 'yes' if value else 'no'


def _redact_diagnostics_line(line: str) -> str:
    text = redact_sensitive(line)
    return PRIVATE_FILE_NAME_RE.sub(lambda match: f'[REDACTED_FILE].{match.group(1).lower()}', text)
