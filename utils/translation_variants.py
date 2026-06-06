# -*- coding: utf-8 -*-

from singletons.config import config


def translation_variant(engine: str) -> str:
    engine_name = (engine or '').lower()
    if engine_name == 'deepl':
        return (config.value('api', 'deepl_glossary_id') or '').strip()
    if engine_name == 'gemini':
        return (config.value('api', 'gemini_model') or '').strip()
    if engine_name == 'openai-compatible':
        return '|'.join((
            (config.value('api', 'openai_base_url') or '').strip().rstrip('/'),
            (config.value('api', 'openai_model') or '').strip(),
        ))
    if engine_name == 'ollama':
        return '|'.join((
            (config.value('api', 'ollama_base_url') or '').strip().rstrip('/'),
            (config.value('api', 'ollama_model') or '').strip(),
        ))
    return ''
