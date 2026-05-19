# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from packer.resource import ResourceID
from singletons.signals import window_signals
from singletons.state import app_state
from storages.records import MainRecord
from utils.constants import EXPORT_JSON_S4S, FLAG_TRANSLATED
from utils.task_runner import TaskRunner
from windows.export_dialog import ExportDialog


def app():
    return QCoreApplication.instance() or QCoreApplication([])


class Checked:

    def __init__(self, checked=False, visible=True):
        self._checked = checked
        self._visible = visible
        self.enabled = True

    def isChecked(self):
        return self._checked

    def isVisible(self):
        return self._visible

    def setEnabled(self, enabled):
        self.enabled = enabled

    def setChecked(self, checked):
        self._checked = checked

    def setVisible(self, visible):
        self._visible = visible


class Button:

    def __init__(self):
        self.enabled = True
        self.text = ''

    def setEnabled(self, enabled):
        self.enabled = enabled

    def setText(self, text):
        self.text = text

    def isEnabled(self):
        return self.enabled


class FakeStorage:

    def __init__(self, item):
        self.item = item
        self.current_package = None
        self.current_instance = 0
        self.packages = []

    def primary_items(self, key=None, instance=0):
        return [self.item]

    def items(self):
        return [self.item]


class ExportDialogAsyncTests(unittest.TestCase):

    def test_non_csv_export_starts_background_task_and_restores_busy_state(self):
        app()
        rid = ResourceID(group=0, instance=1, type=0x220557DA)
        item = MainRecord(
            1,
            42,
            rid.instance,
            rid.group,
            'Hello',
            'Bonjour',
            FLAG_TRANSLATED,
            rid,
            rid,
            'pkg.package',
            None,
            None,
            (1, 1, 4, 4),
            '',
        )

        storage = FakeStorage(item)
        app_state.set_packages_storage(storage)
        dialog = ExportDialog.__new__(ExportDialog)
        dialog._ExportDialog__export = EXPORT_JSON_S4S
        dialog._ExportDialog__runner = TaskRunner(max_threads=1)
        dialog._ExportDialog__export_handle = None
        dialog.rb_all = Checked(False)
        dialog.rb_translated = Checked(False)
        dialog.rb_selection = Checked(False)
        dialog.cb_current_instance = Checked(False, visible=False)
        dialog.cb_separate_instances = Checked(False, visible=False)
        dialog.cb_separate_packages = Checked(False, visible=False)
        dialog.btn_export = Button()
        dialog.btn_cancel = Button()
        closed = []
        dialog.close = lambda: closed.append(True)

        completed = []

        with patch('windows.export_dialog.save_json', return_value='out.json'), \
                patch('windows.export_dialog.export_structured_task', return_value=object()) as task:
            handle = dialog.export()
            handle.finished.connect(lambda _cancelled: completed.append(True))
            loop = QEventLoop()
            handle.finished.connect(lambda _cancelled: loop.quit())
            QTimer.singleShot(1000, loop.quit)
            loop.exec()

        self.assertTrue(completed)
        self.assertTrue(task.called)
        self.assertIsNone(dialog._ExportDialog__export_handle)
        self.assertTrue(dialog.btn_export.isEnabled())
        self.assertEqual(closed, [True])

    def test_non_csv_export_error_restores_state_without_closing_dialog(self):
        app()
        rid = ResourceID(group=0, instance=1, type=0x220557DA)
        item = MainRecord(
            1,
            42,
            rid.instance,
            rid.group,
            'Hello',
            'Bonjour',
            FLAG_TRANSLATED,
            rid,
            rid,
            'pkg.package',
            None,
            None,
            (1, 1, 4, 4),
            '',
        )

        app_state.set_packages_storage(FakeStorage(item))
        dialog = ExportDialog.__new__(ExportDialog)
        dialog._ExportDialog__export = EXPORT_JSON_S4S
        dialog._ExportDialog__runner = TaskRunner(max_threads=1)
        dialog._ExportDialog__export_handle = None
        dialog._ExportDialog__export_failed = False
        dialog.rb_all = Checked(False)
        dialog.rb_translated = Checked(False)
        dialog.rb_selection = Checked(False)
        dialog.cb_current_instance = Checked(False, visible=False)
        dialog.cb_separate_instances = Checked(False, visible=False)
        dialog.cb_separate_packages = Checked(False, visible=False)
        dialog.btn_export = Button()
        dialog.btn_cancel = Button()
        closed = []
        messages = []
        dialog.close = lambda: closed.append(True)
        window_signals.log.connect(messages.append)

        try:
            with patch('windows.export_dialog.save_json', return_value='out.json'), \
                    patch('windows.export_dialog.export_structured_task', side_effect=RuntimeError('disk full')):
                handle = dialog.export()
                loop = QEventLoop()
                handle.finished.connect(lambda _cancelled: loop.quit())
                QTimer.singleShot(1000, loop.quit)
                loop.exec()
        finally:
            window_signals.log.disconnect(messages.append)

        self.assertEqual(closed, [])
        self.assertIsNone(dialog._ExportDialog__export_handle)
        self.assertTrue(dialog.btn_export.isEnabled())
        self.assertTrue(dialog.btn_cancel.isEnabled())
        self.assertTrue(any('disk full' in message for message in messages))


if __name__ == '__main__':
    unittest.main()
