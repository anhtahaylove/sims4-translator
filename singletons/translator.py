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


PLACEHOLDER_PATTERN = re.compile(r'(?:\\n)+|{[A-Za-z]?\d+\.[^{}]+}|<[^>]+>')
BASE_PLACEHOLDER_PATTERN = re.compile(r'{[A-Za-z]?\d+\.[^{}]+}|<[^>]+>')
XML_PLACEHOLDER_PATTERN = re.compile(r'<x\s+id=["\'](\d+)["\']\s*/>', re.IGNORECASE)


def deepl_endpoint(api_key: str) -> str:
    return 'https://api-free.deepl.com' if api_key and ':fx' in api_key else 'https://api.deepl.com'


def deepl_usage(api_key: str = None) -> DeepLUsage:
    api_key = (api_key if api_key is not None else config.value('api', 'deepl_key') or '').strip()
    if not api_key:
        return DeepLUsage(400, 0, 0, 'DeepL API key is empty.')

    try:
        response = requests.get(
            f'{deepl_endpoint(api_key)}/v2/usage',
            headers={'Authorization': f'DeepL-Auth-Key {api_key}'},
            timeout=10
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


class Translator:

    @property
    def engines(self) -> List[str]:
        engines = ['Google', 'MyMemory']
        if deepl_available_for_current_languages():
            engines.append('DeepL')
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
                  preserve_newlines: bool = False) -> Response:
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
                use_xml_placeholders=bool(placeholders)
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
    def __deepl(text: str, context: str = '', glossary_id: str = '', use_xml_placeholders: bool = False) -> Response:
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
                    timeout=10
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
