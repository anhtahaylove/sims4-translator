# -*- coding: utf-8 -*-

import re
import requests
import html.parser
from collections import Counter, namedtuple
from typing import List

from singletons.config import config
from singletons.interface import interface
from singletons.languages import languages


Response = namedtuple('Response', 'status_code text')
DeepLUsage = namedtuple('DeepLUsage', 'status_code character_count character_limit message')
PlaceholderRestoreResult = namedtuple('PlaceholderRestoreResult', 'text warning')
OllamaModels = namedtuple('OllamaModels', 'status_code models message')


PLACEHOLDER_PATTERN = re.compile(r'(?:\\n)+|{[A-Za-z]?\d+\.[^{}]+}|<[^>]+>')
BASE_PLACEHOLDER_PATTERN = re.compile(r'{[A-Za-z]?\d+\.[^{}]+}|<[^>]+>')
XML_PLACEHOLDER_PATTERN = re.compile(r'<x\s+id=["\'](\d+)["\']\s*/>', re.IGNORECASE)
OLLAMA_RECOMMENDED_MODEL = 'translategemma:12b'
OLLAMA_DEFAULT_BASE_URL = 'http://localhost:11434'


def deepl_endpoint(api_key: str) -> str:
    return 'https://api-free.deepl.com' if api_key and ':fx' in api_key else 'https://api.deepl.com'


def deepl_usage(api_key: str = None, timeout: int | float = 10) -> DeepLUsage:
    api_key = (api_key if api_key is not None else config.value('api', 'deepl_key') or '').strip()
    if not api_key:
        return DeepLUsage(400, 0, 0, 'DeepL API key is empty.')

    try:
        response = requests.get(
            f'{deepl_endpoint(api_key)}/v2/usage',
            headers={'Authorization': f'DeepL-Auth-Key {api_key}'},
            timeout=timeout
        )
    except Exception as e:
        return DeepLUsage(500, 0, 0, str(e))

    if response.status_code == 200:
        payload = response.json()
        return DeepLUsage(
            200,
            int(payload.get('character_count') or 0),
            int(payload.get('character_limit') or 0),
            ''
        )
    if response.status_code == 403:
        return DeepLUsage(403, 0, 0, 'Invalid API key.')
    if response.status_code == 456:
        return DeepLUsage(456, 0, 0, 'Your quota has exceeded!')

    return DeepLUsage(response.status_code, 0, 0,
                      interface.text('Errors', 'Translation failed with error code: {}').format(response.status_code))


def deepl_available_for_current_languages() -> bool:
    src = languages.source
    dst = languages.destination
    return bool(config.value('api', 'deepl_key') and src and src.deepl and dst and dst.deepl)


def estimate_deepl_characters(items) -> int:
    total = 0
    for item in items:
        record = item[1] if isinstance(item, tuple) else item
        total += len(record.source or '')
    return total


def estimate_ai_characters(items) -> int:
    return estimate_deepl_characters(items)


def ai_engine_available(engine: str) -> bool:
    engine_name = engine.lower()
    if engine_name == 'gemini':
        return bool(config.value('api', 'gemini_key') and config.value('api', 'gemini_model'))
    if engine_name == 'openai-compatible':
        return bool(
            config.value('api', 'openai_key') and
            config.value('api', 'openai_base_url') and
            config.value('api', 'openai_model')
        )
    if engine_name == 'ollama':
        return bool(config.value('api', 'ollama_enabled') and config.value('api', 'ollama_model'))
    return False


def ai_character_cap(option: str) -> int:
    try:
        return max(0, int(config.value('api', option) or 0))
    except (TypeError, ValueError):
        return 0


def ollama_base_url(value: str = None) -> str:
    base_url = value if value is not None else config.value('api', 'ollama_base_url') or OLLAMA_DEFAULT_BASE_URL
    return base_url.strip().rstrip('/')


def ollama_models(base_url: str = None, timeout: int | float = 5) -> OllamaModels:
    url = ollama_base_url(base_url)
    if not url:
        return OllamaModels(400, (), interface.text('Errors', 'Ollama base URL is empty.'))

    try:
        response = requests.get(f'{url}/api/tags', timeout=timeout)
    except Exception:
        return OllamaModels(503, (), interface.text(
            'Errors',
            'Ollama is not reachable at {url}. Start Ollama or check the base URL.'
        ).format(url=url))

    if response.status_code != 200:
        detail = ''
        try:
            detail = response.json().get('error') or ''
        except Exception:
            detail = getattr(response, 'text', '') or ''
        message = interface.text('Errors', 'Translation failed with error code: {}').format(response.status_code)
        if detail:
            message = f'{message} {detail}'
        return OllamaModels(response.status_code, (), message)

    try:
        payload = response.json()
        names = []
        for model in payload.get('models', []):
            name = model.get('model') or model.get('name')
            if name and name not in names:
                names.append(name)
        return OllamaModels(200, tuple(names), '')
    except Exception as exc:
        return OllamaModels(500, (), str(exc))


class Translator:

    @property
    def engines(self) -> List[str]:
        engines = ['Google', 'MyMemory']
        if deepl_available_for_current_languages():
            engines.append('DeepL')
        if ai_engine_available('Gemini'):
            engines.append('Gemini')
        if ai_engine_available('OpenAI-compatible'):
            engines.append('OpenAI-compatible')
        if ai_engine_available('Ollama'):
            engines.append('Ollama')
        return engines

    @property
    def available(self) -> bool:
        return len(self.engines) > 0

    @staticmethod
    def extract_placeholders(text, xml_safe: bool = False):
        extracted_items = []

        def save_and_replace_pattern(match):
            extracted_items.append(match.group(0))
            index = len(extracted_items) - 1
            if xml_safe:
                return f'<x id="{index}"/>'
            return f"({index})"

        pattern = PLACEHOLDER_PATTERN if xml_safe else BASE_PLACEHOLDER_PATTERN
        modified_text = pattern.sub(save_and_replace_pattern, text)
        return modified_text, extracted_items

    @staticmethod
    def insert_placeholders(text, placeholders):
        return Translator.restore_placeholders(text, placeholders).text

    @staticmethod
    def restore_placeholders(text, placeholders, xml_safe: bool = False) -> PlaceholderRestoreResult:
        if xml_safe:
            restored_indexes = []

            def restore_xml_placeholder(match):
                index = int(match.group(1))
                if index < 0 or index >= len(placeholders):
                    return match.group(0)
                restored_indexes.append(index)
                return placeholders[index]

            text = XML_PLACEHOLDER_PATTERN.sub(restore_xml_placeholder, text)

            expected = Counter(range(len(placeholders)))
            restored = Counter(restored_indexes)
            missing = expected - restored
            extra = restored - expected
            warnings = []
            if missing:
                warnings.append('Missing placeholders: ' + ', '.join(f'<x id="{i}"/>' for i in missing.elements()))
            if extra:
                warnings.append('Duplicated placeholders: ' + ', '.join(f'<x id="{i}"/>' for i in extra.elements()))

            return PlaceholderRestoreResult(text, '; '.join(warnings))

        for i, placeholder in enumerate(placeholders):
            text = text.replace(f"({i})", placeholder)

        text = re.sub(r'(<[^/][^>]+>)\s+', r'\1', text)
        text = re.sub(r'\s+(</[^>]+>)', r'\1', text)

        return PlaceholderRestoreResult(text, '')

    def translate(self, engine: str, text: str, context: str = '', glossary_id: str = None,
                  preserve_newlines: bool = False, request_timeout: int | float = None) -> Response:
        engine_name = engine.lower()
        xml_placeholders = engine_name == 'deepl'
        modified_text, placeholders = self.extract_placeholders(text, xml_safe=xml_placeholders)

        # placeholder_spaces = []
        # for ph in re.finditer(r'\(\d+\)', modified_text):
        #     before = modified_text[:ph.start()].rstrip()
        #     after = modified_text[ph.end():].lstrip()
        #     has_space_before = len(before) != ph.start()
        #     has_space_after = len(after) != len(modified_text) - ph.end()
        #     placeholder_spaces.append((has_space_before, has_space_after))

        if not xml_placeholders:
            modified_text = modified_text.replace('\\n', "\n")

        if engine_name == 'mymemory':
            response = Translator.__mymemory(modified_text)
        elif engine_name == 'deepl':
            response = Translator.__deepl(
                modified_text,
                context=context,
                glossary_id=glossary_id,
                use_xml_placeholders=bool(placeholders),
                request_timeout=request_timeout,
            )
        elif engine_name == 'gemini':
            response = Translator.__gemini(
                modified_text,
                context=context,
                expected_lines=modified_text.count('\n') + 1,
                request_timeout=request_timeout,
            )
        elif engine_name == 'openai-compatible':
            response = Translator.__openai_compatible(
                modified_text,
                context=context,
                expected_lines=modified_text.count('\n') + 1,
                request_timeout=request_timeout,
            )
        elif engine_name == 'ollama':
            response = Translator.__ollama(
                modified_text,
                context=context,
                expected_lines=modified_text.count('\n') + 1,
                request_timeout=request_timeout,
            )
        else:
            response = Translator.__google(modified_text)

        if response.status_code != 200:
            return response

        translated_text = response.text

        # parts = re.split(r'(\(\d+\))', translated_text)
        # for i in range(1, len(parts), 2):
        #     ph_num = int(parts[i][1:-1])
        #     if ph_num < len(placeholder_spaces):
        #         has_space_before, has_space_after = placeholder_spaces[ph_num]
        #         if not has_space_before and parts[i - 1].endswith(' '):
        #             parts[i - 1] = parts[i - 1].rstrip()
        #         if not has_space_after and parts[i + 1].startswith(' '):
        #             parts[i + 1] = parts[i + 1].lstrip()

        # translated_text = ''.join(parts)
        if not preserve_newlines:
            translated_text = translated_text.replace("\n", '\\n')

        restore_result = self.restore_placeholders(translated_text, placeholders, xml_safe=xml_placeholders)
        if restore_result.warning:
            return Response(409, restore_result.warning)

        return Response(response.status_code, restore_result.text)

    @staticmethod
    def __google(text: str) -> Response:
        language = languages.destination

        if language and language.google:
            payload = {
                'sl': 'auto',
                'tl': language.google,
                'q': text
            }

            url = 'http://translate.google.com/m?sl=auto'
            ua = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/122.0.0.0 Safari/537.36')

            try:
                req = requests.get(url, params=payload, headers={'User-Agent': ua}, timeout=10)
                if req.status_code == 200:
                    content = req.content.decode('utf-8')
                    expr = r'(?s)class="(?:t0|result-container)">(.*?)<'
                    return Response(200, html.unescape(re.findall(expr, content)[0]))
                else:
                    return Response(req.status_code,
                                    interface.text('Errors', 'Translation failed with error code: {}').format(
                                        req.status_code))
            except Exception as e:
                return Response(500, str(e))

        return Response(404, interface.text('Errors', 'Language code not found!'))

    @staticmethod
    def __mymemory(text: str) -> Response:
        if len(text) > 500:
            return Response(404, interface.text('Errors', 'A maximum of 500 characters is allowed.'))

        src = languages.source
        dst = languages.destination

        if src and src.google and dst and dst.google:
            payload = {
                'langpair': '{}|{}'.format(src.google, dst.google),
                'q': text
            }

            url = 'https://api.mymemory.translated.net/get'
            ua = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/122.0.0.0 Safari/537.36')

            try:
                req = requests.get(url, params=payload, headers={'User-Agent': ua}, timeout=10)
                if req.status_code == 200:
                    content = req.json()
                    return Response(200, content['responseData']['translatedText'])
                else:
                    return Response(req.status_code,
                                    interface.text('Errors', 'Translation failed with error code: {}').format(
                                        req.status_code))
            except Exception as e:
                return Response(500, str(e))

        return Response(404, interface.text('Errors', 'Language code not found!'))

    @staticmethod
    def __gemini(text: str, context: str = '', expected_lines: int = 1,
                 request_timeout: int | float = None) -> Response:
        api_key = (config.value('api', 'gemini_key') or '').strip()
        model = (config.value('api', 'gemini_model') or '').strip()
        if not api_key or not model:
            return Response(400, 'Gemini API key or model is empty.')

        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
        payload = {
            'contents': [{
                'parts': [{
                    'text': Translator.__ai_prompt(text, context, expected_lines)
                }]
            }],
            'generationConfig': {
                'temperature': 0.2
            }
        }

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={'x-goog-api-key': api_key},
                timeout=request_timeout or 30,
            )
        except Exception as e:
            return Response(500, str(e))

        if resp.status_code == 200:
            try:
                parts = resp.json()['candidates'][0]['content']['parts']
                return Response(200, ''.join(part.get('text', '') for part in parts).strip())
            except Exception as e:
                return Response(500, str(e))

        return Translator.__provider_error_response(resp.status_code, resp, 'Gemini')

    @staticmethod
    def __openai_compatible(text: str, context: str = '', expected_lines: int = 1,
                            request_timeout: int | float = None) -> Response:
        api_key = (config.value('api', 'openai_key') or '').strip()
        base_url = (config.value('api', 'openai_base_url') or '').strip().rstrip('/')
        model = (config.value('api', 'openai_model') or '').strip()
        if not api_key or not base_url or not model:
            return Response(400, 'OpenAI-compatible API key, base URL, or model is empty.')

        try:
            resp = requests.post(
                f'{base_url}/v1/chat/completions',
                json={
                    'model': model,
                    'temperature': 0.2,
                    'messages': [
                        {
                            'role': 'system',
                            'content': (
                                'You translate The Sims 4 localization strings. Preserve placeholders, '
                                'formatting tags, escaped line markers, and line count exactly.'
                            ),
                        },
                        {'role': 'user', 'content': Translator.__ai_prompt(text, context, expected_lines)},
                    ],
                },
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=request_timeout or 30,
            )
        except Exception as e:
            return Response(500, str(e))

        if resp.status_code == 200:
            try:
                return Response(200, resp.json()['choices'][0]['message']['content'].strip())
            except Exception as e:
                return Response(500, str(e))

        return Translator.__provider_error_response(resp.status_code, resp, 'OpenAI-compatible')

    @staticmethod
    def __ollama(text: str, context: str = '', expected_lines: int = 1,
                 request_timeout: int | float = None) -> Response:
        base_url = ollama_base_url()
        model = (config.value('api', 'ollama_model') or '').strip()
        if not base_url or not model:
            return Response(400, interface.text('Errors', 'Ollama base URL or model is empty.'))

        try:
            resp = requests.post(
                f'{base_url}/api/chat',
                json={
                    'model': model,
                    'stream': False,
                    'messages': [{
                        'role': 'user',
                        'content': Translator.__ollama_prompt(text, context, expected_lines),
                    }],
                    'options': {
                        'temperature': 0.2,
                    },
                },
                timeout=request_timeout or 120,
            )
        except Exception:
            return Response(503, interface.text(
                'Errors',
                'Ollama is not reachable at {url}. Start Ollama or check the base URL.'
            ).format(url=base_url))

        if resp.status_code == 200:
            try:
                return Response(200, resp.json()['message']['content'].strip())
            except Exception as e:
                return Response(500, str(e))

        return Translator.__provider_error_response(resp.status_code, resp, 'Ollama')

    @staticmethod
    def __ai_prompt(text: str, context: str, expected_lines: int) -> str:
        src = languages.source
        dst = languages.destination
        parts = [
            f'Source locale: {src.locale if src else config.value("translation", "source")}',
            f'Target locale: {dst.locale if dst else config.value("translation", "destination")}',
            f'Return exactly {expected_lines} line(s).',
            'Do not add explanations, markdown, numbering, quotes, or extra blank lines.',
            'Preserve placeholders like (0), {0.SimFirstName}, <b>, </b>, \\n, \\x0a, and \\x0d exactly.',
        ]
        if context:
            parts.append('Context:\n' + context)
        parts.append('Text to translate:\n' + text)
        return '\n\n'.join(parts)

    @staticmethod
    def __ollama_prompt(text: str, context: str, expected_lines: int) -> str:
        src = Translator.__translation_language_label(config.value('translation', 'source'), source=True)
        dst = Translator.__translation_language_label(config.value('translation', 'destination'), source=False)
        rules = [
            f'You are a professional {src} to {dst} game localization translator.',
            'Your goal is to accurately convey the meaning and nuances of the original text while keeping Vietnamese natural, playful, casual, and game-like.',
            'Produce only the Vietnamese translation, without any explanations, markdown, numbering, quotes, or extra blank lines.',
            f'Return exactly {expected_lines} line(s).',
            'Preserve placeholders exactly: (0), {0.String}, {0.SimFirstName}, %s, %d, <tags>, </tags>, \\n, \\x0a, and \\x0d.',
            'Do not translate item IDs, file keys, XML tags, variable names, or formatting codes.',
            'Use consistent terms: Sim = Sim, Moodlet = moodlet, Aspiration = Khát vọng, Trait = Đặc điểm, Household = Hộ gia đình.',
        ]
        if context:
            rules.append('Context:\n' + context)
        rules.append('Please translate the following text into Vietnamese:\n\n' + text)
        return '\n\n'.join(rules)

    @staticmethod
    def __translation_language_label(locale: str, source: bool) -> str:
        labels = {
            'ENG_US': 'English (en)',
            'VI_VN': 'Vietnamese (vi-VN)',
        }
        if locale in labels:
            return labels[locale]

        language = languages.by_locale(locale)
        if language and language.google:
            return f'{locale} ({language.google})'
        return locale or ('source language' if source else 'target language')

    @staticmethod
    def __provider_error_response(status_code: int, response, provider: str) -> Response:
        detail = ''
        try:
            payload = response.json()
            if isinstance(payload, dict):
                error = payload.get('error') or payload
                if isinstance(error, dict):
                    detail = error.get('message') or error.get('status') or ''
        except Exception:
            detail = getattr(response, 'text', '') or ''

        if status_code in (401, 403):
            message = f'{provider} API key was rejected.'
        elif provider == 'Ollama' and status_code == 404:
            message = interface.text(
                'Errors',
                'Ollama model was not found. Run: ollama pull {model}'
            ).format(model=OLLAMA_RECOMMENDED_MODEL)
        elif status_code == 429:
            message = f'{provider} rate limit was reached.'
        elif status_code >= 500:
            message = f'{provider} service had a temporary problem.'
        else:
            message = interface.text('Errors', 'Translation failed with error code: {}').format(status_code)

        if detail:
            message = f'{message} {detail}'
        return Response(status_code, message)

    @staticmethod
    def __deepl(text: str, context: str = '', glossary_id: str = '', use_xml_placeholders: bool = False,
                request_timeout: int | float = None) -> Response:
        api_key = config.value('api', 'deepl_key')

        src = languages.source
        dst = languages.destination

        if src and src.deepl and dst and dst.deepl:
            payload = {
                'text': text,
                'source_lang': src.deepl,
                'target_lang': dst.deepl,
                'split_sentences': 'nonewlines',
                'preserve_formatting': '1'
            }

            if context:
                payload['context'] = context

            glossary_id = glossary_id if glossary_id is not None else config.value('api', 'deepl_glossary_id')
            glossary_id = (glossary_id or '').strip()
            if glossary_id:
                payload['glossary_id'] = glossary_id

            if use_xml_placeholders:
                payload['tag_handling'] = 'xml'

            api_url = f'{deepl_endpoint(api_key)}/v2/translate'

            try:
                resp = requests.post(
                    api_url,
                    data=payload,
                    headers={'Authorization': f'DeepL-Auth-Key {api_key}'},
                    timeout=request_timeout or 10
                )

                if resp.status_code == 200:
                    txt = resp.json()['translations'][0]['text']
                    return Response(200, txt)
                elif resp.status_code == 403:
                    return Response(403, interface.text('Errors', 'Invalid API key.'))
                elif resp.status_code == 456:
                    return Response(456, interface.text('Errors', 'Your quota has exceeded!'))
                elif resp.status_code == 500:
                    return Response(500,
                                    interface.text('Errors', 'There was a temporary problem with the DeepL Service.'))
                else:
                    return Response(resp.status_code,
                                    interface.text('Errors', 'Translation failed with error code: {}').format(
                                        resp.status_code))
            except Exception as e:
                return Response(500, str(e))

        return Response(404, interface.text('Errors', 'Language code not found!'))


translator = Translator()
