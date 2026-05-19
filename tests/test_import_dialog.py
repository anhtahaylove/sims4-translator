# -*- coding: utf-8 -*-

import unittest

from packer.resource import ResourceID
from singletons.signals import window_signals
from singletons.state import app_state
from singletons.undo import undo
from storages.records import MainRecord
from utils.constants import FLAG_TRANSLATED, FLAG_UNVALIDATED
from windows.import_dialog import ImportDialog, ImportStats


class Checked:

    def __init__(self, value=False):
        self.value = value

    def isChecked(self):
        return self.value


class FakePackage:

    modified = False

    def modify(self, state=True):
        self.modified = state


class FakeTableView:

    def __init__(self):
        self.refreshed = False

    def selected_items(self):
        return []

    def refresh(self):
        self.refreshed = True


class FakeStorage:

    def __init__(self, items, table=None):
        self.items_list = list(items) if isinstance(items, (list, tuple)) and not isinstance(items, MainRecord) else [items]
        self.item = self.items_list[0]
        self.table = table if table is not None else {self.item.id: 'Xin chao'}
        self.package = FakePackage()

    def read_stbl(self, _filename):
        return self.table

    def items(self):
        return self.items_list

    def find(self, _key):
        return self.package


class ImportDialogTests(unittest.TestCase):

    def setUp(self):
        undo.clean()

    def test_import_refreshes_main_table_after_applying_translation(self):
        rid = ResourceID(group=0, instance=1, type=0x220557DA)
        item = MainRecord(
            1,
            0x2A,
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

        storage = FakeStorage(item)
        tableview = FakeTableView()
        app_state.set_packages_storage(storage)
        app_state.set_tableview(tableview)
        messages = []
        window_signals.log.connect(messages.append)

        dialog = ImportDialog.__new__(ImportDialog)
        dialog.filename = 'translations.stbl'
        dialog.rb_selection = Checked(False)
        dialog.rb_validated = Checked(False)
        dialog.rb_validated_partial = Checked(False)
        dialog.rb_partial = Checked(False)
        dialog.rb_all = Checked(True)
        dialog.cb_replace = Checked(True)

        try:
            stats = ImportDialog.translate(dialog)
        finally:
            window_signals.log.disconnect(messages.append)

        self.assertEqual(item.translate, 'Xin chao')
        self.assertTrue(tableview.refreshed)
        self.assertEqual(stats, ImportStats(applied=1, unchanged=0, skipped_by_mode=0, missing=0))
        self.assertTrue(any('Imported 1 translations, unchanged 0, skipped 0, missing 0' in message
                            for message in messages))

    def test_import_returns_stats_and_does_not_refresh_without_changes(self):
        rid = ResourceID(group=0, instance=1, type=0x220557DA)
        changed = MainRecord(
            1, 0x2A, rid.instance, rid.group, 'Hello', 'Hello', FLAG_UNVALIDATED,
            rid, rid, 'pkg', None, None, (1, 1, 4, 4), '',
        )
        unchanged = MainRecord(
            2, 0x2B, rid.instance, rid.group, 'Same', 'Same translated', FLAG_UNVALIDATED,
            rid, rid, 'pkg', None, None, (2, 2, 5, 5), '',
        )
        skipped = MainRecord(
            3, 0x2C, rid.instance, rid.group, 'Skip', 'Skip old', FLAG_TRANSLATED,
            rid, rid, 'pkg', None, None, (3, 3, 6, 6), '',
        )
        missing = MainRecord(
            4, 0x2D, rid.instance, rid.group, 'Missing', 'Missing old', FLAG_UNVALIDATED,
            rid, rid, 'pkg', None, None, (4, 4, 7, 7), '',
        )

        table = {
            changed.id: 'Xin chao',
            unchanged.id: unchanged.translate,
            skipped.id: 'Skipped translation',
        }
        storage = FakeStorage([changed, unchanged, skipped, missing], table)
        tableview = FakeTableView()
        app_state.set_packages_storage(storage)
        app_state.set_tableview(tableview)

        dialog = ImportDialog.__new__(ImportDialog)
        dialog.filename = 'translations.stbl'
        dialog.rb_selection = Checked(False)
        dialog.rb_validated = Checked(False)
        dialog.rb_validated_partial = Checked(True)
        dialog.rb_partial = Checked(False)
        dialog.rb_all = Checked(False)
        dialog.cb_replace = Checked(True)

        stats = ImportDialog.translate(dialog)

        self.assertEqual(stats, ImportStats(applied=1, unchanged=1, skipped_by_mode=1, missing=1))
        self.assertTrue(tableview.refreshed)

        tableview.refreshed = False
        table[changed.id] = changed.translate
        stats = ImportDialog.translate(dialog)

        self.assertEqual(stats.applied, 0)
        self.assertFalse(tableview.refreshed)


if __name__ == '__main__':
    unittest.main()
