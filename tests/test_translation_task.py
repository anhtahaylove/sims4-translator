# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch

from singletons.config import config
from singletons.translator import (
    DeepLUsage,
    Response,
    ai_engine_available,
    deepl_endpoint,
    deepl_usage,
    estimate_ai_characters,
    estimate_deepl_characters,
    translator,
)
from utils.task_runner import CancellationToken, TaskReporter
from windows.edit_dialog import EditTranslationRequest, edit_translation_task
from windows.translate_dialog import (
    TranslateDialog,
    TranslationChunkRequest,
    TranslationChunkResult,
    TranslationItemSnapshot,
    TranslationItemResult,
    translate_chunk_task,
)
from packer.resource import ResourceID
from storages.records import MainRecord
from utils.constants import FLAG_UNVALIDATED


class NoopReporter(TaskReporter):

    def __init__(self):
        pass

    def progress(self, current: int = 0, total: int = 0, message: str = '') -> None:
        pass


class TranslationTaskTests(unittest.TestCase):

    def setUp(self):
        config.set_value('translation', 'source', 'ENG_US')
        config.set_value('translation', 'destination', 'VI_VN')
        config.set_value('api', 'deepl_key', 'sample:fx')
        config.set_value('api', 'deepl_glossary_id', '')
        config.set_value('api', 'gemini_key', '')
        config.set_value('api', 'gemini_model', 'gemini-2.5-flash')
        config.set_value('api', 'openai_key', '')
        config.set_value('api', 'openai_base_url', 'https://api.openai.com')
        config.set_value('api', 'openai_model', 'gpt-4o-mini')

    def test_task_returns_immutable_translation_result_without_records(self):
        request = TranslationChunkRequest(
            engine='Mock',
            items=(TranslationItemSnapshot(index=0, source='Hello'),)
        )

        with patch('windows.translate_dialog.translator.translate', return_value=Response(200, 'Bonjour')):
            result = translate_chunk_task(CancellationToken(), NoopReporter(), request)

        self.assertEqual(result.error, '')
        self.assertEqual(result.translations[0].index, 0)
        self.assertEqual(result.translations[0].text, 'Bonjour')

    def test_fast_task_preserves_line_break_placeholders(self):
        request = TranslationChunkRequest(
            engine='Mock',
            items=(
                TranslationItemSnapshot(index=0, source='Hello\\nA'),
                TranslationItemSnapshot(index=1, source='World'),
            ),
            fast=True
        )

        with patch('windows.translate_dialog.translator.translate', return_value=Response(200, 'Bonjour\\x0aA\nMonde')):
            result = translate_chunk_task(CancellationToken(), NoopReporter(), request)

        self.assertEqual(result.translations[0].text, 'Bonjour\\nA')
        self.assertEqual(result.translations[1].text, 'Monde')

    def test_deepl_endpoint_selects_free_or_pro_host(self):
        self.assertEqual(deepl_endpoint('abc:fx'), 'https://api-free.deepl.com')
        self.assertEqual(deepl_endpoint('abc'), 'https://api.deepl.com')

    def test_deepl_usage_uses_usage_endpoint_and_maps_quota(self):
        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {'character_count': 1234, 'character_limit': 500000}

        with patch('singletons.translator.requests.get', return_value=FakeResponse()) as get:
            usage = deepl_usage('abc:fx')

        self.assertEqual(usage, DeepLUsage(200, 1234, 500000, ''))
        api_url, kwargs = get.call_args.args[0], get.call_args.kwargs
        self.assertEqual(api_url, 'https://api-free.deepl.com/v2/usage')
        self.assertIn('DeepL-Auth-Key abc:fx', kwargs['headers']['Authorization'])

    def test_deepl_translate_sends_context_glossary_and_xml_placeholders(self):
        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {
                    'translations': [{
                        'text': 'Xin chao <x id="0"/><x id="1"/><x id="2"/>World<x id="3"/>'
                    }]
                }

        with patch('singletons.translator.requests.post', return_value=FakeResponse()) as post:
            response = translator.translate(
                'DeepL',
                'Hello {0.SimFirstName}\\n<b>World</b>',
                context='Package: sample.package',
                glossary_id='glossary-123',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, 'Xin chao {0.SimFirstName}\\n<b>World</b>')
        payload = post.call_args.kwargs['data']
        self.assertEqual(payload['context'], 'Package: sample.package')
        self.assertEqual(payload['glossary_id'], 'glossary-123')
        self.assertEqual(payload['tag_handling'], 'xml')
        self.assertIn('<x id="0"/>', payload['text'])
        self.assertNotIn('{0.SimFirstName}', payload['text'])

    def test_deepl_placeholder_restore_reports_missing_placeholder(self):
        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {'translations': [{'text': 'Xin chao'}]}

        with patch('singletons.translator.requests.post', return_value=FakeResponse()):
            response = translator.translate('DeepL', 'Hello {0.SimFirstName}')

        self.assertEqual(response.status_code, 409)
        self.assertIn('Missing placeholders', response.text)

    def test_deepl_character_estimate_counts_source_characters(self):
        rid = ResourceID(group=0, instance=1, type=0x220557DA)
        item = MainRecord(
            1,
            42,
            rid.instance,
            rid.group,
            'Hello',
            'Hello',
            FLAG_UNVALIDATED,
            rid,
            rid,
            'pkg',
            None,
            None,
            (1, 1, 4, 4),
            '',
        )

        self.assertEqual(estimate_deepl_characters([item, (0, item)]), 10)
        self.assertEqual(estimate_ai_characters([item, (0, item)]), 10)

    def test_ai_engines_appear_only_when_configured(self):
        self.assertFalse(ai_engine_available('Gemini'))
        self.assertFalse(ai_engine_available('OpenAI-compatible'))

        config.set_value('api', 'gemini_key', 'gemini-secret')
        config.set_value('api', 'openai_key', 'openai-secret')

        self.assertTrue(ai_engine_available('Gemini'))
        self.assertTrue(ai_engine_available('OpenAI-compatible'))
        self.assertIn('Gemini', translator.engines)
        self.assertIn('OpenAI-compatible', translator.engines)

    def test_gemini_translate_sends_prompt_and_restores_placeholders(self):
        config.set_value('api', 'gemini_key', 'gemini-secret')
        config.set_value('api', 'gemini_model', 'gemini-test')

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {'candidates': [{'content': {'parts': [{'text': 'Xin chao (0)'}]}}]}

        with patch('singletons.translator.requests.post', return_value=FakeResponse()) as post:
            response = translator.translate('Gemini', 'Hello {0.SimFirstName}', context='Package: sample.package')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, 'Xin chao {0.SimFirstName}')
        api_url, kwargs = post.call_args.args[0], post.call_args.kwargs
        self.assertEqual(api_url, 'https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent')
        self.assertEqual(kwargs['headers']['x-goog-api-key'], 'gemini-secret')
        prompt = kwargs['json']['contents'][0]['parts'][0]['text']
        self.assertIn('Package: sample.package', prompt)
        self.assertIn('Return exactly 1 line(s).', prompt)
        self.assertIn('(0)', prompt)

    def test_openai_compatible_translate_sends_chat_completion_request(self):
        config.set_value('api', 'openai_key', 'openai-secret')
        config.set_value('api', 'openai_base_url', 'https://example.test/api')
        config.set_value('api', 'openai_model', 'model-test')

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {'choices': [{'message': {'content': 'Xin chao (0)'}}]}

        with patch('singletons.translator.requests.post', return_value=FakeResponse()) as post:
            response = translator.translate('OpenAI-compatible', 'Hello {0.SimFirstName}')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, 'Xin chao {0.SimFirstName}')
        api_url, kwargs = post.call_args.args[0], post.call_args.kwargs
        self.assertEqual(api_url, 'https://example.test/api/v1/chat/completions')
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer openai-secret')
        self.assertEqual(kwargs['json']['model'], 'model-test')
        self.assertIn('Preserve placeholders', kwargs['json']['messages'][1]['content'])

    def test_ai_provider_rate_limit_error_is_user_friendly(self):
        config.set_value('api', 'gemini_key', 'gemini-secret')

        class FakeResponse:
            status_code = 429

            @staticmethod
            def json():
                return {'error': {'message': 'quota exhausted'}}

        with patch('singletons.translator.requests.post', return_value=FakeResponse()):
            response = translator.translate('Gemini', 'Hello')

        self.assertEqual(response.status_code, 429)
        self.assertIn('rate limit', response.text)
        self.assertIn('quota exhausted', response.text)

    def test_translation_chunk_passes_deepl_context_glossary_and_preserves_fast_newlines(self):
        request = TranslationChunkRequest(
            engine='DeepL',
            items=(
                TranslationItemSnapshot(index=0, source='Hello'),
                TranslationItemSnapshot(index=1, source='World'),
            ),
            fast=True,
            context='Package: sample.package',
            glossary_id='glossary-123',
        )

        with patch('windows.translate_dialog.translator.translate', return_value=Response(200, 'Xin chao\nThe gioi')) as call:
            result = translate_chunk_task(CancellationToken(), NoopReporter(), request)

        call.assert_called_once_with(
            'DeepL',
            'Hello\nWorld',
            context='Package: sample.package',
            glossary_id='glossary-123',
            preserve_newlines=True,
        )
        self.assertEqual(result.translations[0].text, 'Xin chao')
        self.assertEqual(result.translations[1].text, 'The gioi')

    def test_fast_ai_chunk_rejects_mismatched_line_count_without_auto_approving(self):
        request = TranslationChunkRequest(
            engine='Gemini',
            items=(
                TranslationItemSnapshot(index=0, source='Hello'),
                TranslationItemSnapshot(index=1, source='World'),
            ),
            fast=True,
        )

        with patch('windows.translate_dialog.translator.translate', return_value=Response(200, 'Only one line')):
            result = translate_chunk_task(CancellationToken(), NoopReporter(), request)

        self.assertEqual(result.translations, ())
        self.assertIn('Some lines could not be translated', result.warning)

    def test_edit_translation_task_returns_dto_without_ui_mutation(self):
        request = EditTranslationRequest(engine='Mock', source='Hello')

        with patch('windows.edit_dialog.translator.translate', return_value=Response(200, 'Bonjour')):
            result = edit_translation_task(CancellationToken(), NoopReporter(), request)

        self.assertEqual(result.text, 'Bonjour')
        self.assertEqual(result.error, '')

    def test_cancelled_translate_handle_does_not_apply_stale_result(self):
        rid = ResourceID(group=0, instance=1, type=0x220557DA)
        item = MainRecord(
            1,
            42,
            rid.instance,
            rid.group,
            'Hello',
            'Hello',
            FLAG_UNVALIDATED,
            rid,
            rid,
            'pkg',
            None,
            None,
            (1, 1, 4, 4),
            '',
        )

        class CancelledHandle:

            cancelled = True

        class RefreshTimer:

            started = False

            def start(self, _msecs):
                self.started = True

        handle = CancelledHandle()
        timer = RefreshTimer()
        dialog = TranslateDialog.__new__(TranslateDialog)
        dialog._TranslateDialog__items = [item]
        dialog._TranslateDialog__handles = [handle]
        dialog._TranslateDialog__refresh_timer = timer
        dialog._TranslateDialog__error = False
        dialog._TranslateDialog__log = []

        result = TranslationChunkResult(translations=(TranslationItemResult(0, 'Bonjour'),))
        TranslateDialog._TranslateDialog__translated_chunk(dialog, result, handle)

        self.assertEqual(item.translate, 'Hello')
        self.assertFalse(timer.started)


if __name__ == '__main__':
    unittest.main()
