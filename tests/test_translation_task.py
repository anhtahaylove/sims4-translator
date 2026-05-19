# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch

from singletons.translator import Response
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
