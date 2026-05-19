# -*- coding: utf-8 -*-

import csv
import os
import tempfile
import unittest

from storages.package_tasks import (
    TranslationHubCsvRequest,
    TranslationHubCsvRow,
    export_translation_hub_csv_task,
)
from utils.constants import FLAG_TRANSLATED, FLAG_UNVALIDATED
from utils.task_runner import CancellationToken, TaskReporter


class NoopReporter(TaskReporter):

    def __init__(self):
        pass

    def progress(self, current: int = 0, total: int = 0, message: str = '') -> None:
        pass


class TranslationHubCsvTests(unittest.TestCase):

    def export_rows(self, rows, include_untranslated=True):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'hub.csv')
            request = TranslationHubCsvRequest(
                path=path,
                rows=tuple(rows),
                include_untranslated=include_untranslated,
                message='Exporting Translation Hub CSV...'
            )

            result = export_translation_hub_csv_task(CancellationToken(), NoopReporter(), request)
            with open(path, 'rb') as fp:
                raw = fp.read()
            with open(path, 'r', encoding='utf-8-sig', newline='') as fp:
                data = list(csv.reader(fp))

            return result, raw, data

    def test_writes_exact_headers_hex_keys_and_utf8_bom(self):
        result, raw, data = self.export_rows((
            TranslationHubCsvRow(
                string_id=0x3810DE7A,
                source_text='Hello',
                translated_text='Xin chào Đặng',
                flag=FLAG_TRANSLATED
            ),
            TranslationHubCsvRow(
                string_id=1,
                source_text='Quoted',
                translated_text='A, "quoted" value',
                flag=FLAG_TRANSLATED
            ),
        ))

        self.assertEqual(result.row_count, 2)
        self.assertTrue(raw.startswith(b'\xef\xbb\xbf'))
        self.assertEqual(data[0], ['Key', 'Translated Text'])
        self.assertEqual(data[1], ['0x3810DE7A', 'Xin chào Đặng'])
        self.assertEqual(data[2], ['0x00000001', 'A, "quoted" value'])

    def test_deduplicates_exact_record_keys_and_preserves_variations(self):
        result, _raw, data = self.export_rows((
            TranslationHubCsvRow(42, 'Hello', 'Bonjour', FLAG_TRANSLATED),
            TranslationHubCsvRow(42, 'Hello', 'Bonjour', FLAG_TRANSLATED),
            TranslationHubCsvRow(42, 'Hi', 'Bonjour', FLAG_TRANSLATED),
            TranslationHubCsvRow(42, 'Hello', 'Salut', FLAG_TRANSLATED),
            TranslationHubCsvRow(7, 'Skip me', 'Skip me', FLAG_UNVALIDATED),
        ), include_untranslated=False)

        self.assertEqual(result.row_count, 3)
        self.assertEqual(data, [
            ['Key', 'Translated Text'],
            ['0x0000002A', 'Bonjour'],
            ['0x0000002A', 'Bonjour'],
            ['0x0000002A', 'Salut'],
        ])


if __name__ == '__main__':
    unittest.main()
