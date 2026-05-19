# -*- coding: utf-8 -*-

from dataclasses import dataclass

from PySide6.QtCore import Qt, QObject, Slot
from PySide6.QtWidgets import QDialog, QMenu
from PySide6.QtGui import QIcon

from .ui.edit_dialog import Ui_EditDialog

import themes.light as light
import themes.dark as dark

from singletons.config import config
from singletons.interface import interface
from singletons.signals import color_signals, storage_signals
from singletons.state import app_state
from singletons.translator import translator
from singletons.undo import undo
from utils.functions import text_to_edit, text_to_stbl
from utils.task_runner import CancellationToken, TaskReporter, TaskRunner
from utils.constants import *


@dataclass(frozen=True)
class EditTranslationRequest:
    engine: str
    source: str


@dataclass(frozen=True)
class EditTranslationResult:
    text: str = ''
    error: str = ''


def edit_translation_task(
        token: CancellationToken,
        _reporter: TaskReporter,
        request: EditTranslationRequest
) -> EditTranslationResult:
    token.raise_if_cancelled()
    response = translator.translate(request.engine, request.source)
    token.raise_if_cancelled()

    if response.status_code == 200:
        return EditTranslationResult(text=response.text)

    return EditTranslationResult(error=response.text)


class EditDialog(QDialog, Ui_EditDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)

        self.item = None
        self.__runner = TaskRunner(max_threads=1, parent=self)
        self.__translate_handle = None

        self.tableview.clicked.connect(self.tableview_click)
        self.tableview.customContextMenuRequested.connect(self.generate_item_context_menu)

        self.btn_ok.clicked.connect(self.ok_click)
        self.btn_cancel.clicked.connect(self.cancel_click)

        self.cb_api.currentTextChanged.connect(self.change_api)

        self.btn_translate.clicked.connect(self.translate_click)

        self.txt_original.selected.connect(self.selection_change)
        self.txt_original_diff.selected.connect(self.selection_change)

        app_state.dictionaries_storage.signals.updated.connect(self.__dictionaries_updated)
        storage_signals.updated.connect(self.__dictionaries_updated)

        self.tableview.set_model()

        self.retranslate()

    def retranslate(self):
        self.setWindowTitle(interface.text('EditWindow', 'Search and Edit'))
        self.edit_title.setText(interface.text('EditWindow', 'Search and Edit'))
        self.edit_detail.setText('Review suggestions, refine the draft, then validate the selected string.')
        self.dictionary_title.setText('Dictionary suggestions')
        self.search_title.setText('Selected suggestion')
        self.btn_translate.setText(interface.text('EditWindow', 'Translate'))
        self.btn_ok.setText(interface.text('EditWindow', 'OK (Ctrl+Enter)'))
        self.lbl_original.setText(interface.text('EditWindow', 'Original text'))
        self.lbl_original_diff.setText(interface.text('EditWindow', 'Different original'))
        self.lbl_translate.setText(interface.text('EditWindow', 'Current translation'))
        self.lbl_translate_diff.setText(interface.text('EditWindow', 'Different translation'))
        self.btn_cancel.setText(interface.text('EditWindow', 'Cancel'))
        self.txt_comment.setPlaceholderText(interface.text('EditWindow', 'Comment...'))

    def showEvent(self, event):
        self.txt_translate.setFocus()

    def keyPressEvent(self, event):
        if event.key() in [Qt.Key.Key_Enter, Qt.Key.Key_Return]:
            if event.modifiers() and Qt.KeyboardModifier.ControlModifier:
                self.ok_click()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    @Slot()
    def __dictionaries_updated(self):
        app_state.dictionaries_storage.proxy.process_filter()
        self.__sync_suggestions_visibility()

    def change_api(self):
        config.set_value('api', 'engine', self.cb_api.currentText())

    @Slot(QObject)
    def selection_change(self, sender):
        text = sender.textCursor().selectedText()
        if len(text) >= 3:
            app_state.dictionaries_storage.proxy.filter(text=text)
            self.__sync_suggestions_visibility()

    def tableview_click(self, index):
        model = self.tableview.model()
        item = model.sourceModel().filtered[model.mapToSource(index).row()]
        if item:
            if index.column() == COLUMN_DICTIONARIES_TRANSLATE:
                text = item[RECORD_DICTIONARY_TRANSLATE]
            else:
                text = item[RECORD_DICTIONARY_SOURCE]
            self.txt_search.setPlainText(text_to_edit(text))
            self.__sync_suggestions_visibility()

    def prepare(self, item):
        if self.__translate_handle:
            self.__translate_handle.cancel()
            self.__translate_handle = None
            self.btn_translate.setEnabled(True)

        self.item = item

        self.txt_search.setPlainText('')

        self.txt_original.setPlainText(text_to_edit(item.source))
        self.txt_translate.setPlainText(text_to_edit(item.translate))

        self.txt_comment.setText(item.comment)

        engine = config.value('api', 'engine')
        self.cb_api.clear()
        self.cb_api.addItems(translator.engines)
        engine_index = self.cb_api.findText(engine)
        self.cb_api.setCurrentIndex(engine_index if engine_index >= 0 else 0)

        if item.source_old:
            self.txt_original_diff.setPlainText(text_to_edit(item.source_old))
            self.txt_original_diff.setVisible(True)
            self.lbl_original_diff.setVisible(True)
        else:
            self.txt_original_diff.setVisible(False)
            self.lbl_original_diff.setVisible(False)

        if item.translate_old:
            self.txt_translate_diff.setPlainText(text_to_edit(item.translate_old))
            self.txt_translate_diff.setVisible(True)
            self.lbl_translate_diff.setVisible(True)
        else:
            self.txt_translate_diff.setVisible(False)
            self.lbl_translate_diff.setVisible(False)

        self.txt_resource.setText('Record: STBL - 0x{instance:016x}[0x{id:08x}]'.format(instance=item.resource.instance,
                                                                                        id=item.id))
        self.__sync_suggestions_visibility()

    def __sync_suggestions_visibility(self):
        model = self.tableview.model()
        has_suggestions = bool(model and model.rowCount() > 0)
        self.suggestions_splitter.setVisible(has_suggestions)
        self.dictionary_panel.setVisible(has_suggestions)
        self.search_panel.setVisible(has_suggestions)
        if has_suggestions:
            self.edit_splitter.setSizes([180, 420])
        else:
            self.edit_splitter.setSizes([0, 1])

    def ok_click(self):
        undo.wrap(self.item)
        undo.commit()

        self.item.translate = text_to_stbl(self.txt_translate.toPlainText())
        self.item.flag = FLAG_VALIDATED
        self.item.comment = self.txt_comment.text()

        self.item.translate_old = None

        app_state.dictionaries_storage.update(self.item)

        color_signals.update.emit()

        self.close()

    def translate_click(self):
        self.lbl_status.setStyleSheet('')
        self.lbl_status.setText(interface.text('EditWindow', 'Loading...'))
        self.btn_translate.setEnabled(False)

        if self.__translate_handle:
            self.__translate_handle.cancel()

        request = EditTranslationRequest(self.cb_api.currentText(), self.item.source)
        self.__translate_handle = self.__runner.start(
            edit_translation_task,
            request,
            job_name=interface.text('EditWindow', 'Translate')
        )
        self.__translate_handle.result.connect(self.__translated)
        self.__translate_handle.error.connect(self.__translation_error)
        self.__translate_handle.finished.connect(
            lambda cancelled, handle=self.__translate_handle: self.__translation_finished(cancelled, handle)
        )

    @Slot(object)
    def __translated(self, result: EditTranslationResult):
        if result.error:
            self.__show_translation_error(result.error)
        else:
            self.txt_translate.setPlainText(text_to_edit(result.text))
            self.lbl_status.setText('')

    @Slot(object)
    def __translation_error(self, error):
        self.__show_translation_error(error.message)

    def __translation_finished(self, _cancelled: bool, handle):
        if self.__translate_handle is handle:
            self.btn_translate.setEnabled(True)
            self.__translate_handle = None

    def __show_translation_error(self, message: str):
        color = dark.TEXT_ERROR if config.is_dark_theme() else light.TEXT_ERROR
        self.lbl_status.setStyleSheet(f'color: {color};')
        self.lbl_status.setText(message)

    def cancel_click(self):
        if self.__translate_handle:
            self.__translate_handle.cancel()
        self.close()

    def generate_item_context_menu(self, position):
        index = self.sender().indexAt(position)
        if not index.isValid():
            return

        position.setY(position.y() + 22)

        context_menu = QMenu()

        use_action = context_menu.addAction(QIcon(':/images/validate_2.png'),
                                            interface.text('EditWindow', 'Use this translation'))

        action = context_menu.exec_(self.sender().mapToGlobal(position))
        if action is None:
            return

        if action == use_action:
            item = self.tableview.selected_item()
            self.txt_translate.setPlainText(text_to_edit(item[RECORD_DICTIONARY_TRANSLATE]))
