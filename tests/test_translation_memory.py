# -*- coding: utf-8 -*-

import sqlite3
import tempfile
import unittest
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
