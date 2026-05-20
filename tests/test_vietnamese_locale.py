# -*- coding: utf-8 -*-

import os
import tempfile
import unittest
from unittest.mock import patch

from packer.resource import ResourceID
from packer.stbl import Stbl
from scripts.synthetic_package import create_synthetic_package, read_stbl_by_locale
from singletons.config import ConfigManager
from singletons.config import config
from singletons.languages import languages
from singletons.state import app_state
from singletons.translator import translator
from storages.package_tasks import (
    ExportRecordDTO,
    StructuredExportRequest,
    export_structured_task,
)
from storages.packages import PackagesStorage
from utils.constants import EXPORT_STBL, FLAG_VALIDATED
from utils.task_runner import CancellationToken, TaskReporter


class NoopReporter(TaskReporter):

    def __init__(self):
        pass

    def progress(self, current: int = 0, total: int = 0, message: str = '') -> None:
        pass


class VietnameseLocaleTests(unittest.TestCase):

    def setUp(self):
        config.set_value('translation', 'source', 'ENG_US')
        config.set_value('translation', 'destination', 'VI_VN')
        config.set_value('api', 'deepl_key', '')
        config.set_value('api', 'deepl_glossary_id', '')
        config.set_value('group', 'original', True)
        config.set_value('group', 'highbit', False)
        config.set_value('save', 'experemental', False)
        config.set_value('save', 'backup', False)
        app_state.set_current_package(None)
        app_state.set_current_instance(0)

    def test_vietnamese_locale_is_registered_as_custom_destination(self):
        lang = languages.by_locale('VI_VN')

        self.assertIsNotNone(lang)
        self.assertEqual(lang.code, '0x14')
        self.assertEqual(lang.google, 'vi')
        self.assertEqual(lang.deepl, 'VI')
        self.assertIs(languages.by_code('0x14'), lang)
        self.assertIn('VI_VN', languages.locales)

    def test_default_translation_pair_is_english_to_vietnamese(self):
        self.assertEqual(ConfigManager.DEFAULTS['translation']['source'], 'ENG_US')
        self.assertEqual(ConfigManager.DEFAULTS['translation']['destination'], 'VI_VN')

    def test_deepl_engine_supports_english_to_vietnamese_when_key_is_configured(self):
        config.set_value('api', 'deepl_key', 'sample:fx')

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {'translations': [{'text': 'Xin chao'}]}

        with patch('singletons.translator.requests.post', return_value=FakeResponse()) as post:
            response = translator.translate('DeepL', 'Hello')

        self.assertIn('DeepL', translator.engines)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, 'Xin chao')

        api_url, kwargs = post.call_args.args[0], post.call_args.kwargs
        self.assertEqual(api_url, 'https://api-free.deepl.com/v2/translate')
        self.assertEqual(kwargs['data']['source_lang'], 'EN')
        self.assertEqual(kwargs['data']['target_lang'], 'VI')
        self.assertEqual(kwargs['data']['split_sentences'], 'nonewlines')
        self.assertEqual(kwargs['data']['preserve_formatting'], '1')
        self.assertNotIn('tag_handling', kwargs['data'])

    def test_resource_id_converts_to_vietnamese_language_slot(self):
        source = ResourceID(group=0, instance=0x0000000000000001, type=0x220557DA)

        converted = source.convert_instance('VI_VN')

        self.assertEqual(converted.instance, 0x1400000000000001)
        self.assertEqual(converted.language_code, '0x14')
        self.assertEqual(converted.language, 'VI_VN')

    def test_structured_export_can_target_vietnamese_stbl(self):
        source = ResourceID(group=0, instance=0x0000000000000001, type=0x220557DA)
        records = (
            ExportRecordDTO(source, 42, 'Hello', 'Xin chao', FLAG_VALIDATED, 'synthetic.package', ''),
            ExportRecordDTO(source, 7, 'World', 'The gioi', FLAG_VALIDATED, 'synthetic.package', ''),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'out_vi.stbl')
            result = export_structured_task(
                CancellationToken(),
                NoopReporter(),
                StructuredExportRequest(
                    export_type=EXPORT_STBL,
                    filename=path,
                    records=records,
                    include_untranslated=True,
                    destination_locale='VI_VN',
                    message='Exporting translate...',
                ),
            )
            with open(path, 'rb') as fp:
                parsed = Stbl(source.convert_instance('VI_VN'), fp.read()).strings

        self.assertEqual(result.string_count, 2)
        self.assertEqual(parsed, {42: 'Xin chao', 7: 'The gioi'})

    def test_save_and_finalize_can_write_vietnamese_destination_tables(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            package_path = os.path.join(tmpdir, 'synthetic.package')
            saved_path = os.path.join(tmpdir, 'saved_vi.package')
            finalized_path = os.path.join(tmpdir, 'finalized_vi.package')
            create_synthetic_package(package_path, include_duplicate=False)

            storage = PackagesStorage()
            app_state.set_packages_storage(storage)
            storage.load(package_path)
            for item in storage.model.items:
                item.translate = 'Xin chao' if item.id == 42 else 'The gioi'
                item.flag = FLAG_VALIDATED

            save_result = storage.save(saved_path, asynchronous=False)
            finalize_result = storage.finalize(package_path, finalized_path, asynchronous=False)

            saved_tables = read_stbl_by_locale(saved_path, 'VI_VN')
            finalized_tables = read_stbl_by_locale(finalized_path, 'VI_VN')

        self.assertEqual(save_result.resource_count, 1)
        self.assertEqual(finalize_result.resource_count, 1)
        self.assertEqual(next(iter(saved_tables.values())), {42: 'Xin chao', 7: 'The gioi'})
        self.assertEqual(next(iter(finalized_tables.values())), {42: 'Xin chao', 7: 'The gioi'})


if __name__ == '__main__':
    unittest.main()
