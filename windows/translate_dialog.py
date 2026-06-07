# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import List, Tuple

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QMessageBox

from windows.ui.translate_dialog import Ui_TranslateDialog

from storages.records import MainRecord

import themes.balanced as theme

from singletons.config import config
from singletons.interface import interface
from singletons.signals import progress_signals
from singletons.state import app_state
from singletons.translation_cache import translation_cache
from singletons.translation_memory import STATUS_APPROVED, translation_memory
from singletons.translator import deepl_usage, estimate_ai_characters, estimate_deepl_characters, translator
from singletons.undo import undo
from utils.task_runner import CancellationToken, TaskReporter, TaskRunner
from utils.provider_engines import refresh_engine_combo
from utils.translation_variants import translation_variant
from utils.functions import text_to_stbl, text_to_edit
from utils.constants import *


def split_by_char_limit(items: List[MainRecord], char_limit: int = 256) -> list:
    result = []
    current_chunk = []
    current_length = 0

    for item in items:
        record = item[1] if isinstance(item, tuple) else item
        text_length = len(record.source)
        if current_length + text_length > char_limit:
            result.append(current_chunk)
            current_chunk = [item]
            current_length = text_length
        else:
            current_chunk.append(item)
            current_length += text_length

    if current_chunk:
        result.append(current_chunk)

    return result


@dataclass(frozen=True)
class TranslationItemSnapshot:
    index: int
    source: str
    package: str = ''
    comment: str = ''
    record_id: int = 0
    instance: int = 0


@dataclass(frozen=True)
class TranslationChunkRequest:
    engine: str
    items: Tuple[TranslationItemSnapshot, ...]
    fast: bool = False
    context: str = ''
    glossary_id: str = ''


@dataclass(frozen=True)
class TranslationItemResult:
    index: int
    text: str


@dataclass(frozen=True)
class TranslationChunkResult:
    translations: Tuple[TranslationItemResult, ...] = ()
    warning: str = ''
    error: str = ''


def translate_chunk_task(
        token: CancellationToken,
        _reporter: TaskReporter,
        request: TranslationChunkRequest
) -> TranslationChunkResult:
    token.raise_if_cancelled()

    if request.fast:
        text_strings = []

        for item in request.items:
            token.raise_if_cancelled()
            text_string = text_to_edit(item.source)
            text_string = text_string.replace("\n", r"\x0a")
            text_string = text_string.replace("\r", r"\x0d")
            text_strings.append(text_string)

        combined_text = '\n'.join(text_strings)

    else:
        combined_text = text_to_edit(request.items[0].source)

    response = translator.translate(
        request.engine,
        combined_text,
        context=request.context,
        glossary_id=request.glossary_id,
        preserve_newlines=request.fast,
    )
    token.raise_if_cancelled()

    if response.status_code != 200:
        return TranslationChunkResult(error=response.text)

    translated_text = response.text

    if request.fast:
        translated_texts = translated_text.split('\n')
        if len(translated_texts) != len(request.items):
            return TranslationChunkResult(
                warning=interface.text('TranslateDialog', 'Some lines could not be translated.')
            )

        line_break = bytes(r"\x0a", 'utf-8').decode('unicode-escape')
        carriage_return = bytes(r"\x0d", 'utf-8').decode('unicode-escape')
        translations = []

        for item, text in zip(request.items, translated_texts):
            token.raise_if_cancelled()
            text = text.replace("\\x0a", line_break)
            text = text.replace("\\x0d", carriage_return)
            translations.append(TranslationItemResult(item.index, text_to_stbl(text)))

        return TranslationChunkResult(translations=tuple(translations))

    return TranslationChunkResult(
        translations=(TranslationItemResult(request.items[0].index, text_to_stbl(translated_text)),)
    )


class TranslateDialog(QDialog, Ui_TranslateDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(':/logo.ico'))

        self.cb_api.currentTextChanged.connect(self.change_api)

        self.btn_translate.clicked.connect(self.translate_click)
        self.btn_cancel.clicked.connect(self.cancel_click)
        self.btn_retry_failed.clicked.connect(self.retry_failed_click)

        self.__runner = TaskRunner(max_threads=3, parent=self)

        self.__progress = 0
        self.__translating = False
        self.__error = False
        self.__log = []
        self.__items = []
        self.__handles = []
        self.__chunk_items_by_handle = {}
        self.__failed_item_indexes = set()
        self.__last_failed_items = []
        self.__stopping_for_error = False
        self.__refresh_timer = QTimer(self)
        self.__refresh_timer.setSingleShot(True)
        self.__refresh_timer.timeout.connect(self.__refresh_table)

        self.check_api()

        self.retranslate()

    def retranslate(self):
        self.setWindowTitle(interface.text('TranslateDialog', 'Batch translate'))
        self.header_title.setText(interface.text('TranslateDialog', 'Batch translate'))
        self.header_detail.setText(interface.text(
            'TranslateDialog',
            'Translate the chosen records in the background and keep the workspace responsive.'
        ))
        self.__set_radio_text(self.rb_all, interface.text('ImportDialog', 'Everything'))
        self.__set_radio_text(
            self.rb_validated,
            interface.text('ImportDialog', 'Everything but already validated strings')
        )
        self.__set_radio_text(
            self.rb_validated_partial,
            interface.text('ImportDialog', 'Everything but already validated and partial strings')
        )
        self.__set_radio_text(self.rb_partial, interface.text('ImportDialog', 'Partial strings'))
        self.__set_radio_text(self.rb_selection, interface.text('ImportDialog', 'Selection only'))
        self.btn_cancel.setText(interface.text('TranslateDialog', 'Cancel'))
        self.btn_retry_failed.setText(interface.text('TranslateDialog', 'Retry failed only'))
        self.btn_translate.setText(interface.text('TranslateDialog', 'Translate'))
        self.rb_slow.setText(interface.text('TranslateDialog', 'Line-by-line translation'))
        self.rb_fast.setText(interface.text('TranslateDialog', 'Multiline translation'))
        self.lbl_slow.setText(interface.text('TranslateDialog', 'Slow but more accurate translation.'))
        self.lbl_fast.setText(interface.text('TranslateDialog', 'A faster, but perhaps less accurate translation.'))
        self.log_box.setTitle(interface.text('TranslateDialog', 'Log'))

    @staticmethod
    def __set_radio_text(button, text: str):
        button.setToolTip(text)
        if len(text) <= 58:
            button.setText(text)
            button.setMinimumHeight(button.sizeHint().height())
            return
        midpoint = len(text) // 2
        split = text.rfind(' ', 0, midpoint + 10)
        if split <= 0:
            split = text.find(' ', max(0, midpoint - 10))
        button.setText(f'{text[:split]}\n{text[split + 1:]}' if split > 0 else text)
        button.setMinimumHeight(button.sizeHint().height())

    def showEvent(self, event):
        self.refresh_api_list()

    def refresh_api_list(self):
        refresh_engine_combo(self.cb_api)
        self.check_api()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def change_api(self):
        config.set_value('api', 'engine', self.cb_api.currentText())
        self.check_api()

    def check_api(self):
        api = self.cb_api.currentText().lower()
        if api in ('deepl', 'gemini', 'openai-compatible', 'ollama'):
            self.rb_fast.setEnabled(True)
        else:
            self.rb_fast.setEnabled(False)
            self.rb_slow.setChecked(True)

    def translate(self):
        if self.rb_selection.isChecked():
            items = app_state.tableview.selected_items()
        else:
            items = app_state.packages_storage.items()
            if self.rb_validated.isChecked():
                items = [i for i in items if i.flag in (FLAG_UNVALIDATED, FLAG_PROGRESS, FLAG_REPLACED)]
            elif self.rb_validated_partial.isChecked():
                items = [i for i in items if i.flag == FLAG_UNVALIDATED]
            elif self.rb_partial.isChecked():
                items = [i for i in items if i.flag in (FLAG_PROGRESS, FLAG_REPLACED)]

        self.__start_translation(items)

    def __start_translation(self, items: List[MainRecord], retry_failed_only: bool = False) -> None:
        if not items:
            return

        self.__items = items

        indexed_items = list(enumerate(items))
        engine = self.cb_api.currentText()
        cached_results, indexed_items = self.__cached_results(engine, indexed_items)

        if engine.lower() == 'deepl' and indexed_items and not self.__confirm_deepl_cost(
                [item for _index, item in indexed_items]
        ):
            return
        if engine.lower() in ('gemini', 'openai-compatible', 'ollama') and indexed_items and not self.__confirm_ai_cost(
                engine,
                [item for _index, item in indexed_items]
        ):
            return

        force_slow = retry_failed_only
        if self.rb_fast.isChecked() and not force_slow:
            chunk_items = split_by_char_limit(indexed_items, 1024)
        else:
            chunk_items = [[item] for item in indexed_items]

        self.__progress = len(chunk_items)
        self.__translating = True
        self.__error = False
        self.__log = []
        self.__handles = []
        self.__chunk_items_by_handle = {}
        self.__failed_item_indexes = set()
        self.__last_failed_items = []
        self.__stopping_for_error = False
        self.__set_busy(True)

        self.edt_log.clear()

        if retry_failed_only:
            self.__log.append(interface.text(
                'TranslateDialog',
                'Retrying {count:,} failed/skipped record(s) line by line.'
            ).format(count=len(items)))
            self.print_log()

        if translation_cache.enabled:
            self.__log.append(interface.text(
                'TranslateDialog',
                'Translation cache: {hits:,} reused, {misses:,} to translate.'
            ).format(hits=len(cached_results), misses=len(indexed_items)))
            self.print_log()

        progress_signals.initiate.emit(interface.text('System', 'Translating...'), self.__progress)

        if cached_results:
            self.__translated_chunk(TranslationChunkResult(translations=tuple(cached_results)))

        if not chunk_items:
            self.__finish_translation()
            return

        for chunk in chunk_items:
            if not self.__error:
                snapshots = tuple(TranslationItemSnapshot(index=index, source=item.source) for index, item in chunk)
                request = TranslationChunkRequest(
                    engine=engine,
                    items=snapshots,
                    fast=self.rb_fast.isChecked() and not force_slow,
                    context=self.__deepl_context_for_items([item for _index, item in chunk]),
                    glossary_id=config.value('api', 'deepl_glossary_id') or ''
                )
                handle = self.__runner.start(
                    translate_chunk_task,
                    request,
                    job_name=interface.text('System', 'Translating...')
                )
                self.__handles.append(handle)
                self.__chunk_items_by_handle[handle] = tuple(chunk)
                handle.result.connect(lambda result, task_handle=handle: self.__translated_chunk(result, task_handle))
                handle.error.connect(lambda error, task_handle=handle: self.__task_error(error, task_handle))
                handle.finished.connect(
                    lambda cancelled, task_handle=handle: self.__finished_translate_chunk(cancelled, task_handle)
                )

    def stop_translate(self):
        for handle in self.__handles:
            handle.cancel()
        self.__set_busy(True, stopping=True)
        progress_signals.initiate.emit(interface.text('System',
                                                      'Stopping translate, waiting for the finish of the threads...'),
                                       self.__progress)

    @Slot(object)
    def __translated_chunk(self, result: TranslationChunkResult, handle=None):
        if handle is not None and (handle.cancelled or handle not in self.__handles):
            return

        if result.error:
            self.__mark_handle_failed(handle)
            self.__error_translate_chunk(result.error)
            return

        if result.warning:
            self.__warning_translate_chunk(result.warning)
            if handle is not None:
                translated_indexes = {translated.index for translated in result.translations}
                self.__mark_handle_failed(handle, exclude_indexes=translated_indexes)

        for translated in result.translations:
            if translated.index >= len(self.__items):
                continue

            failed_indexes = getattr(self, '_TranslateDialog__failed_item_indexes', None)
            if failed_indexes is not None:
                failed_indexes.discard(translated.index)
            item = self.__items[translated.index]
            undo.wrap(item)
            item.translate = translated.text
            item.flag = FLAG_VALIDATED
            self.__store_cached_translation(item, translated.text)

        if result.translations:
            self.__refresh_timer.start(50)

    @Slot(object)
    def __task_error(self, error, handle=None):
        if handle is not None and (handle.cancelled or handle not in self.__handles):
            return
        self.__mark_handle_failed(handle)
        self.__error_translate_chunk(error.message)

    @Slot(bool)
    def __finished_translate_chunk(self, _cancelled: bool, handle=None):
        if handle is not None:
            if handle not in self.__handles:
                return
            self.__handles.remove(handle)
            self.__chunk_items_by_handle.pop(handle, None)

        self.__progress -= 1
        if self.__progress == 0:
            self.__finish_translation()

        progress_signals.increment.emit()

    def __finish_translation(self) -> None:
        if self.__refresh_timer.isActive():
            self.__refresh_timer.stop()
        self.__refresh_table()
        undo.commit()
        if self.__stopping_for_error:
            for chunk in self.__chunk_items_by_handle.values():
                for index, _item in chunk:
                    self.__failed_item_indexes.add(index)
        self.__last_failed_items = [
            self.__items[index]
            for index in sorted(self.__failed_item_indexes)
            if 0 <= index < len(self.__items)
        ]
        if self.__last_failed_items:
            self.__log.append(interface.text(
                'TranslateDialog',
                'Retry available for {count:,} failed/skipped record(s).'
            ).format(count=len(self.__last_failed_items)))
            self.print_log()
        self.__progress = 0
        self.__translating = False
        self.__handles = []
        self.__chunk_items_by_handle = {}
        self.__failed_item_indexes = set()
        self.__stopping_for_error = False
        self.__set_busy(False)
        progress_signals.finished.emit()

    @staticmethod
    def __refresh_table():
        if app_state.tableview:
            app_state.tableview.refresh()

    @Slot(str)
    def __error_translate_chunk(self, text: str):
        if not self.__error:
            self.__error = True
            self.__stopping_for_error = True
            self.__log.append(f'<span style="color: {theme.TEXT_ERROR};">{text}</span>')
            self.print_log()
            self.stop_translate()

    @Slot(str)
    def __warning_translate_chunk(self, text: str):
        self.__log.append(text)
        self.print_log()

    def print_log(self):
        self.edt_log.setText('<br>'.join(self.__log))
        self.edt_log.verticalScrollBar().setValue(self.edt_log.verticalScrollBar().maximum())

    def translate_click(self):
        if not self.__translating:
            self.translate()
        else:
            self.stop_translate()

    def retry_failed_click(self):
        if self.__translating or not self.__last_failed_items:
            return
        self.__start_translation(list(self.__last_failed_items), retry_failed_only=True)

    def cancel_click(self):
        if self.__translating:
            self.stop_translate()
        else:
            self.close()

    def translate_selection(self):
        if not app_state.tableview.selected_items():
            return

        self.refresh_api_list()
        self.rb_selection.setChecked(True)
        self.show()
        self.translate()

    def __confirm_deepl_cost(self, items: List[MainRecord]) -> bool:
        character_count = estimate_deepl_characters(items)
        usage = deepl_usage()
        if usage.status_code == 200 and usage.character_limit:
            after_count = usage.character_count + character_count
            percent = after_count / usage.character_limit * 100
            usage_text = interface.text(
                'TranslateDialog',
                'Current usage: {used:,} / {limit:,} characters.\n'
                'After this batch: about {after:,} characters ({percent:.1f}%).',
            ).format(
                used=usage.character_count,
                limit=usage.character_limit,
                after=after_count,
                percent=percent,
            )
        elif usage.status_code == 200:
            usage_text = interface.text(
                'TranslateDialog',
                'Current usage: {used:,} characters.',
            ).format(used=usage.character_count)
        else:
            usage_text = interface.text(
                'TranslateDialog',
                'Usage unavailable: {message}',
            ).format(message=usage.message)

        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Information)
        message_box.setWindowTitle(interface.text('TranslateDialog', 'DeepL batch translation'))
        message_box.setText(interface.text(
            'TranslateDialog',
            'DeepL will translate {records:,} records, about {characters:,} source characters.',
        ).format(records=len(items), characters=character_count))
        message_box.setInformativeText(usage_text)
        message_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        message_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        message_box.setEscapeButton(QMessageBox.StandardButton.Cancel)
        continue_button = message_box.button(QMessageBox.StandardButton.Yes)
        continue_button.setText(interface.text('TranslateDialog', 'Continue with DeepL'))
        cancel_button = message_box.button(QMessageBox.StandardButton.Cancel)
        cancel_button.setText(interface.text('TranslateDialog', 'Cancel'))

        answer = message_box.exec()
        message_box.deleteLater()
        yes = QMessageBox.StandardButton.Yes
        return answer == yes or answer == yes.value

    def __confirm_ai_cost(self, engine: str, items: List[MainRecord]) -> bool:
        character_count = estimate_ai_characters(items)

        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Information)
        message_box.setWindowTitle(interface.text('TranslateDialog', 'AI batch translation'))
        message_box.setText(interface.text(
            'TranslateDialog',
            '{engine} will translate {records:,} records, about {characters:,} source characters.',
        ).format(engine=engine, records=len(items), characters=character_count))
        message_box.setInformativeText(interface.text(
            'TranslateDialog',
            'Review provider pricing and quota before continuing.'
        ))
        message_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        message_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        message_box.setEscapeButton(QMessageBox.StandardButton.Cancel)
        continue_button = message_box.button(QMessageBox.StandardButton.Yes)
        continue_button.setText(interface.text('TranslateDialog', 'Continue with AI provider'))
        cancel_button = message_box.button(QMessageBox.StandardButton.Cancel)
        cancel_button.setText(interface.text('TranslateDialog', 'Cancel'))

        answer = message_box.exec()
        message_box.deleteLater()
        yes = QMessageBox.StandardButton.Yes
        return answer == yes or answer == yes.value

    def __cached_results(self, engine: str, indexed_items: list) -> tuple[list[TranslationItemResult], list]:
        if not translation_cache.enabled:
            return [], indexed_items

        source_locale = config.value('translation', 'source')
        destination_locale = config.value('translation', 'destination')
        variant = self.__cache_variant(engine)
        cached = []
        missing = []

        for index, item in indexed_items:
            text = translation_cache.lookup(source_locale, destination_locale, engine, variant, item.source)
            if text is None and translation_memory.enabled:
                text = translation_memory.lookup_exact(
                    source_locale,
                    destination_locale,
                    engine,
                    variant,
                    item.source,
                )
            if text is None:
                missing.append((index, item))
            else:
                cached.append(TranslationItemResult(index, text))

        return cached, missing

    def __store_cached_translation(self, item: MainRecord, translated_text: str) -> None:
        if not translation_cache.enabled:
            return

        engine = self.cb_api.currentText()
        translation_cache.store(
            config.value('translation', 'source'),
            config.value('translation', 'destination'),
            engine,
            self.__cache_variant(engine),
            item.source,
            translated_text,
        )
        if translation_memory.enabled:
            translation_memory.store(
                config.value('translation', 'source'),
                config.value('translation', 'destination'),
                engine,
                self.__cache_variant(engine),
                item.source,
                translated_text,
                status=STATUS_APPROVED,
                package=item.package,
                record_id=item.id,
                instance=item.resource.instance,
            )

    @staticmethod
    def __cache_variant(engine: str) -> str:
        return translation_variant(engine)

    @staticmethod
    def __deepl_context_for_items(items: List[MainRecord]) -> str:
        packages = []
        comments = []
        ids = []

        for item in items[:8]:
            if item.package and item.package not in packages:
                packages.append(item.package)
            if item.comment and item.comment not in comments:
                comments.append(item.comment)
            ids.append(item.id_hex)

        parts = []
        if packages:
            parts.append('Package: ' + ', '.join(packages[:3]))
        if ids:
            parts.append('String IDs: ' + ', '.join(ids[:8]))
        if comments:
            parts.append('Translator comments: ' + ' | '.join(comments[:3]))

        return '\n'.join(parts)

    def __set_busy(self, busy: bool, stopping: bool = False) -> None:
        controls = (
            self.cb_api,
            self.rb_all,
            self.rb_validated,
            self.rb_validated_partial,
            self.rb_partial,
            self.rb_selection,
            self.rb_slow,
            self.rb_fast,
        )
        for control in controls:
            control.setEnabled(not busy)

        self.btn_cancel.setEnabled(not busy)
        self.btn_retry_failed.setEnabled((not busy) and bool(self.__last_failed_items))
        self.btn_translate.setEnabled(not stopping)

        if stopping:
            self.btn_translate.setText(interface.text('TranslateDialog', 'Stopping...'))
        elif busy:
            self.btn_translate.setText(interface.text('TranslateDialog', 'Stop translate'))
        else:
            self.btn_translate.setText(interface.text('TranslateDialog', 'Translate'))
            self.check_api()

    def __mark_handle_failed(self, handle, exclude_indexes=None) -> None:
        if handle is None:
            return
        failed_indexes = getattr(self, '_TranslateDialog__failed_item_indexes', None)
        chunk_items = getattr(self, '_TranslateDialog__chunk_items_by_handle', {})
        if failed_indexes is None:
            return
        excluded = set(exclude_indexes or ())
        for index, _item in chunk_items.get(handle, ()):
            if index not in excluded:
                failed_indexes.add(index)
