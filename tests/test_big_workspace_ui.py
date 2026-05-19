# -*- coding: utf-8 -*-

import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from packer.resource import ResourceID
from singletons.config import config
from singletons.state import app_state
from storages.dictionaries import DictionariesStorage
from storages.packages import PackagesStorage
from storages.records import MainRecord
from utils.constants import FLAG_PROGRESS, FLAG_UNVALIDATED, FLAG_VALIDATED
from windows.main_window import MainWindow


def app():
    return QApplication.instance() or QApplication([])


def close_widget(widget):
    widget.close()
    widget.deleteLater()
    app().processEvents()


def record(flag=FLAG_PROGRESS):
    rid = ResourceID(group=0, instance=0x1234, type=0x220557DA)
    return MainRecord(
        1,
        42,
        rid.instance,
        rid.group,
        'Hello source',
        'Bonjour draft',
        flag,
        rid,
        rid,
        'sample.package',
        None,
        None,
        (1, 1, 1, 1),
        'Needs review',
    )


class WorkspaceProShellTests(unittest.TestCase):

    def setUp(self):
        app()
        config.set_value('translation', 'source', 'ENG_US')
        config.set_value('translation', 'destination', 'FRE_FR')
        app_state.set_packages_storage(PackagesStorage())
        app_state.set_dictionaries_storage(DictionariesStorage())

    def test_main_window_creates_workspace_pro_shell_without_losing_legacy_actions(self):
        window = MainWindow()
        try:
            self.assertEqual(window.project_sidebar.objectName(), 'projectSidebar')
            self.assertEqual(window.inspector_panel.objectName(), 'inspectorPanel')
            self.assertEqual(window.workspace_splitter.objectName(), 'workspaceSplitter')
            self.assertIs(window.activity_drawer, window.job_drawer)
            self.assertIs(window.command_open.defaultAction(), window.action_load_file)
            self.assertIs(window.command_translate.defaultAction(), window.action_translate)
            self.assertFalse(window.inspector_apply.isEnabled())
        finally:
            close_widget(window)

    def test_inspector_populates_from_record_without_mutating_it(self):
        window = MainWindow()
        item = record()
        before = list(item)
        try:
            window.update_inspector_item(item)

            self.assertEqual(list(item), before)
            self.assertIn('0x0000002A', window.inspector_meta.text())
            self.assertEqual(window.inspector_original.toPlainText(), 'Hello source')
            self.assertEqual(window.inspector_translation.toPlainText(), 'Bonjour draft')
            self.assertEqual(window.inspector_comment.text(), 'Needs review')
            self.assertTrue(window.inspector_apply.isEnabled())
        finally:
            close_widget(window)

    def test_inspector_reset_and_apply_use_existing_record_state(self):
        window = MainWindow()
        item = record()
        try:
            window.update_inspector_item(item)
            window.inspector_translation.setPlainText('Salut')
            window.inspector_comment.setText('Reviewed')
            window.apply_inspector_translation()

            self.assertEqual(item.translate, 'Salut')
            self.assertEqual(item.comment, 'Reviewed')
            self.assertEqual(item.flag, FLAG_VALIDATED)

            window.update_inspector_item(item)
            window.reset_inspector_translation()

            self.assertEqual(item.translate, item.source)
            self.assertEqual(item.flag, FLAG_UNVALIDATED)
        finally:
            close_widget(window)


if __name__ == '__main__':
    unittest.main()
