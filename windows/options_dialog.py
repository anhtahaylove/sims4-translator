# -*- coding: utf-8 -*-

from dataclasses import dataclass

from PySide6.QtCore import Qt, QCoreApplication, QObject, QTimer, QAbstractTableModel, \
    QSize, Signal, Slot, QThreadPool, QRunnable, QUrl
from PySide6.QtWidgets import QHeaderView, QStyledItemDelegate, QDialog, QMessageBox
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPainter

from windows.ui.options_dialog import Ui_OptionsDialog

from packer.dbpf import DbpfPackage
from packer.stbl import Stbl

from storages.records import MainRecord

import themes.balanced as theme

from singletons.config import config
from singletons.expansions import expansions, Expansion
from singletons.interface import interface
from singletons.languages import languages
from singletons.signals import progress_signals
from singletons.state import app_state
from singletons.translation_cache import translation_cache
from singletons.translator import (
    OLLAMA_RECOMMENDED_MODEL,
    deepl_usage,
    gemini_models,
    openai_compatible_models,
    translator,
)
from utils.functions import opendir
from utils.diagnostics import provider_health_snapshot
from utils.ollama_setup import (
    OLLAMA_DOWNLOAD_URL,
    OLLAMA_RECOMMENDED_MODEL_SIZE,
    OllamaSetupStatus,
    pull_ollama_model_task,
    refresh_ollama_status_task,
)
from utils.task_runner import TaskRunner
from utils.constants import *


PROVIDER_TEST_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class ProviderTestResult:
    engine: str
    status_code: int
    message: str
    models: tuple[str, ...] = ()
    model_list_status_code: int = 0
    model_list_message: str = ''
    selected_model: str = ''
    model_list_loaded: bool = False


@dataclass(frozen=True)
class DeepLUsageResult:
    usage: object
    validation_only: bool


def provider_test_task(token, reporter, engine: str, timeout: int | float = PROVIDER_TEST_TIMEOUT_SECONDS):
    reporter.progress(0, 0, interface.text('OptionsDialog', 'Checking {provider}...').format(provider=engine))
    token.raise_if_cancelled()
    engine_name = engine.lower()
    selected_model = ''
    model_list_status_code = 0
    model_list_message = ''
    models = ()

    if engine_name in ('gemini', 'openai-compatible'):
        reporter.progress(0, 0, interface.text('OptionsDialog', 'Loading models...'))
        if engine_name == 'gemini':
            selected_model = (config.value('api', 'gemini_model') or '').strip()
            model_result = gemini_models(timeout=timeout)
        else:
            selected_model = (config.value('api', 'openai_model') or '').strip()
            model_result = openai_compatible_models(timeout=timeout)

        token.raise_if_cancelled()
        model_list_status_code = model_result.status_code
        model_list_message = model_result.message
        models = tuple(model_result.models)
        if model_result.status_code == 200 and not selected_model:
            return ProviderTestResult(
                engine,
                200,
                interface.text('OptionsDialog', 'API key OK, choose a model.'),
                models,
                model_result.status_code,
                model_result.message,
                selected_model,
                True,
            )
        if model_result.status_code != 200 and not selected_model:
            return ProviderTestResult(
                engine,
                model_result.status_code,
                model_result.message,
                (),
                model_result.status_code,
                model_result.message,
                selected_model,
                False,
            )

    reporter.progress(0, 0, interface.text('OptionsDialog', 'Checking {provider}...').format(provider=engine))
    response = translator.translate(engine, 'Hello', request_timeout=timeout)
    token.raise_if_cancelled()
    message = response.text
    if (
            engine_name in ('gemini', 'openai-compatible') and
            model_list_status_code and
            model_list_status_code != 200 and
            response.status_code == 200
    ):
        message = '{}: OK. {}'.format(
            engine,
            interface.text('OptionsDialog', 'Model list is unavailable; typed model was kept.'),
        )
    return ProviderTestResult(
        engine,
        response.status_code,
        message,
        models,
        model_list_status_code,
        model_list_message,
        selected_model,
        model_list_status_code == 200,
    )


def deepl_usage_task(token, reporter, api_key: str, validation_only: bool,
                     timeout: int | float = PROVIDER_TEST_TIMEOUT_SECONDS):
    reporter.progress(0, 0, interface.text('OptionsDialog', 'Checking DeepL...'))
    token.raise_if_cancelled()
    usage = deepl_usage(api_key, timeout=timeout)
    token.raise_if_cancelled()
    return DeepLUsageResult(usage, validation_only)


class DictSignals(QObject):
    finished = Signal()


class DictWorker(QRunnable):

    __slots__ = ()

    def __init__(self, expansion: Expansion):
        super().__init__()

        self.expansion = expansion

        self.signals = DictSignals()

    def run(self):
        file_source = self.expansion.file_source
        file_dest = self.expansion.file_dest

        _strings = {}

        items = []

        language_source = config.value('translation', 'source')
        language_dest = config.value('translation', 'destination')

        with DbpfPackage.read(file_source) as dbfile:
            for rid in dbfile.search_stbl():
                if rid.language == language_source:
                    stbl = Stbl(rid=rid, value=dbfile[rid].content)
                    for sid, value in stbl.strings.items():
                        QCoreApplication.processEvents()
                        if value:
                            _strings[sid] = value

        with DbpfPackage.read(file_dest) as dbfile:
            for rid in dbfile.search_stbl():
                if rid.language == language_dest:
                    stbl = Stbl(rid=rid, value=dbfile[rid].content)
                    for sid, value in stbl.strings.items():
                        QCoreApplication.processEvents()
                        if sid in _strings and _strings[sid] and value:
                            items.append(
                                MainRecord(0, sid, 0, 0, _strings[sid], value, FLAG_TRANSLATED, rid, rid, None, None,
                                           None, [], ''))

        app_state.dictionaries_storage.save_standalone(self.expansion.dictionary, items)

        self.signals.finished.emit()


class Model(QAbstractTableModel):

    def __init__(self, parent=None, filter_text: str = '', category_filter: str = 'all'):
        super().__init__(parent)

        self.items = expansions.filtered_items(filter_text, category_filter)
        self.count = len(self.items)
        self.summary = expansions.summary(self.items)
        self.summary_text = self._summary_text()

        self.color_found = QColor(theme.EDITOR_SIMNAME)
        self.color_not_found = QColor(theme.TEXT_ERROR)

        self.color_null = QColor(theme.TEXT_MUTED)
        self.color_heading = QColor(theme.ACCENT)

    def rowCount(self, parent=None):
        return self.count

    def columnCount(self, parent=None):
        return 3

    def data(self, index, role=None):
        if not index.isValid():
            return None

        row = index.row()
        column = index.column()

        if row < 0 or row >= self.count:
            return None

        item = self.items[row]
        extension = isinstance(item, Expansion)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if column == 2:
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        elif role == Qt.ItemDataRole.ForegroundRole:
            if extension:
                if not item.exists:
                    return self.color_null
                else:
                    return self.color_found if item.exists_strings else self.color_not_found
            else:
                return self.color_heading

        elif role == Qt.ItemDataRole.FontRole:
            if not extension:
                font = QFont()
                font.setBold(True)
                return font

        elif role == Qt.ItemDataRole.DisplayRole:
            if not column:
                return None

            if column == 1:
                return item.offset + item.name if extension else interface.text('OptionsDialog', item)

            elif column == 2:
                return item.status + ' ' if extension else None

        elif role == Qt.ItemDataRole.ToolTipRole:
            if extension:
                return '{}\n{}\n{}'.format(item.folder, item.name, item.status)

        return None

    def _summary_text(self) -> str:
        total = self.summary['total']
        ready = self.summary['ready']
        found = self.summary['found']
        missing = self.summary['missing']
        label = 'pack' if total == 1 else 'packs'
        return f'{total} {label} listed · {ready} ready · {found} found · {missing} missing'


class PackStatusDelegate(QStyledItemDelegate):

    def __init__(self, parent=None, model=None):
        super().__init__(parent)
        self.__model = model

    def paint(self, painter, option, index):
        try:
            row = index.row()
            item = self.__model.items[row]
        except IndexError:
            item = None

        if index.column() != 2 or not isinstance(item, Expansion):
            super().paint(painter, option, index)
            return

        if item.exists_strings:
            bg = QColor(theme.SUCCESS)
            fg = QColor('#ffffff')
        elif item.exists:
            bg = QColor(theme.WARNING)
            fg = QColor('#172433')
        else:
            bg = QColor(theme.PANEL_RAISED)
            fg = QColor(theme.TEXT_MUTED)

        text = item.status
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = min(option.rect.width() - 12, max(96, option.fontMetrics.horizontalAdvance(text) + 26))
        rect = option.rect.adjusted(option.rect.width() - width - 6, 6, -6, -6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(fg)
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), text)
        painter.restore()


class OptionsDialog(QDialog, Ui_OptionsDialog):

    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon(':/logo.ico'))
        self.__configure_action_icons()

        self.main_window = parent
        self.__ollama_runner = TaskRunner(max_threads=1, parent=self)
        self.__provider_runner = TaskRunner(max_threads=2, parent=self)
        self.__ollama_status = None
        self.__ollama_status_handle = None
        self.__ollama_pull_handle = None
        self.__ollama_pull_succeeded = False
        self.__provider_test_handles = {}

        self.cb_backup.setChecked(config.value('save', 'backup'))
        self.cb_experemental.setChecked(config.value('save', 'experemental'))
        self.cb_strong.setChecked(config.value('dictionaries', 'strong'))

        for lang in interface.languages:
            self.cb_language.addItem(lang.name, lang.code)

        self.cb_language.setCurrentIndex(interface.current_index)

        for k in languages.locales:
            self.cb_source.addItem(k)
            self.cb_dest.addItem(k)

        self.cb_source.setCurrentText(config.value('translation', 'source'))
        self.cb_dest.setCurrentText(config.value('translation', 'destination'))

        self.cb_backup.clicked.connect(self.checkbox_click)
        self.cb_experemental.clicked.connect(self.checkbox_click)
        self.cb_strong.clicked.connect(self.checkbox_click)

        self.txt_path.setText(config.value('dictionaries', 'gamepath'))
        self.txt_deepl_key.setText(config.value('api', 'deepl_key'))
        self.txt_deepl_glossary_id.setText(config.value('api', 'deepl_glossary_id') or '')
        self.txt_gemini_key.setText(config.value('api', 'gemini_key') or '')
        self.cb_gemini_model.set_model_items((), config.value('api', 'gemini_model') or '')
        self.txt_openai_key.setText(config.value('api', 'openai_key') or '')
        self.txt_openai_base_url.setText(config.value('api', 'openai_base_url') or '')
        self.cb_openai_model.set_model_items((), config.value('api', 'openai_model') or '')
        self.cb_ollama_enabled.setChecked(bool(config.value('api', 'ollama_enabled')))
        self.txt_ollama_base_url.setText(config.value('api', 'ollama_base_url') or '')
        self.cb_ollama_model.set_model_items((), config.value('api', 'ollama_model') or OLLAMA_RECOMMENDED_MODEL)
        self.cb_translation_cache.setChecked(bool(config.value('translation_cache', 'enabled')))

        self.cb_language.currentIndexChanged.connect(self.interface_change)
        self.cb_source.currentIndexChanged.connect(self.language_change)
        self.cb_dest.currentIndexChanged.connect(self.language_change)

        self.txt_path.textChanged.connect(self.change_path)
        self.btn_path.clicked.connect(self.select_path)
        self.txt_pack_search.textChanged.connect(self.refresh)
        self.cb_pack_category.currentIndexChanged.connect(self.refresh)

        self.txt_deepl_key.textChanged.connect(self.change_deepl_key)
        self.txt_deepl_glossary_id.textChanged.connect(self.change_deepl_glossary_id)
        self.txt_gemini_key.textChanged.connect(self.change_ai_provider_settings)
        self.cb_gemini_model.currentTextChanged.connect(self.change_ai_provider_settings)
        self.txt_openai_key.textChanged.connect(self.change_ai_provider_settings)
        self.txt_openai_base_url.textChanged.connect(self.change_ai_provider_settings)
        self.cb_openai_model.currentTextChanged.connect(self.change_ai_provider_settings)
        self.cb_ollama_enabled.clicked.connect(self.change_ai_provider_settings)
        self.txt_ollama_base_url.textChanged.connect(self.change_ai_provider_settings)
        self.cb_ollama_model.currentTextChanged.connect(self.change_ai_provider_settings)
        self.btn_deepl_test.clicked.connect(self.test_deepl_key)
        self.btn_deepl_usage.clicked.connect(self.check_deepl_usage)
        self.btn_gemini_test.clicked.connect(lambda: self.test_ai_provider('Gemini'))
        self.btn_openai_test.clicked.connect(lambda: self.test_ai_provider('OpenAI-compatible'))
        self.btn_ollama_refresh.clicked.connect(self.refresh_ollama_models)
        self.btn_ollama_test.clicked.connect(lambda: self.test_ai_provider('Ollama'))
        self.btn_ollama_download.clicked.connect(self.download_ollama)
        self.btn_ollama_pull.clicked.connect(self.download_ollama_recommended_model)
        self.btn_ollama_cancel_pull.clicked.connect(self.cancel_ollama_model_download)
        self.cb_translation_cache.clicked.connect(self.change_translation_cache_enabled)
        self.btn_translation_cache_clear.clicked.connect(self.clear_translation_cache)

        self.btn_build.clicked.connect(self.build_click)

        self.culling_timer = QTimer()
        self.culling_timer.setSingleShot(True)
        self.culling_timer.timeout.connect(self.refresh)

        self.start_culling_timer()
        self.blank = Model(filter_text='__no_pack_matches__')
        self.model = Model()
        self.tableview.setModel(self.model)

        header = self.tableview.verticalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setDefaultSectionSize(32)

        self.tableview.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.tableview.setColumnWidth(2, 170)
        self.tableview.setColumnHidden(0, True)

        self.tableview.setItemDelegate(PackStatusDelegate(model=self.model))
        self.lbl_pack_summary.setText(self.model.summary_text)
        self.btn_build.setEnabled(len(expansions.exists()) > 0)

        self.__pool = QThreadPool()
        self.__progress = 0

        self.retranslate()
        self.refresh_translation_cache_status()
        self.refresh_provider_health_summary()
        self.refresh_ollama_models()

    def retranslate(self):
        self.setWindowTitle(interface.text('OptionsDialog', 'Options and dictionaries'))
        self.gb_interface.setTitle(interface.text('OptionsDialog', 'Interface'))
        self.gb_safety.setTitle(interface.text('OptionsDialog', 'Safety defaults'))
        self.cb_backup.setText(interface.text('OptionsDialog', 'Create backup before Finalize'))
        self.cb_backup.setToolTip(interface.text(
            'OptionsDialog',
            'Recommended. When Finalize writes over a source package, keep a .package.backup copy first.'
        ))
        self.cb_experemental.setText(interface.text('OptionsDialog',
                                                    'Use conflict-free save mode (experimental)'))
        self.cb_experemental.setToolTip(interface.text(
            'OptionsDialog',
            'Creates separate hashed STBL resources instead of touching the original STBL resources. '
            'Use only when testing conflict avoidance with a package copy.'
        ))
        self.cb_strong.setText(interface.text('OptionsDialog',
                                              'Only use exact dictionary matches'))
        self.cb_strong.setToolTip(interface.text(
            'OptionsDialog',
            'When enabled, dictionary auto-fill is stricter and avoids fallback matches from the same source text. '
            'Leave disabled to reuse more dictionary translations, then review context-sensitive strings manually.'
        ))
        self.lbl_safety_hint.setText(interface.text(
            'OptionsDialog',
            'These choices are saved automatically. For Vietnamese release work, keep backups on, leave '
            'conflict-free mode off unless testing a copy, and review context-sensitive dictionary matches.'
        ))
        self.gb_path.setTitle(interface.text('OptionsDialog', 'Game path'))
        self.gb_lang.setTitle(interface.text('OptionsDialog', 'Languages'))
        self.gb_pack_manager.setTitle(interface.text('OptionsDialog', 'Pack Manager'))
        self.label_source.setText(interface.text('OptionsDialog', 'Source'))
        self.label_dest.setText(interface.text('OptionsDialog', 'Destination'))
        self.btn_build.setText(interface.text('OptionsDialog', 'Build dictionaries'))
        self.btn_path.setText(interface.text('OptionsDialog', 'Browse...'))
        self.txt_pack_search.setPlaceholderText(interface.text('OptionsDialog', 'Filter packs...'))
        self.__retranslate_pack_categories()
        self.lbl_path_hint.setText(interface.text(
            'OptionsDialog',
            'Select the folder that contains Data, EP, GP, SP, and FP folders from your The Sims 4 installation.'
        ))
        self.lbl_pack_empty.setText(interface.text(
            'OptionsDialog',
            'No packs match the current filter. Clear the search field to see the full catalog.'
        ))
        self.tabs.setTabText(self.tabs.indexOf(self.tab_general), interface.text('OptionsDialog', 'General'))
        self.tabs.setTabText(self.tabs.indexOf(self.tab_providers), interface.text('OptionsDialog', 'Providers'))
        self.tabs.setTabText(self.tabs.indexOf(self.tab_dictionaries), interface.text('OptionsDialog', 'Dictionaries'))
        self.gb_deepl.setTitle(interface.text('OptionsDialog', 'Translation providers'))
        self.gb_provider_health.setTitle(interface.text('OptionsDialog', 'Provider health'))
        self.gb_provider_deepl.setTitle('DeepL')
        self.gb_provider_gemini.setTitle('Gemini')
        self.gb_provider_openai.setTitle(interface.text('OptionsDialog', 'OpenAI-compatible'))
        self.gb_provider_ollama.setTitle(interface.text('OptionsDialog', 'Ollama local'))
        self.lbl_deepl_key.setText(interface.text('OptionsDialog', 'API key'))
        self.lbl_deepl_glossary_id.setText(interface.text('OptionsDialog', 'Glossary ID'))
        self.lbl_gemini_key.setText(interface.text('OptionsDialog', 'API key'))
        self.lbl_gemini_model.setText(interface.text('OptionsDialog', 'Model'))
        self.lbl_openai_key.setText(interface.text('OptionsDialog', 'API key'))
        self.lbl_openai_base_url.setText(interface.text('OptionsDialog', 'Base URL'))
        self.lbl_openai_model.setText(interface.text('OptionsDialog', 'Model'))
        self.lbl_ollama_base_url.setText(interface.text('OptionsDialog', 'Base URL'))
        self.lbl_ollama_model.setText(interface.text('OptionsDialog', 'Model'))
        self.btn_deepl_test.setText(interface.text('OptionsDialog', 'Test'))
        self.btn_deepl_usage.setText(interface.text('OptionsDialog', 'Usage'))
        self.btn_gemini_test.setText(interface.text('OptionsDialog', 'Test'))
        self.btn_openai_test.setText(interface.text('OptionsDialog', 'Test'))
        model_tooltip = interface.text(
            'OptionsDialog',
            'Click Test to validate the API key and load available models. You can also type a custom model name.'
        )
        self.cb_gemini_model.setToolTip(model_tooltip)
        self.cb_openai_model.setToolTip(model_tooltip)
        self.cb_ollama_model.setToolTip(interface.text(
            'OptionsDialog',
            'Choose a local model from the dropdown, or type a custom Ollama model name.'
        ))
        self.btn_gemini_test.setToolTip(interface.text(
            'OptionsDialog',
            'Test the API key and load available models.'
        ))
        self.btn_openai_test.setToolTip(interface.text(
            'OptionsDialog',
            'Test the API key and load available models.'
        ))
        self.cb_ollama_enabled.setText(interface.text('OptionsDialog', 'Enable Ollama local provider'))
        self.btn_ollama_refresh.setText(interface.text('OptionsDialog', 'Refresh Ollama models'))
        self.btn_ollama_test.setText(interface.text('OptionsDialog', 'Test'))
        self.btn_ollama_download.setText(interface.text('OptionsDialog', 'Download Ollama'))
        self.btn_ollama_pull.setText(interface.text('OptionsDialog', 'Download model'))
        self.btn_ollama_cancel_pull.setText(interface.text('TranslateDialog', 'Cancel'))
        self.lbl_deepl_hint.setText(interface.text(
            'OptionsDialog',
            'Configured and enabled providers appear in Batch Translate and Translation Studio.'
        ))
        self.gb_cache.setTitle(interface.text('OptionsDialog', 'Translation cache'))
        self.cb_translation_cache.setText(interface.text('OptionsDialog', 'Reuse exact translation matches'))
        self.lbl_translation_cache_hint.setText(interface.text(
            'OptionsDialog',
            'Stores successful translations by source/destination language, engine, glossary or model, and source text hash. '
            'API keys are never stored in the cache.'
        ))
        self.btn_translation_cache_clear.setText(interface.text('OptionsDialog', 'Clear translation cache'))
        self.refresh_provider_health_summary()

        self.lbl_language.setText(interface.text('OptionsDialog', 'Language'))

        version = interface.version
        if version and version != APP_VERSION:
            self.lbl_language_hint.setText(interface.text('OptionsDialog', 'The translation version differs from the application version, so the interface may not be fully translated'))
            self.lbl_language_hint.setVisible(True)
        else:
            self.lbl_language_hint.setVisible(False)

        authors = interface.authors
        if authors:
            self.lbl_language_authors.setText(interface.text('OptionsDialog', 'by {}').format(authors))
            self.lbl_language_authors.setVisible(True)
        else:
            self.lbl_language_authors.setVisible(False)

    def __retranslate_pack_categories(self):
        current = self.cb_pack_category.currentData() or 'all'
        self.cb_pack_category.blockSignals(True)
        self.cb_pack_category.clear()
        self.cb_pack_category.addItem(interface.text('OptionsDialog', 'All packs'), 'all')
        self.cb_pack_category.addItem(interface.text('OptionsDialog', 'Expansion packs'), 'expansion')
        self.cb_pack_category.addItem(interface.text('OptionsDialog', 'Game packs'), 'game')
        self.cb_pack_category.addItem(interface.text('OptionsDialog', 'Stuff packs'), 'stuff')
        self.cb_pack_category.addItem(interface.text('OptionsDialog', 'Kits'), 'kit')
        self.cb_pack_category.addItem(interface.text('OptionsDialog', 'Free packs'), 'free')
        index = self.cb_pack_category.findData(current)
        self.cb_pack_category.setCurrentIndex(index if index >= 0 else 0)
        self.cb_pack_category.blockSignals(False)

    def __configure_action_icons(self):
        button_icons = (
            (self.btn_path, ':/images/load.png', QSize(20, 20)),
            (self.btn_deepl_test, ':/images/life_validate.png', QSize(20, 20)),
            (self.btn_deepl_usage, ':/images/api.png', QSize(20, 20)),
            (self.btn_gemini_test, ':/images/api.png', QSize(20, 20)),
            (self.btn_openai_test, ':/images/api.png', QSize(20, 20)),
            (self.btn_ollama_refresh, ':/images/api.png', QSize(20, 20)),
            (self.btn_ollama_test, ':/images/api.png', QSize(20, 20)),
            (self.btn_ollama_download, ':/images/load.png', QSize(20, 20)),
            (self.btn_ollama_pull, ':/images/load.png', QSize(20, 20)),
            (self.btn_ollama_cancel_pull, ':/images/validate_0.png', QSize(20, 20)),
            (self.btn_translation_cache_clear, ':/images/validate_0.png', QSize(20, 20)),
            (self.btn_build, ':/images/dict.png', QSize(22, 22)),
        )
        for button, icon_path, size in button_icons:
            icon = QIcon(icon_path)
            button.setIcon(icon)
            button.setIconSize(size)
            button.setMinimumHeight(max(button.minimumHeight(), size.height() + 12))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def start_culling_timer(self):
        self.culling_timer.start(50)

    def refresh(self):
        self.tableview.setModel(self.blank)

        self.model = Model(
            filter_text=self.txt_pack_search.text(),
            category_filter=self.cb_pack_category.currentData() or 'all'
        )

        self.tableview.setModel(self.model)
        self.tableview.setItemDelegate(PackStatusDelegate(model=self.model))
        self.lbl_pack_summary.setText(self.model.summary_text)
        self.lbl_pack_empty.setVisible(self.model.summary['total'] == 0)
        self.tableview.setVisible(self.model.summary['total'] > 0)
        self.btn_build.setEnabled(len(expansions.exists()) > 0)

    def change_deepl_key(self):
        config.set_value('api', 'deepl_key', self.txt_deepl_key.text().strip())
        self.__sync_engine_preference()
        config.save()
        self.refresh_provider_health_summary()

    def change_deepl_glossary_id(self):
        config.set_value('api', 'deepl_glossary_id', self.txt_deepl_glossary_id.text().strip())
        config.save()
        self.refresh_provider_health_summary()

    def change_ai_provider_settings(self):
        config.set_value('api', 'gemini_key', self.txt_gemini_key.text().strip())
        config.set_value('api', 'gemini_model', self.cb_gemini_model.currentText().strip())
        config.set_value('api', 'openai_key', self.txt_openai_key.text().strip())
        config.set_value('api', 'openai_base_url', self.txt_openai_base_url.text().strip())
        config.set_value('api', 'openai_model', self.cb_openai_model.currentText().strip())
        config.set_value('api', 'ollama_enabled', self.cb_ollama_enabled.isChecked())
        config.set_value('api', 'ollama_base_url', self.txt_ollama_base_url.text().strip())
        config.set_value('api', 'ollama_model', self.cb_ollama_model.currentText().strip())
        self.__sync_engine_preference()
        config.save()
        self.__refresh_ollama_status_message()
        self.refresh_provider_health_summary()

    def refresh_ollama_models(self):
        if self.__ollama_pull_handle is not None:
            return

        if self.__ollama_status_handle is not None:
            self.__ollama_status_handle.cancel()

        self.__set_ollama_busy(True)
        self.__set_ollama_status(
            interface.text('OptionsDialog', 'Checking Ollama setup...'),
            warning=False,
        )
        handle = self.__ollama_runner.start(
            refresh_ollama_status_task,
            self.txt_ollama_base_url.text().strip(),
            job_name=interface.text('OptionsDialog', 'Checking Ollama setup...'),
        )
        self.__ollama_status_handle = handle
        handle.result.connect(lambda status, task_handle=handle: self.__ollama_status_result(status, task_handle))
        handle.error.connect(lambda error, task_handle=handle: self.__ollama_task_error(error, task_handle))
        handle.finished.connect(lambda cancelled, task_handle=handle: self.__ollama_status_finished(cancelled, task_handle))

    def download_ollama(self):
        QDesktopServices.openUrl(QUrl(OLLAMA_DOWNLOAD_URL))
        self.__set_ollama_status(
            interface.text('OptionsDialog', 'Opened the official Ollama download page. Install Ollama, start it, then refresh models.'),
            warning=False,
        )

    def download_ollama_recommended_model(self):
        if not self.__ollama_status or not self.__ollama_status.can_pull_recommended_model:
            self.__set_ollama_status(
                interface.text('OptionsDialog', 'Recommended model download is not available until Ollama is installed and running.'),
                warning=True,
            )
            return

        if not self.__confirm_ollama_model_download():
            return

        self.__ollama_pull_succeeded = False
        self.__set_ollama_busy(True, pulling=True)
        handle = self.__ollama_runner.start(
            pull_ollama_model_task,
            self.__ollama_status.executable,
            OLLAMA_RECOMMENDED_MODEL,
            job_name=interface.text('OptionsDialog', 'Downloading Ollama model...'),
        )
        self.__ollama_pull_handle = handle
        handle.progress.connect(self.__ollama_pull_progress)
        handle.result.connect(lambda result, task_handle=handle: self.__ollama_pull_result(result, task_handle))
        handle.error.connect(lambda error, task_handle=handle: self.__ollama_task_error(error, task_handle))
        handle.finished.connect(lambda cancelled, task_handle=handle: self.__ollama_pull_finished(cancelled, task_handle))

    def cancel_ollama_model_download(self):
        if self.__ollama_pull_handle is not None:
            self.__ollama_pull_handle.cancel()
            self.__set_ollama_status(interface.text('OptionsDialog', 'Cancelling Ollama model download...'), warning=True)
            self.btn_ollama_cancel_pull.setEnabled(False)

    @Slot(object)
    def __ollama_status_result(self, status: OllamaSetupStatus, handle):
        if handle is not self.__ollama_status_handle:
            return
        self.__ollama_status = status
        self.__apply_ollama_status(status)

    @Slot(object)
    def __ollama_pull_result(self, result, handle):
        if handle is not self.__ollama_pull_handle:
            return
        if result.success:
            self.__ollama_pull_succeeded = True
            self.cb_ollama_model.setCurrentText(result.model)
            self.cb_ollama_enabled.setChecked(True)
            self.change_ai_provider_settings()
            self.__set_ollama_status(result.message, warning=False)
        else:
            self.__set_ollama_status(result.message, warning=True)

    @Slot(object)
    def __ollama_pull_progress(self, progress):
        if progress.message:
            self.__set_ollama_status(progress.message, warning=False)

    @Slot(object)
    def __ollama_task_error(self, error, handle):
        if handle is self.__ollama_status_handle:
            self.__ollama_status_handle = None
        if handle is self.__ollama_pull_handle:
            self.__ollama_pull_handle = None
        self.__set_ollama_busy(False)
        self.__set_ollama_status(error.message, warning=True)

    @Slot(bool)
    def __ollama_status_finished(self, _cancelled: bool, handle):
        if handle is not self.__ollama_status_handle:
            return
        self.__ollama_status_handle = None
        self.__set_ollama_busy(False)

    @Slot(bool)
    def __ollama_pull_finished(self, _cancelled: bool, handle):
        if handle is not self.__ollama_pull_handle:
            return
        succeeded = self.__ollama_pull_succeeded
        self.__ollama_pull_handle = None
        self.__ollama_pull_succeeded = False
        self.__set_ollama_busy(False)
        if succeeded:
            self.refresh_ollama_models()

    def __apply_ollama_status(self, status: OllamaSetupStatus):
        self.__ollama_status = status
        current = self.cb_ollama_model.currentText().strip() or OLLAMA_RECOMMENDED_MODEL
        models = list(status.models)
        if current and current not in models:
            models.insert(0, current)
        if OLLAMA_RECOMMENDED_MODEL not in models:
            models.insert(0, OLLAMA_RECOMMENDED_MODEL)

        self.cb_ollama_model.set_model_items(models, current)
        self.__refresh_ollama_status_message()
        self.__sync_ollama_buttons()

    def __refresh_ollama_status_message(self):
        status = self.__ollama_status
        if status is None:
            return

        selected_model = self.cb_ollama_model.currentText().strip()
        selected_model_ready = bool(selected_model and selected_model in status.models)
        ready = status.server_reachable and (status.recommended_model_installed or selected_model_ready)

        if ready and self.cb_ollama_enabled.isChecked():
            self.__set_ollama_status(
                interface.text('OptionsDialog', 'Ollama is ready and enabled.'),
                warning=False,
            )
        elif ready:
            self.__set_ollama_status(
                interface.text(
                    'OptionsDialog',
                    'Ollama is ready but disabled. Enable it to show Ollama in translation lists.'
                ),
                warning=True,
            )
        else:
            self.__set_ollama_status(status.message, warning=not status.recommended_model_installed)

    def __set_ollama_busy(self, busy: bool, pulling: bool = False):
        self.btn_ollama_refresh.setEnabled(not busy)
        self.btn_ollama_test.setEnabled(not busy)
        self.btn_ollama_download.setEnabled(not busy)
        self.btn_ollama_pull.setEnabled(not busy)
        self.btn_ollama_cancel_pull.setVisible(pulling)
        self.btn_ollama_cancel_pull.setEnabled(pulling)
        if busy and self.__ollama_status is None and not pulling:
            self.btn_ollama_download.setVisible(False)
            self.btn_ollama_pull.setVisible(False)
        if not busy:
            self.__sync_ollama_buttons()

    def __sync_ollama_buttons(self):
        status = self.__ollama_status
        if status is None:
            self.btn_ollama_download.setVisible(False)
            self.btn_ollama_pull.setVisible(False)
            self.btn_ollama_cancel_pull.setVisible(False)
            return

        self.btn_ollama_download.setVisible(not status.installed)
        self.btn_ollama_pull.setVisible(status.can_pull_recommended_model)
        self.btn_ollama_pull.setEnabled(status.can_pull_recommended_model and self.__ollama_pull_handle is None)
        self.btn_ollama_test.setEnabled(status.server_reachable and self.__ollama_pull_handle is None)
        self.btn_ollama_cancel_pull.setVisible(self.__ollama_pull_handle is not None)

    def __set_ollama_status(self, text: str, warning: bool = False):
        self.lbl_ollama_status.setProperty('state', 'warning' if warning else 'ok')
        self.lbl_ollama_status.setText(text)
        self.lbl_ollama_status.style().unpolish(self.lbl_ollama_status)
        self.lbl_ollama_status.style().polish(self.lbl_ollama_status)
        self.refresh_provider_health_summary()

    def __confirm_ollama_model_download(self) -> bool:
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Warning)
        message_box.setWindowTitle(interface.text('OptionsDialog', 'Download recommended Ollama model'))
        message_box.setText(interface.text(
            'OptionsDialog',
            'Download {model} for local translation?'
        ).format(model=OLLAMA_RECOMMENDED_MODEL))
        message_box.setInformativeText(interface.text(
            'OptionsDialog',
            'This model is about {size}. It needs internet access and disk space, and Ollama stores it outside this app.'
        ).format(size=OLLAMA_RECOMMENDED_MODEL_SIZE))
        message_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        message_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        message_box.setEscapeButton(QMessageBox.StandardButton.Cancel)
        continue_button = message_box.button(QMessageBox.StandardButton.Yes)
        continue_button.setText(interface.text('OptionsDialog', 'Download model'))
        cancel_button = message_box.button(QMessageBox.StandardButton.Cancel)
        cancel_button.setText(interface.text('TranslateDialog', 'Cancel'))

        answer = message_box.exec()
        message_box.deleteLater()
        yes = QMessageBox.StandardButton.Yes
        return answer == yes or answer == yes.value

    def test_deepl_key(self):
        self.__start_deepl_usage_task(validation_only=True)

    def check_deepl_usage(self):
        self.__start_deepl_usage_task(validation_only=False)

    def test_ai_provider(self, engine: str):
        key = self.__provider_task_key(engine)
        if key in self.__provider_test_handles:
            return

        self.change_ai_provider_settings()
        self.__set_provider_test_busy(engine, True)
        initial_status = interface.text('OptionsDialog', 'Checking {provider}...').format(provider=engine)
        if engine.lower() in ('gemini', 'openai-compatible'):
            initial_status = interface.text('OptionsDialog', 'Loading models...')
        self.__set_provider_status(
            initial_status,
            warning=False,
            engine=engine,
        )
        handle = self.__provider_runner.start(
            provider_test_task,
            engine,
            PROVIDER_TEST_TIMEOUT_SECONDS,
            job_name=interface.text('OptionsDialog', 'Checking {provider}...').format(provider=engine),
        )
        self.__provider_test_handles[key] = handle
        handle.progress.connect(lambda progress, task_key=key: self.__provider_test_progress(progress, task_key))
        handle.result.connect(lambda result, task_handle=handle: self.__provider_test_result(result, task_handle))
        handle.error.connect(lambda error, task_handle=handle, task_key=key: self.__provider_test_error(error, task_handle, task_key))
        handle.finished.connect(lambda _cancelled, task_handle=handle, task_key=key: self.__provider_test_finished(task_handle, task_key))

    @Slot(object)
    def __provider_test_progress(self, progress, key: str):
        if key not in self.__provider_test_handles or not progress.message:
            return
        engine = key.replace(' validation', '').replace(' usage', '')
        self.__set_provider_status(progress.message, warning=False, engine=engine)

    def __start_deepl_usage_task(self, validation_only: bool):
        key = 'DeepL validation' if validation_only else 'DeepL usage'
        if key in self.__provider_test_handles:
            return

        button = self.btn_deepl_test if validation_only else self.btn_deepl_usage
        button.setEnabled(False)
        self.__set_provider_status(interface.text('OptionsDialog', 'Checking DeepL...'), warning=False, engine='DeepL')
        handle = self.__provider_runner.start(
            deepl_usage_task,
            self.txt_deepl_key.text().strip(),
            validation_only,
            PROVIDER_TEST_TIMEOUT_SECONDS,
            job_name=interface.text('OptionsDialog', 'Checking DeepL...'),
        )
        self.__provider_test_handles[key] = handle
        handle.result.connect(lambda result, task_handle=handle: self.__deepl_usage_result(result, task_handle))
        handle.error.connect(lambda error, task_handle=handle, task_key=key: self.__provider_test_error(error, task_handle, task_key))
        handle.finished.connect(lambda _cancelled, task_handle=handle, task_key=key: self.__provider_test_finished(task_handle, task_key))

    @Slot(object)
    def __deepl_usage_result(self, result: DeepLUsageResult, handle):
        if handle not in self.__provider_test_handles.values():
            return
        self.__set_deepl_usage_status(result.usage, validation_only=result.validation_only)

    @Slot(object)
    def __provider_test_result(self, result: ProviderTestResult, handle):
        key = self.__provider_task_key(result.engine)
        if self.__provider_test_handles.get(key) is not handle:
            return

        if result.model_list_loaded:
            self.__apply_provider_models(result.engine, result.models, result.selected_model)

        if result.status_code == 200:
            if result.model_list_loaded:
                message = '{}: OK. {}'.format(
                    result.engine,
                    interface.text('OptionsDialog', 'Loaded {count} models.').format(count=len(result.models)),
                )
                if result.message == interface.text('OptionsDialog', 'API key OK, choose a model.'):
                    message = '{} {}'.format(
                        interface.text('OptionsDialog', 'Loaded {count} models.').format(count=len(result.models)),
                        result.message,
                    )
            else:
                message = result.message if result.message else f'{result.engine}: OK'
            self.__set_provider_status(message, warning=False, engine=result.engine)
            if result.engine.lower() == 'ollama' and not self.cb_ollama_enabled.isChecked():
                self.__set_ollama_status(
                    interface.text(
                        'OptionsDialog',
                        'Ollama is ready but disabled. Enable it to show Ollama in translation lists.'
                    ),
                    warning=True,
                )
        else:
            self.__set_provider_status(result.message, warning=True, engine=result.engine)

    def __apply_provider_models(self, engine: str, models: tuple[str, ...], current: str):
        engine_name = engine.lower()
        if engine_name == 'gemini':
            self.cb_gemini_model.set_model_items(models, current)
        elif engine_name == 'openai-compatible':
            self.cb_openai_model.set_model_items(models, current)

    @Slot(object)
    def __provider_test_error(self, error, handle, key: str):
        if self.__provider_test_handles.get(key) is not handle:
            return
        engine = key.replace(' validation', '').replace(' usage', '')
        self.__set_provider_status(error.message, warning=True, engine=engine)

    def __provider_test_finished(self, handle, key: str):
        if self.__provider_test_handles.get(key) is not handle:
            return
        self.__provider_test_handles.pop(key, None)
        engine = key.replace(' validation', '').replace(' usage', '')
        self.__set_provider_test_busy(engine, False)

    def change_translation_cache_enabled(self):
        config.set_value('translation_cache', 'enabled', self.cb_translation_cache.isChecked())
        config.save()
        self.refresh_translation_cache_status()

    def clear_translation_cache(self):
        translation_cache.clear()
        self.refresh_translation_cache_status()

    def refresh_translation_cache_status(self):
        stats = translation_cache.stats()
        self.lbl_translation_cache_status.setText(interface.text(
            'OptionsDialog',
            'Cache contains {entries:,} entry/entries, {size:,} bytes.'
        ).format(entries=stats.entries, size=stats.size_bytes))
        self.refresh_provider_health_summary()

    def refresh_provider_health_summary(self):
        if not hasattr(self, 'lbl_provider_health'):
            return

        lines = []
        for provider in provider_health_snapshot():
            status_text = self.__provider_health_status_text(provider.name, provider.status)
            detail = f' - {provider.detail}' if provider.detail else ''
            lines.append(interface.text(
                'OptionsDialog',
                '{provider}: {status} (configured: {configured}, enabled: {enabled}){detail}'
            ).format(
                provider=provider.name,
                status=status_text,
                configured=self.__yes_no(provider.configured),
                enabled=self.__yes_no(provider.enabled),
                detail=detail,
            ))
        self.lbl_provider_health.setText('\n'.join(lines))

    def __set_deepl_usage_status(self, usage, validation_only: bool = False):
        if usage.status_code == 200:
            if usage.character_limit:
                percent = usage.character_count / usage.character_limit * 100
                usage_text = f'{usage.character_count:,} / {usage.character_limit:,} characters ({percent:.1f}%)'
            else:
                usage_text = f'{usage.character_count:,} characters used'
            prefix = 'Valid key.' if validation_only else 'DeepL usage:'
            self.lbl_deepl_status.setProperty('state', 'ok')
            self.lbl_deepl_status.setText(f'{prefix} {usage_text}')
        else:
            self.__set_provider_status(usage.message, warning=True)
            return

        self.__set_provider_status(self.lbl_deepl_status.text(), warning=False, engine='DeepL')

    def __set_provider_status(self, text: str, warning: bool = False, engine: str = ''):
        if engine.lower() == 'ollama':
            self.__set_ollama_status(text, warning=warning)
            return

        label = self.__provider_status_label(engine)
        label.setProperty('state', 'warning' if warning else 'ok')
        label.setText(text)
        label.style().unpolish(label)
        label.style().polish(label)
        self.refresh_provider_health_summary()

    def __provider_status_label(self, engine: str):
        engine_name = (engine or '').lower()
        if engine_name == 'gemini':
            return self.lbl_gemini_status
        if engine_name == 'openai-compatible':
            return self.lbl_openai_status
        return self.lbl_deepl_status

    def __provider_health_status_text(self, provider_name: str, status: str) -> str:
        live_label = {
            'DeepL': self.lbl_deepl_status,
            'Gemini': self.lbl_gemini_status,
            'OpenAI-compatible': self.lbl_openai_status,
            'Ollama': self.lbl_ollama_status,
        }.get(provider_name)
        if live_label is not None and live_label.text().strip():
            return live_label.text().strip()

        labels = {
            'configured': 'Configured',
            'missing-key': 'Missing API key',
            'missing-model': 'Missing model',
            'missing-base-url': 'Missing base URL',
            'enabled': 'Enabled',
            'disabled': 'Disabled',
        }
        return interface.text('OptionsDialog', labels.get(status, status))

    @staticmethod
    def __yes_no(value: bool) -> str:
        return interface.text('OptionsDialog', 'Yes' if value else 'No')

    @staticmethod
    def __provider_task_key(engine: str) -> str:
        return (engine or '').strip() or 'Provider'

    def __set_provider_test_busy(self, engine: str, busy: bool):
        engine_name = (engine or '').lower()
        buttons = {
            'deepl': (self.btn_deepl_test, self.btn_deepl_usage),
            'gemini': (self.btn_gemini_test,),
            'openai-compatible': (self.btn_openai_test,),
            'ollama': (self.btn_ollama_test,),
        }.get(engine_name, ())
        for button in buttons:
            button.setEnabled(not busy)

    def change_path(self):
        config.set_value('dictionaries', 'gamepath', self.txt_path.text())
        self.start_culling_timer()

    def select_path(self):
        directory = opendir(config.value('dictionaries', 'gamepath'))
        if directory:
            self.txt_path.setText(directory)

    def language_change(self):
        config.set_value('translation', 'source', self.cb_source.currentText())
        config.set_value('translation', 'destination', self.cb_dest.currentText())
        self.__sync_engine_preference()
        config.save()
        self.start_culling_timer()

    @staticmethod
    def __sync_engine_preference():
        src = languages.source
        dst = languages.destination
        api_key = config.value('api', 'deepl_key')
        deepl_available = bool(api_key and src and src.deepl and dst and dst.deepl)
        if deepl_available:
            config.set_value('api', 'engine', 'DeepL')
        elif config.value('api', 'engine') not in translator.engines:
            config.set_value('api', 'engine', 'Google')

    def interface_change(self):
        config.set_value('interface', 'language', self.cb_language.currentData())
        config.save()
        interface.reload()
        self.retranslate()
        self.refresh()
        self.main_window.edit_dialog.retranslate()
        self.main_window.export_dialog.retranslate()
        self.main_window.import_dialog.retranslate()
        self.main_window.replace_dialog.retranslate()
        self.main_window.translate_dialog.retranslate()
        self.main_window.retranslate()
        self.main_window.toolbar.retranslate()
        self.main_window.tableview.refresh()
 
    def checkbox_click(self):
        config.set_value('save', 'backup', self.cb_backup.isChecked())
        config.set_value('save', 'experemental', self.cb_experemental.isChecked())
        config.set_value('dictionaries', 'strong', self.cb_strong.isChecked())
        config.save()

    def build_click(self):
        exists = expansions.exists()

        if exists:
            self.__progress = len(exists)

            progress_signals.initiate.emit(interface.text('System', 'Build dictionaries...'), self.__progress)

            for exp in exists:
                worker = DictWorker(exp)
                worker.setAutoDelete(True)
                worker.signals.finished.connect(self.__finished)
                self.__pool.start(worker)

    @Slot()
    def __finished(self):
        progress_signals.increment.emit()
        self.__progress -= 1
        if self.__progress <= 0:
            self.__progress = 0
            progress_signals.finished.emit()

    def close_click(self):
        self.close()
