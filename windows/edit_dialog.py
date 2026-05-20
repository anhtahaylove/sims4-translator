# -*- coding: utf-8 -*-

from dataclasses import dataclass

from PySide6.QtCore import Qt, QObject, Slot
from PySide6.QtWidgets import QDialog, QMenu, QMessageBox
from PySide6.QtGui import QGuiApplication, QIcon

from .ui.edit_dialog import Ui_EditDialog

import themes.balanced as theme

from singletons.config import config
from singletons.interface import interface
from singletons.signals import color_signals, storage_signals
from singletons.state import app_state
from singletons.translator import translator
from singletons.undo import undo
from utils.functions import text_to_table, text_to_stbl
from utils.task_runner import CancellationToken, TaskReporter, TaskRunner
from utils.constants import *
from widgets.token_highlight import TokenValidationResult, validate_translation_tokens
from widgets.delegate import STATUS_META


@dataclass(frozen=True)
class EditTranslationRequest:
    engine: str
    source: str
    context: str = ''
    glossary_id: str = ''


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
    response = translator.translate(
        request.engine,
        request.source,
        context=request.context,
        glossary_id=request.glossary_id
    )
    token.raise_if_cancelled()

    if response.status_code == 200:
        return EditTranslationResult(text=response.text)

    return EditTranslationResult(error=response.text)


class EditDialog(QDialog, Ui_EditDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.setWindowIcon(QIcon(':/logo.ico'))
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)

        self.item = None
        self.__runner = TaskRunner(max_threads=1, parent=self)
        self.__translate_handle = None
        self.__token_result = TokenValidationResult()
        self.__focus_sized = False

        self.tableview.clicked.connect(self.tableview_click)
        self.tableview.customContextMenuRequested.connect(self.generate_item_context_menu)

        self.btn_ok.clicked.connect(self.ok_click)
        self.btn_review.clicked.connect(self.needs_review_click)
        self.btn_cancel.clicked.connect(self.cancel_click)

        self.cb_api.currentTextChanged.connect(self.change_api)

        self.btn_translate.clicked.connect(self.translate_click)
        self.btn_suggestions.toggled.connect(self.toggle_suggestions)
        self.txt_translate.textChanged.connect(self.__refresh_token_state)

        self.txt_original.selected.connect(self.selection_change)
        self.txt_original_diff.selected.connect(self.selection_change)

        app_state.dictionaries_storage.signals.updated.connect(self.__dictionaries_updated)
        storage_signals.updated.connect(self.__dictionaries_updated)

        self.tableview.set_model()

        self.retranslate()

    def retranslate(self):
        self.setWindowTitle('Translation Studio')
        self.edit_title.setText('Translation Studio')
        self.edit_detail.setText('Review token safety, refine the draft, then approve it or mark it for review.')
        self.dictionary_title.setText('Dictionary suggestions')
        self.search_title.setText('Selected suggestion')
        self.btn_translate.setText(interface.text('EditWindow', 'Translate'))
        self.btn_ok.setText('Approve (Ctrl+Enter)')
        self.btn_review.setText('Needs Review')
        self.lbl_original.setText(interface.text('EditWindow', 'Original text'))
        self.lbl_original_diff.setText(interface.text('EditWindow', 'Different original'))
        self.lbl_translate.setText('Translation draft')
        self.lbl_translate_diff.setText(interface.text('EditWindow', 'Different translation'))
        self.btn_cancel.setText(interface.text('EditWindow', 'Cancel'))
        self.txt_comment.setPlaceholderText(interface.text('EditWindow', 'Comment...'))

    def showEvent(self, event):
        if not self.__focus_sized:
            self.__resize_for_focus_mode()
            self.__focus_sized = True
        self.txt_translate.setFocus()
        super().showEvent(event)

    def keyPressEvent(self, event):
        if event.key() in [Qt.Key.Key_Enter, Qt.Key.Key_Return]:
            modifiers = event.modifiers()
            if modifiers & Qt.KeyboardModifier.ControlModifier and modifiers & Qt.KeyboardModifier.ShiftModifier:
                self.needs_review_click()
                return
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                self.ok_click()
                return
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
            return
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
            self.txt_search.setPlainText(text_to_table(text))
            self.__sync_suggestions_visibility()

    def prepare(self, item):
        if self.__translate_handle:
            self.__translate_handle.cancel()
            self.__translate_handle = None
            self.btn_translate.setEnabled(True)

        self.item = item

        self.txt_search.setPlainText('')

        self.txt_original.setPlainText(text_to_table(item.source))
        self.txt_translate.setPlainText(text_to_table(item.translate))

        self.txt_comment.setText(item.comment)
        self.__refresh_record_meta()

        engine = config.value('api', 'engine')
        self.cb_api.clear()
        self.cb_api.addItems(translator.engines)
        engine_index = self.cb_api.findText(engine)
        self.cb_api.setCurrentIndex(engine_index if engine_index >= 0 else 0)

        if item.source_old:
            self.txt_original_diff.setPlainText(text_to_table(item.source_old))
            self.txt_original_diff.setVisible(True)
            self.lbl_original_diff.setVisible(True)
        else:
            self.txt_original_diff.setVisible(False)
            self.lbl_original_diff.setVisible(False)

        if item.translate_old:
            self.txt_translate_diff.setPlainText(text_to_table(item.translate_old))
            self.txt_translate_diff.setVisible(True)
            self.lbl_translate_diff.setVisible(True)
        else:
            self.txt_translate_diff.setVisible(False)
            self.lbl_translate_diff.setVisible(False)

        self.txt_resource.setText('Record: STBL - 0x{instance:016x}[0x{id:08x}]'.format(instance=item.resource.instance,
                                                                                        id=item.id))
        self.__refresh_token_state()
        self.__sync_suggestions_visibility()

    def __sync_suggestions_visibility(self):
        model = self.tableview.model()
        has_suggestions = bool(model and model.rowCount() > 0)
        self.btn_suggestions.setEnabled(has_suggestions)
        self.btn_suggestions.setText(f'Suggestions {model.rowCount()}' if has_suggestions else 'Suggestions 0')

        if not has_suggestions:
            self.btn_suggestions.setChecked(False)

        show_suggestions = has_suggestions and self.btn_suggestions.isChecked()
        self.suggestions_dock.setVisible(show_suggestions)
        self.suggestions_splitter.setVisible(show_suggestions)
        self.dictionary_panel.setVisible(show_suggestions)
        self.search_panel.setVisible(show_suggestions)
        self.edit_splitter.setSizes([620, 190] if show_suggestions else [1, 0])

    def toggle_suggestions(self, checked: bool):
        model = self.tableview.model()
        has_suggestions = bool(model and model.rowCount() > 0)
        show_suggestions = checked and has_suggestions
        self.suggestions_dock.setVisible(show_suggestions)
        self.suggestions_splitter.setVisible(show_suggestions)
        self.dictionary_panel.setVisible(show_suggestions)
        self.search_panel.setVisible(show_suggestions)
        if show_suggestions:
            self.edit_splitter.setSizes([620, 190])
        else:
            self.edit_splitter.setSizes([1, 0])

    def ok_click(self):
        self.__refresh_token_state()
        if not self.__confirm_token_warning('Approved'):
            return
        self.__save(FLAG_VALIDATED)

    def needs_review_click(self):
        self.__refresh_token_state()
        if not self.__confirm_token_warning('Needs Review'):
            return
        self.__save(FLAG_PROGRESS)

    def __save(self, flag):
        undo.wrap(self.item)
        undo.commit()

        self.item.translate = text_to_stbl(self.txt_translate.toPlainText())
        self.item.flag = flag
        self.item.comment = self.txt_comment.text()

        self.item.translate_old = None

        app_state.dictionaries_storage.update(self.item)

        color_signals.update.emit()

        self.close()

    def translate_click(self):
        self.lbl_status.setStyleSheet('')
        self.lbl_status.setText(interface.text('EditWindow', 'Loading...'))
        self.__set_translate_busy(True)

        if self.__translate_handle:
            self.__translate_handle.cancel()

        request = EditTranslationRequest(
            self.cb_api.currentText(),
            self.item.source,
            context=self.__deepl_context_for_item(),
            glossary_id=config.value('api', 'deepl_glossary_id') or ''
        )
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
            self.txt_translate.setPlainText(text_to_table(result.text))
            self.lbl_status.setText('')
            self.__refresh_token_state()

    @Slot(object)
    def __translation_error(self, error):
        self.__show_translation_error(error.message)

    def __translation_finished(self, _cancelled: bool, handle):
        if self.__translate_handle is handle:
            self.__set_translate_busy(False)
            self.__translate_handle = None

    def __show_translation_error(self, message: str):
        self.lbl_status.setStyleSheet(f'color: {theme.TEXT_ERROR};')
        self.lbl_status.setText(message)

    def cancel_click(self):
        if self.__translate_handle:
            self.__translate_handle.cancel()
        self.close()

    def __resize_for_focus_mode(self):
        screen = QGuiApplication.screenAt(self.mapToGlobal(self.rect().center())) or QGuiApplication.primaryScreen()
        if not screen:
            return

        available = screen.availableGeometry()
        width = min(max(int(available.width() * 0.86), 1120), available.width())
        height = min(max(int(available.height() * 0.86), 740), available.height())
        self.resize(width, height)
        self.move(
            available.x() + (available.width() - self.width()) // 2,
            available.y() + (available.height() - self.height()) // 2,
        )

    def __refresh_record_meta(self):
        if not self.item:
            self.record_status.setText('Status: -')
            self.record_status.setProperty('state', '')
            self.text_metrics.setText('')
            return

        label, _color = STATUS_META.get(self.item.flag, ('Unknown', None))
        self.record_status.setText(f'Status: {label}')
        self.record_status.setProperty('state', str(self.item.flag))
        self.record_status.style().unpolish(self.record_status)
        self.record_status.style().polish(self.record_status)

    def __refresh_token_state(self):
        source = text_to_stbl(self.txt_original.toPlainText())
        translation = text_to_stbl(self.txt_translate.toPlainText())
        self.__token_result = validate_translation_tokens(source, translation)

        state = 'ok' if self.__token_result.ok else 'warning'
        self.token_status.setText(self.__token_result.summary())
        self.token_status.setProperty('state', state)
        self.token_status.style().unpolish(self.token_status)
        self.token_status.style().polish(self.token_status)

        detail = self.__token_result.details()
        if self.__token_result.ok:
            detail += ' Suggested outcome: Approved.'
        else:
            detail += ' Suggested outcome: Needs Review until the token differences are intentional.'
        self.token_detail.setText(detail)
        self.text_metrics.setText(f'Original {len(source):,} chars | Draft {len(translation):,} chars')

    def __confirm_token_warning(self, outcome: str) -> bool:
        if self.__token_result.ok:
            return True

        details = self.__token_result.details()
        self.token_detail.setText(
            details
            + f' Continue as {outcome} only if these token differences are intentional.'
        )
        message_box = self.__build_token_warning_box(outcome, details)
        answer = message_box.exec()
        message_box.deleteLater()

        yes = QMessageBox.StandardButton.Yes
        return answer == yes or answer == yes.value

    def __build_token_warning_box(self, outcome: str, details: str) -> QMessageBox:
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Warning)
        message_box.setWindowTitle(f'{outcome} with token warnings')
        message_box.setText(details)
        message_box.setInformativeText('Token differences can break in-game placeholders or formatting.')
        message_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        message_box.setDefaultButton(QMessageBox.StandardButton.No)
        message_box.setEscapeButton(QMessageBox.StandardButton.No)

        continue_button = message_box.button(QMessageBox.StandardButton.Yes)
        continue_button.setText(self.__token_continue_label(outcome))
        back_button = message_box.button(QMessageBox.StandardButton.No)
        back_button.setText('Back to Edit')
        return message_box

    @staticmethod
    def __token_continue_label(outcome: str) -> str:
        if outcome == 'Needs Review':
            return 'Continue and Mark Needs Review'
        return 'Continue and Approve'

    def __set_translate_busy(self, busy: bool):
        self.btn_translate.setEnabled(not busy)
        self.cb_api.setEnabled(not busy)
        self.btn_translate.setText(interface.text('EditWindow', 'Loading...') if busy else interface.text('EditWindow', 'Translate'))

    def __deepl_context_for_item(self) -> str:
        if not self.item:
            return ''

        parts = []
        if self.item.package:
            parts.append(f'Package: {self.item.package}')
        parts.append(f'String ID: {self.item.id_hex}')
        if self.item.comment:
            parts.append(f'Translator comment: {self.item.comment}')
        return '\n'.join(parts)

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
            self.txt_translate.setPlainText(text_to_table(item[RECORD_DICTIONARY_TRANSLATE]))
