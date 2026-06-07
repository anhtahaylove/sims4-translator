# -*- coding: utf-8 -*-

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.termbase import (
    clear_user_termbase,
    effective_termbase_terms,
    ensure_user_termbase,
    export_effective_termbase,
    import_user_termbase,
    termbase_stats,
    user_termbase_entries,
)


class TermbaseTests(unittest.TestCase):

    def test_effective_terms_include_bundled_vietnamese_terms(self):
        terms = effective_termbase_terms('VI_VN')

        self.assertIn(('Trait', 'Đặc điểm'), terms)
        self.assertIn(('Household', 'Hộ gia đình'), terms)

    def test_user_import_overrides_bundled_terms(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'custom.csv'
            source.write_text(
                'source_term,expected_translation,note\n'
                'Trait,tinh cach,project term\n'
                'Lot,lô đất,project addition\n',
                encoding='utf-8',
            )
            with patch.dict(os.environ, {'SIMS4_TRANSLATOR_CONFIG_DIR': tmpdir}):
                result = import_user_termbase('VI_VN', source)
                terms = dict(effective_termbase_terms('VI_VN'))
                stats = termbase_stats('VI_VN')

        self.assertEqual(result.imported, 2)
        self.assertEqual(terms['Trait'], 'tinh cach')
        self.assertEqual(terms['Lot'], 'lô đất')
        self.assertEqual(stats.user_entries, 2)

    def test_export_effective_termbase_writes_reviewable_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / 'export.csv'

            count = export_effective_termbase('VI_VN', output)
            raw = output.read_text(encoding='utf-8-sig')

        self.assertGreaterEqual(count, 5)
        self.assertIn('source_term,expected_translation,note', raw)
        self.assertIn('Trait,Đặc điểm', raw)

    def test_ensure_and_clear_user_termbase_are_locale_scoped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {'SIMS4_TRANSLATOR_CONFIG_DIR': tmpdir}):
                path = ensure_user_termbase('VI_VN')
                self.assertTrue(path.exists())
                self.assertGreaterEqual(len(user_termbase_entries('VI_VN')), 5)

                cleared = clear_user_termbase('VI_VN')

                self.assertGreaterEqual(cleared, 5)
                self.assertFalse(path.exists())
                self.assertEqual(len(user_termbase_entries('VI_VN')), 0)


if __name__ == '__main__':
    unittest.main()
