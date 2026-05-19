# -*- coding: utf-8 -*-

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from .ui.import_dialog import Ui_ImportDialog

from singletons.interface import interface
from singletons.signals import progress_signals, color_signals, window_signals
from singletons.state import app_state
from singletons.undo import undo
from utils.functions import compare, text_to_stbl
from utils.constants import *


@dataclass(frozen=True)
class ImportStats:
    applied: int = 0
    unchanged: int = 0
    skipped_by_mode: int = 0
    missing: int = 0

    @property
    def total(self) -> int:
        return self.applied + self.unchanged + self.skipped_by_mode + self.missing


class ImportDialog(QDialog, Ui_ImportDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.filename = None

        self.btn_import.clicked.connect(self.import_click)
        self.btn_cancel.clicked.connect(self.cancel_click)

        self.retranslate()

    def retranslate(self):
        self.setWindowTitle(interface.text('ImportDialog', 'Import translate'))
        self.header_title.setText(interface.text('ImportDialog', 'Import translate'))
        self.header_detail.setText(interface.text(
            'ImportDialog',
            'Apply matching translations while keeping validated work protected.'
        ))
        self.gb_overwrite.setTitle(interface.text('ImportDialog', 'Overwrite'))
        self.rb_all.setText(interface.text('ImportDialog', 'Everything'))
        self.rb_validated.setText(interface.text('ImportDialog', 'Everything but already validated strings'))
        self.rb_validated_partial.setText(interface.text('ImportDialog',
                                                         'Everything but already validated and partial strings'))
        self.rb_partial.setText(interface.text('ImportDialog', 'Partial strings'))
        self.rb_selection.setText(interface.text('ImportDialog', 'Selection only'))
        self.cb_replace.setText(interface.text('ImportDialog', 'Replace existing translation'))
        self.btn_import.setText(interface.text('ImportDialog', 'Import'))
        self.btn_cancel.setText(interface.text('ImportDialog', 'Cancel'))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.filename = None

    def translate(self) -> ImportStats:
        if not self.filename:
            return ImportStats()

        table = {}

        if self.filename.lower().endswith('.xml'):
            table = app_state.packages_storage.read_xml(self.filename)
        elif self.filename.lower().endswith('.stbl'):
            table = app_state.packages_storage.read_stbl(self.filename)
        elif self.filename.lower().endswith('.package'):
            table = app_state.packages_storage.read_package(self.filename)
        elif self.filename.lower().endswith('.json'):
            table = app_state.packages_storage.read_json(self.filename)
        elif self.filename.lower().endswith('.binary'):
            table = app_state.packages_storage.read_binary(self.filename)

        if self.rb_selection.isChecked():
            items = app_state.tableview.selected_items()
        else:
            items = app_state.packages_storage.items()

        if not table or not items:
            return ImportStats()

        if self.rb_validated.isChecked():
            flags = [FLAG_UNVALIDATED, FLAG_PROGRESS, FLAG_REPLACED]
        elif self.rb_validated_partial.isChecked():
            flags = [FLAG_UNVALIDATED]
        elif self.rb_partial.isChecked():
            flags = [FLAG_PROGRESS, FLAG_REPLACED]
        else:
            flags = []

        progress_signals.initiate.emit(interface.text('System', 'Importing translate...'), len(items) / 100)
        applied = 0
        unchanged = 0
        skipped_by_mode = 0
        missing = 0

        for i, item in enumerate(items):
            if i % 100 == 0:
                progress_signals.increment.emit()

            if not (self.rb_all.isChecked() or self.rb_selection.isChecked() or item.flag in flags):
                skipped_by_mode += 1
                continue

            sid = item.id
            if sid not in table:
                missing += 1
                continue

            source = item.source
            dest = item.translate
            translate = table[sid]
            if compare(dest, translate) or compare(source, translate):
                unchanged += 1
                continue

            undo.wrap(item)
            applied += 1
            if self.cb_replace.isChecked():
                if item.flag != FLAG_UNVALIDATED:
                    item.translate_old = item.translate
                item.translate = text_to_stbl(translate)
                item.flag = FLAG_VALIDATED
            else:
                if item.flag == FLAG_UNVALIDATED:
                    item.translate = text_to_stbl(translate)
                    item.flag = FLAG_VALIDATED
                else:
                    item.translate_old = text_to_stbl(translate)

        undo.commit()

        if applied and app_state.tableview:
            app_state.tableview.refresh()

        stats = ImportStats(
            applied=applied,
            unchanged=unchanged,
            skipped_by_mode=skipped_by_mode,
            missing=missing
        )
        window_signals.log.emit(interface.text(
            'System',
            'Imported {} translations, unchanged {}, skipped {}, missing {}'
        ).format(stats.applied, stats.unchanged, stats.skipped_by_mode, stats.missing))

        color_signals.update.emit()
        progress_signals.finished.emit()
        return stats

    def import_click(self):
        self.__set_busy(True)
        try:
            self.translate()
        finally:
            self.__set_busy(False)
            self.close()

    def cancel_click(self):
        self.close()

    def __set_busy(self, busy: bool) -> None:
        widgets = (
            self.gb_overwrite,
            self.rb_all,
            self.rb_validated,
            self.rb_validated_partial,
            self.rb_partial,
            self.rb_selection,
            self.cb_replace,
            self.btn_import,
        )
        for widget in widgets:
            widget.setEnabled(not busy)
        self.btn_import.setText(
            interface.text('System', 'Importing translate...')
            if busy else interface.text('ImportDialog', 'Import')
        )
