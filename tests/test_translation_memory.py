# -*- coding: utf-8 -*-

import sqlite3
import tempfile
import unittest
import csv
from pathlib import Path

from singletons.config import config
from singletons.translation_memory import (
    STATUS_APPROVED,
    STATUS_DRAFT,
    TranslationMemory,
    TranslationMemoryEntry,
)
from storages.dictionaries import DictionariesStorage
from utils.constants import RECORD_DICTIONARY_PACKAGE, RECORD_DICTIONARY_TRANSLATE


class TranslationMemoryTests(unittest.TestCase):

    def setUp(self):
        config.set_value('translation_cache', 'enabled', True)

    def test_exact_lookup_uses_locale_engine_variant_and_normalized_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = TranslationMemory(Path(tmpdir) / 'memory.sqlite3')
            memory.store('ENG_US', 'VI_VN', 'Ollama', 'local|model-a', 'Hello\nSim', 'Xin chao\\nSim')

            self.assertEqual(
                memory.lookup_exact('ENG_US', 'VI_VN', 'Ollama', 'local|model-a', 'Hello\\nSim'),
                'Xin chao\\nSim',
            )
            self.assertIsNone(memory.lookup_exact('ENG_US', 'FRE_FR', 'Ollama', 'local|model-a', 'Hello\\nSim'))
            self.assertIsNone(memory.lookup_exact('ENG_US', 'VI_VN', 'Ollama', 'local|model-b', 'Hello\\nSim'))

    def test_fuzzy_suggestions_rank_approved_provider_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = TranslationMemory(Path(tmpdir) / 'memory.sqlite3')
            memory.store(
                'ENG_US',
                'VI_VN',
                'Gemini',
                'gemini-2.5-flash',
                'Hello {0.SimFirstName}, welcome home!',
                'Approved translation {0.SimFirstName}, welcome home!',
                status=STATUS_APPROVED,
            )
            memory.store(
                'ENG_US',
                'VI_VN',
                'Google',
                '',
                'Hello {0.SimFirstName}, welcome home!',
                'Draft translation {0.SimFirstName}, welcome home!',
                status=STATUS_DRAFT,
            )

            suggestions = memory.suggestions(
                'ENG_US',
                'VI_VN',
                'Hello {0.SimFirstName}, welcome back home!',
                engine='Gemini',
                variant='gemini-2.5-flash',
            )

            self.assertGreaterEqual(len(suggestions), 1)
            self.assertEqual(suggestions[0].engine, 'Gemini')
            self.assertIn('{0.SimFirstName}', suggestions[0].translated_text)

    def test_memory_does_not_store_api_keys_or_private_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'memory.sqlite3'
            memory = TranslationMemory(path)
            memory.store(
                'ENG_US',
                'VI_VN',
                'OpenAI-compatible',
                'https://api.openai.com|gpt-4o-mini',
                'secret source',
                'translated',
                package=r'C:\Users\Administrator\private\sample.package',
            )

            conn = sqlite3.connect(path)
            try:
                raw_values = ' '.join(str(row) for row in conn.execute('SELECT * FROM entries').fetchall())
            finally:
                conn.close()

            self.assertNotIn('sk-', raw_values)
            self.assertNotIn(r'C:\Users\Administrator\private', raw_values)
            self.assertIn('sample.package', raw_values)

    def test_clear_removes_entries_and_keeps_database_usable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = TranslationMemory(Path(tmpdir) / 'memory.sqlite3')
            memory.store('ENG_US', 'VI_VN', 'Google', '', 'Hello', 'Xin chao')

            self.assertEqual(memory.stats().entries, 1)
            memory.clear()

            self.assertEqual(memory.stats().entries, 0)
            self.assertIsNone(memory.lookup_exact('ENG_US', 'VI_VN', 'Google', '', 'Hello'))

    def test_group_stats_and_filtered_clear_support_memory_management(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = TranslationMemory(Path(tmpdir) / 'memory.sqlite3')
            memory.store('ENG_US', 'VI_VN', 'Google', '', 'Hello', 'Xin chao')
            memory.store('ENG_US', 'VI_VN', 'Ollama', 'local|translategemma:12b', 'Goodbye', 'Tam biet')
            memory.store('ENG_US', 'FRE_FR', 'Google', '', 'Chair', 'Chaise')

            groups = memory.group_stats()
            self.assertEqual(memory.count(source_locale='ENG_US', destination_locale='VI_VN'), 2)
            self.assertEqual(memory.count(engine='Google'), 2)
            self.assertTrue(any(group.engine == 'Ollama' and group.entries == 1 for group in groups))

            memory.clear(source_locale='ENG_US', destination_locale='VI_VN')

            self.assertEqual(memory.count(), 1)
            self.assertIsNone(memory.lookup_exact('ENG_US', 'VI_VN', 'Google', '', 'Hello'))
            self.assertEqual(memory.lookup_exact('ENG_US', 'FRE_FR', 'Google', '', 'Chair'), 'Chaise')

    def test_export_import_csv_roundtrips_without_private_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = TranslationMemory(Path(tmpdir) / 'source.sqlite3')
            source.store(
                'ENG_US',
                'VI_VN',
                'OpenAI-compatible',
                'https://api.openai.com|gpt-4o-mini',
                'Hello {0.SimFirstName}',
                'Xin chao {0.SimFirstName}',
                status=STATUS_DRAFT,
                package=r'C:\Users\Administrator\private\sample.package',
                record_id=123,
                instance=456,
            )
            csv_path = Path(tmpdir) / 'memory.csv'

            self.assertEqual(source.export_csv(csv_path), 1)
            raw = csv_path.read_text(encoding='utf-8-sig')
            self.assertNotIn(r'C:\Users\Administrator\private', raw)
            self.assertIn('sample.package', raw)

            imported = TranslationMemory(Path(tmpdir) / 'imported.sqlite3')
            result = imported.import_csv(csv_path)

            self.assertEqual(result.imported, 1)
            self.assertEqual(result.skipped, 0)
            self.assertEqual(
                imported.lookup_exact(
                    'ENG_US',
                    'VI_VN',
                    'OpenAI-compatible',
                    'https://api.openai.com|gpt-4o-mini',
                    'Hello {0.SimFirstName}',
                ),
                'Xin chao {0.SimFirstName}',
            )

    def test_import_csv_rejects_missing_required_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / 'bad.csv'
            with csv_path.open('w', encoding='utf-8', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=('source_locale', 'translated_text'))
                writer.writeheader()
                writer.writerow({'source_locale': 'ENG_US', 'translated_text': 'Xin chao'})

            memory = TranslationMemory(Path(tmpdir) / 'memory.sqlite3')

            with self.assertRaises(ValueError):
                memory.import_csv(csv_path)

    def test_dictionary_storage_replaces_transient_memory_suggestions(self):
        storage = DictionariesStorage()
        storage.model.append([['sample', 'Hello source', 'Bonjour dictionary', 12]])

        storage.replace_translation_memory_suggestions((
            TranslationMemoryEntry(
                'ENG_US',
                'VI_VN',
                'Gemini',
                'gemini-2.5-flash',
                'Similar source',
                'Memory suggestion',
                STATUS_APPROVED,
                score=0.91,
            ),
        ))
        storage.proxy.filter('Hello source')

        packages = [row[RECORD_DICTIONARY_PACKAGE] for row in storage.model.filtered]
        translations = [row[RECORD_DICTIONARY_TRANSLATE] for row in storage.model.filtered]
        self.assertIn('sample', packages)
        self.assertTrue(any(str(package).startswith('tm ') for package in packages))
        self.assertIn('Memory suggestion', translations)

        storage.replace_translation_memory_suggestions(())

        self.assertFalse(any(str(row[RECORD_DICTIONARY_PACKAGE]).startswith('tm ') for row in storage.model.items))


if __name__ == '__main__':
    unittest.main()
