# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from singletons.config import config
from singletons.translation_cache import TranslationCache
from singletons.translation_memory import TranslationMemory
from singletons.translator import (
    DeepLUsage,
    OLLAMA_RECOMMENDED_MODEL,
    OllamaModels,
    ProviderModels,
    Response,
    ai_engine_available,
    deepl_endpoint,
    deepl_usage,
    estimate_ai_characters,
    estimate_deepl_characters,
    gemini_models,
    ollama_base_url,
    ollama_models,
    openai_compatible_models,
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
from utils.constants import FLAG_UNVALIDATED, FLAG_VALIDATED


class NoopReporter(TaskReporter):

    def __init__(self):
        pass

    def progress(self, current: int = 0, total: int = 0, message: str = '') -> None:
        pass


class FakeSignal:

    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class FakeHandle:

    def __init__(self):
        self.cancelled = False
        self.result = FakeSignal()
        self.error = FakeSignal()
        self.finished = FakeSignal()

    def cancel(self):
        self.cancelled = True


class FakeControl:

    def __init__(self, text=''):
        self.enabled = True
        self.text = text

    def setEnabled(self, enabled):
        self.enabled = enabled

    def setText(self, text):
        self.text = text

    def currentText(self):
        return self.text


class FakeRadio(FakeControl):

    def __init__(self, text='', checked=False):
        super().__init__(text)
        self.checked = checked

    def isChecked(self):
        return self.checked

    def setChecked(self, checked):
        self.checked = checked


class FakeLog:

    def __init__(self):
        self.text = ''

    def setText(self, text):
        self.text = text

    def clear(self):
        self.text = ''

    def verticalScrollBar(self):
        return self

    def maximum(self):
        return 0

    def setValue(self, _value):
        pass


class FakeTimer:

    def __init__(self):
        self.started = False
        self.stopped = False

    def start(self, _msecs):
        self.started = True

    def isActive(self):
        return False

    def stop(self):
        self.stopped = True


class FakeUndo:

    def wrap(self, _item):
        pass

    def commit(self):
        pass


def make_translate_dialog_for_retry(items):
    dialog = TranslateDialog.__new__(TranslateDialog)
    dialog.cb_api = FakeControl('Google')
    dialog.rb_all = FakeRadio()
    dialog.rb_validated = FakeRadio()
    dialog.rb_validated_partial = FakeRadio()
    dialog.rb_partial = FakeRadio()
    dialog.rb_selection = FakeRadio()
    dialog.rb_slow = FakeRadio(checked=False)
    dialog.rb_fast = FakeRadio(checked=True)
    dialog.btn_cancel = FakeControl()
    dialog.btn_translate = FakeControl()
    dialog.btn_retry_failed = FakeControl()
    dialog.edt_log = FakeLog()
    dialog._TranslateDialog__items = list(items)
    dialog._TranslateDialog__handles = []
    dialog._TranslateDialog__chunk_items_by_handle = {}
    dialog._TranslateDialog__failed_item_indexes = set()
    dialog._TranslateDialog__last_failed_items = []
    dialog._TranslateDialog__stopping_for_error = False
    dialog._TranslateDialog__progress = 0
    dialog._TranslateDialog__translating = False
    dialog._TranslateDialog__error = False
    dialog._TranslateDialog__log = []
    dialog._TranslateDialog__refresh_timer = FakeTimer()
    return dialog


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
        config.set_value('api', 'ollama_enabled', False)
        config.set_value('api', 'ollama_base_url', 'http://localhost:11434')
        config.set_value('api', 'ollama_model', OLLAMA_RECOMMENDED_MODEL)

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
        self.assertEqual(kwargs['timeout'], 10)

        with patch('singletons.translator.requests.get', return_value=FakeResponse()) as get:
            deepl_usage('abc:fx', timeout=3)

        self.assertEqual(get.call_args.kwargs['timeout'], 3)

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
        self.assertFalse(ai_engine_available('Ollama'))

        config.set_value('api', 'gemini_key', 'gemini-secret')
        config.set_value('api', 'openai_key', 'openai-secret')
        config.set_value('api', 'ollama_enabled', True)

        self.assertTrue(ai_engine_available('Gemini'))
        self.assertTrue(ai_engine_available('OpenAI-compatible'))
        self.assertTrue(ai_engine_available('Ollama'))
        self.assertIn('Gemini', translator.engines)
        self.assertIn('OpenAI-compatible', translator.engines)
        self.assertIn('Ollama', translator.engines)

    def test_ollama_base_url_normalizes_config_and_input(self):
        self.assertEqual(ollama_base_url('http://localhost:11434/'), 'http://localhost:11434')
        config.set_value('api', 'ollama_base_url', ' http://example.test:11434/ ')
        self.assertEqual(ollama_base_url(), 'http://example.test:11434')

    def test_ollama_models_parses_local_tags_and_handles_server_down(self):
        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {
                    'models': [
                        {'model': 'translategemma:12b'},
                        {'name': 'gemma4:e4b'},
                        {'model': 'translategemma:12b'},
                    ]
                }

        with patch('singletons.translator.requests.get', return_value=FakeResponse()) as get:
            result = ollama_models('http://localhost:11434/')

        self.assertEqual(result, OllamaModels(200, ('translategemma:12b', 'gemma4:e4b'), ''))
        self.assertEqual(get.call_args.args[0], 'http://localhost:11434/api/tags')

        with patch('singletons.translator.requests.get', side_effect=RuntimeError('offline')):
            result = ollama_models('http://localhost:11434')

        self.assertEqual(result.status_code, 503)
        self.assertIn('Ollama is not reachable', result.message)

    def test_gemini_models_lists_generate_content_models(self):
        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {
                    'models': [
                        {
                            'name': 'models/gemini-2.5-flash',
                            'supportedGenerationMethods': ['generateContent'],
                        },
                        {
                            'name': 'models/text-embedding',
                            'supportedGenerationMethods': ['embedContent'],
                        },
                        {
                            'name': 'models/gemini-2.5-flash',
                            'supportedGenerationMethods': ['generateContent'],
                        },
                    ]
                }

        with patch('singletons.translator.requests.get', return_value=FakeResponse()) as get:
            result = gemini_models('gemini-secret', timeout=4)

        self.assertEqual(result, ProviderModels(200, ('gemini-2.5-flash',), ''))
        self.assertEqual(get.call_args.args[0], 'https://generativelanguage.googleapis.com/v1beta/models')
        self.assertEqual(get.call_args.kwargs['params']['key'], 'gemini-secret')
        self.assertEqual(get.call_args.kwargs['timeout'], 4)

    def test_gemini_models_reports_auth_errors(self):
        class FakeResponse:
            status_code = 403

            @staticmethod
            def json():
                return {'error': {'message': 'bad key'}}

        with patch('singletons.translator.requests.get', return_value=FakeResponse()):
            result = gemini_models('bad-key')

        self.assertEqual(result.status_code, 403)
        self.assertEqual(result.models, ())
        self.assertIn('rejected', result.message)
        self.assertIn('bad key', result.message)

    def test_openai_compatible_models_lists_ids_and_preserves_base_url_contract(self):
        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {
                    'data': [
                        {'id': 'gpt-4o-mini'},
                        {'id': 'gpt-4.1-mini'},
                        {'id': 'gpt-4o-mini'},
                    ]
                }

        with patch('singletons.translator.requests.get', return_value=FakeResponse()) as get:
            result = openai_compatible_models('openai-secret', 'https://example.test/', timeout=6)

        self.assertEqual(result, ProviderModels(200, ('gpt-4o-mini', 'gpt-4.1-mini'), ''))
        self.assertEqual(get.call_args.args[0], 'https://example.test/v1/models')
        self.assertEqual(get.call_args.kwargs['headers']['Authorization'], 'Bearer openai-secret')
        self.assertEqual(get.call_args.kwargs['timeout'], 6)

    def test_openai_compatible_models_reports_unavailable_list_endpoint(self):
        class FakeResponse:
            status_code = 404
            text = 'not found'

            @staticmethod
            def json():
                return {'error': {'message': 'missing route'}}

        with patch('singletons.translator.requests.get', return_value=FakeResponse()):
            result = openai_compatible_models('openai-secret', 'https://example.test')

        self.assertEqual(result.status_code, 404)
        self.assertEqual(result.models, ())
        self.assertIn('endpoint was not found', result.message)
        self.assertIn('missing route', result.message)

    def test_ollama_translate_sends_chat_payload_and_restores_placeholders(self):
        config.set_value('api', 'ollama_enabled', True)
        config.set_value('api', 'ollama_base_url', 'http://localhost:11434/')
        config.set_value('api', 'ollama_model', 'translategemma:12b')

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {'message': {'content': 'Xin chao (0)'}}

        with patch('singletons.translator.requests.post', return_value=FakeResponse()) as post:
            response = translator.translate('Ollama', 'Hello {0.SimFirstName}', context='Package: sample.package')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, 'Xin chao {0.SimFirstName}')
        api_url, kwargs = post.call_args.args[0], post.call_args.kwargs
        self.assertEqual(api_url, 'http://localhost:11434/api/chat')
        self.assertEqual(kwargs['json']['model'], 'translategemma:12b')
        self.assertFalse(kwargs['json']['stream'])
        self.assertEqual(kwargs['json']['options']['temperature'], 0.2)
        prompt = kwargs['json']['messages'][0]['content']
        self.assertIn('professional English (en) to Vietnamese (vi-VN) game localization translator', prompt)
        self.assertIn('Return exactly 1 line(s).', prompt)
        self.assertIn('Package: sample.package', prompt)
        self.assertIn('(0)', prompt)

    def test_provider_translate_accepts_short_request_timeout_for_options_checks(self):
        config.set_value('api', 'ollama_enabled', True)
        config.set_value('api', 'ollama_base_url', 'http://localhost:11434')
        config.set_value('api', 'ollama_model', 'translategemma:12b')

        class FakeOllamaResponse:
            status_code = 200

            @staticmethod
            def json():
                return {'message': {'content': 'Xin chao'}}

        with patch('singletons.translator.requests.post', return_value=FakeOllamaResponse()) as post:
            translator.translate('Ollama', 'Hello', request_timeout=7)

        self.assertEqual(post.call_args.kwargs['timeout'], 7)

    def test_ollama_missing_model_error_is_actionable(self):
        config.set_value('api', 'ollama_enabled', True)

        class FakeResponse:
            status_code = 404
            text = 'model not found'

            @staticmethod
            def json():
                return {'error': 'model not found'}

        with patch('singletons.translator.requests.post', return_value=FakeResponse()):
            response = translator.translate('Ollama', 'Hello')

        self.assertEqual(response.status_code, 404)
        self.assertIn('ollama pull translategemma:12b', response.text)

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

    def test_ollama_cache_variant_uses_base_url_and_model(self):
        config.set_value('api', 'ollama_base_url', 'http://localhost:11434/')
        config.set_value('api', 'ollama_model', 'translategemma:12b')

        self.assertEqual(
            TranslateDialog._TranslateDialog__cache_variant('Ollama'),
            'http://localhost:11434|translategemma:12b',
        )

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

    def test_warning_chunk_records_failed_items_for_retry(self):
        first = self._record(1, 'First')
        second = self._record(2, 'Second')
        dialog = make_translate_dialog_for_retry([first, second])
        handle = FakeHandle()
        dialog._TranslateDialog__handles = [handle]
        dialog._TranslateDialog__chunk_items_by_handle = {
            handle: ((0, first), (1, second)),
        }
        dialog._TranslateDialog__progress = 1
        dialog._TranslateDialog__translating = True

        result = TranslationChunkResult(warning='Some lines could not be translated.')
        with patch('windows.translate_dialog.undo', FakeUndo()):
            TranslateDialog._TranslateDialog__translated_chunk(dialog, result, handle)
            TranslateDialog._TranslateDialog__finished_translate_chunk(dialog, False, handle)

        self.assertEqual(dialog._TranslateDialog__last_failed_items, [first, second])
        self.assertTrue(dialog.btn_retry_failed.enabled)
        self.assertIn('Retry available for 2 failed/skipped record(s).', dialog.edt_log.text)

    def test_retry_failed_only_uses_cache_before_line_by_line_network(self):
        first = self._record(1, 'Cached source')
        second = self._record(2, 'Network source')
        dialog = make_translate_dialog_for_retry([first, second])
        dialog._TranslateDialog__last_failed_items = [first, second]
        config.set_value('translation_cache', 'enabled', True)

        class Runner:

            def __init__(self):
                self.requests = []

            def start(self, _fn, request, job_name=''):
                self.requests.append((request, job_name))
                return FakeHandle()

        runner = Runner()
        dialog._TranslateDialog__runner = runner

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = TranslationCache(Path(tmpdir) / 'cache.sqlite3')
            memory = TranslationMemory(Path(tmpdir) / 'memory.sqlite3')
            cache.store('ENG_US', 'VI_VN', 'Google', '', 'Cached source', 'Cached translation')

            with patch('windows.translate_dialog.translation_cache', cache), \
                    patch('windows.translate_dialog.translation_memory', memory), \
                    patch('windows.translate_dialog.undo', FakeUndo()):
                TranslateDialog.retry_failed_click(dialog)

        self.assertEqual(first.translate, 'Cached translation')
        self.assertEqual(first.flag, FLAG_VALIDATED)
        self.assertEqual(len(runner.requests), 1)
        request = runner.requests[0][0]
        self.assertFalse(request.fast)
        self.assertEqual([item.source for item in request.items], ['Network source'])

    @staticmethod
    def _record(idx: int, source: str) -> MainRecord:
        rid = ResourceID(group=0, instance=idx, type=0x220557DA)
        return MainRecord(
            idx,
            idx,
            rid.instance,
            rid.group,
            source,
            source,
            FLAG_UNVALIDATED,
            rid,
            rid,
            'pkg',
            None,
            None,
            (idx, idx, idx, idx),
            '',
        )


if __name__ == '__main__':
    unittest.main()
