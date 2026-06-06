# -*- coding: utf-8 -*-

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from packer.resource import ResourceID
from singletons.config import config
from singletons.translation_cache import TranslationCache
from singletons.translation_memory import TranslationMemory
from storages.records import MainRecord
from utils.constants import FLAG_UNVALIDATED
from windows.translate_dialog import TranslateDialog


def make_record(idx: int, source: str = 'Hello') -> MainRecord:
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
        'sample.package',
        None,
        None,
        (idx, idx, idx, idx),
        '',
    )


class TranslationCacheTests(unittest.TestCase):

    def setUp(self):
        config.set_value('translation', 'source', 'ENG_US')
        config.set_value('translation', 'destination', 'VI_VN')
        config.set_value('translation_cache', 'enabled', True)
        config.set_value('api', 'deepl_glossary_id', 'glossary-123')

    def test_cache_uses_exact_locale_engine_variant_and_source_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = TranslationCache(Path(tmpdir) / 'cache.sqlite3')
            cache.store('ENG_US', 'VI_VN', 'DeepL', 'glossary-123', 'Hello', 'Xin chao')

            self.assertEqual(cache.lookup('ENG_US', 'VI_VN', 'DeepL', 'glossary-123', 'Hello'), 'Xin chao')
            self.assertIsNone(cache.lookup('ENG_US', 'FRE_FR', 'DeepL', 'glossary-123', 'Hello'))
            self.assertIsNone(cache.lookup('ENG_US', 'VI_VN', 'Google', 'glossary-123', 'Hello'))
            self.assertIsNone(cache.lookup('ENG_US', 'VI_VN', 'DeepL', '', 'Hello'))
            self.assertIsNone(cache.lookup('ENG_US', 'VI_VN', 'DeepL', 'glossary-123', 'Hello!'))

    def test_cache_does_not_store_api_keys_or_source_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'cache.sqlite3'
            cache = TranslationCache(path)
            cache.store('ENG_US', 'VI_VN', 'DeepL', 'glossary-123', 'secret source', 'translated')

            conn = sqlite3.connect(path)
            try:
                columns = [row[1] for row in conn.execute('PRAGMA table_info(translations)').fetchall()]
                raw_values = ' '.join(str(row) for row in conn.execute('SELECT * FROM translations').fetchall())
            finally:
                conn.close()

            self.assertNotIn('source_text', columns)
            self.assertNotIn('api', raw_values.lower())
            self.assertNotIn('secret source', raw_values)

    def test_clear_removes_entries_and_keeps_database_usable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = TranslationCache(Path(tmpdir) / 'cache.sqlite3')
            cache.store('ENG_US', 'VI_VN', 'Google', '', 'Hello', 'Xin chao')

            self.assertEqual(cache.stats().entries, 1)
            cache.clear()

            self.assertEqual(cache.stats().entries, 0)
            self.assertIsNone(cache.lookup('ENG_US', 'VI_VN', 'Google', '', 'Hello'))

    def test_translate_dialog_reuses_cache_and_reports_missing_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = TranslationCache(Path(tmpdir) / 'cache.sqlite3')
            memory = TranslationMemory(Path(tmpdir) / 'memory.sqlite3')
            cache.store('ENG_US', 'VI_VN', 'DeepL', 'glossary-123', 'Hello', 'Xin chao')
            dialog = TranslateDialog.__new__(TranslateDialog)

            with patch('windows.translate_dialog.translation_cache', cache), \
                    patch('windows.translate_dialog.translation_memory', memory):
                cached, missing = TranslateDialog._TranslateDialog__cached_results(
                    dialog,
                    'DeepL',
                    [(0, make_record(1, 'Hello')), (1, make_record(2, 'World'))],
                )

            self.assertEqual(cached[0].index, 0)
            self.assertEqual(cached[0].text, 'Xin chao')
            self.assertEqual(missing[0][0], 1)

    def test_translate_dialog_reuses_translation_memory_after_cache_miss(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = TranslationCache(Path(tmpdir) / 'cache.sqlite3')
            memory = TranslationMemory(Path(tmpdir) / 'memory.sqlite3')
            memory.store('ENG_US', 'VI_VN', 'DeepL', 'glossary-123', 'Hello', 'Xin chao')
            dialog = TranslateDialog.__new__(TranslateDialog)

            with patch('windows.translate_dialog.translation_cache', cache), \
                    patch('windows.translate_dialog.translation_memory', memory):
                cached, missing = TranslateDialog._TranslateDialog__cached_results(
                    dialog,
                    'DeepL',
                    [(0, make_record(1, 'Hello'))],
                )

            self.assertEqual(cached[0].text, 'Xin chao')
            self.assertEqual(missing, [])

    def test_translate_dialog_stores_successful_translation_in_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = TranslationCache(Path(tmpdir) / 'cache.sqlite3')
            memory = TranslationMemory(Path(tmpdir) / 'memory.sqlite3')
            dialog = TranslateDialog.__new__(TranslateDialog)

            class ApiCombo:
                def currentText(self):
                    return 'DeepL'

            dialog.cb_api = ApiCombo()
            with patch('windows.translate_dialog.translation_cache', cache), \
                    patch('windows.translate_dialog.translation_memory', memory):
                TranslateDialog._TranslateDialog__store_cached_translation(
                    dialog,
                    make_record(1, 'Hello'),
                    'Xin chao',
                )

            self.assertEqual(cache.lookup('ENG_US', 'VI_VN', 'DeepL', 'glossary-123', 'Hello'), 'Xin chao')
            self.assertEqual(memory.lookup_exact('ENG_US', 'VI_VN', 'DeepL', 'glossary-123', 'Hello'), 'Xin chao')


if __name__ == '__main__':
    unittest.main()
