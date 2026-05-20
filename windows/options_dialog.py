# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt, QCoreApplication, QObject, QTimer, QAbstractTableModel, \
    QSize, Signal, Slot, QThreadPool, QRunnable
from PySide6.QtWidgets import QHeaderView, QStyledItemDelegate, QDialog
from PySide6.QtGui import QColor, QFont, QIcon, QPainter

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
from singletons.translator import deepl_usage
from utils.functions import opendir
from utils.constants import *


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

        self.cb_language.currentIndexChanged.connect(self.interface_change)
        self.cb_source.currentIndexChanged.connect(self.language_change)
        self.cb_dest.currentIndexChanged.connect(self.language_change)

        self.txt_path.textChanged.connect(self.change_path)
        self.btn_path.clicked.connect(self.select_path)
        self.txt_pack_search.textChanged.connect(self.refresh)
        self.cb_pack_category.currentIndexChanged.connect(self.refresh)

        self.txt_deepl_key.textChanged.connect(self.change_deepl_key)
        self.txt_deepl_glossary_id.textChanged.connect(self.change_deepl_glossary_id)
        self.btn_deepl_test.clicked.connect(self.test_deepl_key)
        self.btn_deepl_usage.clicked.connect(self.check_deepl_usage)

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
        self.tabs.setTabText(self.tabs.indexOf(self.tab_dictionaries), interface.text('OptionsDialog', 'Dictionaries'))
        self.gb_deepl.setTitle(interface.text('OptionsDialog', 'DeepL API key'))
        self.btn_deepl_test.setText(interface.text('OptionsDialog', 'Test key'))
        self.btn_deepl_usage.setText(interface.text('OptionsDialog', 'Check usage'))
        self.lbl_deepl_hint.setText(interface.text(
            'OptionsDialog',
            'Paste a DeepL API key here, then choose DeepL in Search and Edit or Batch translate. '
            'DeepL appears only when the selected source and destination languages are supported. '
            'Glossary ID is optional and must match the selected DeepL language pair. '
            'Do not share or commit your API key.'
        ))
        self.lbl_deepl_autosave.setText(interface.text('OptionsDialog', 'Changes are saved automatically.'))

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
        self.__sync_deepl_engine_preference()
        config.save()

    def change_deepl_glossary_id(self):
        config.set_value('api', 'deepl_glossary_id', self.txt_deepl_glossary_id.text().strip())
        config.save()

    def test_deepl_key(self):
        usage = deepl_usage(self.txt_deepl_key.text().strip())
        self.__set_deepl_usage_status(usage, validation_only=True)

    def check_deepl_usage(self):
        usage = deepl_usage(self.txt_deepl_key.text().strip())
        self.__set_deepl_usage_status(usage, validation_only=False)

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
            self.lbl_deepl_status.setProperty('state', 'warning')
            self.lbl_deepl_status.setText(usage.message)

        self.lbl_deepl_status.style().unpolish(self.lbl_deepl_status)
        self.lbl_deepl_status.style().polish(self.lbl_deepl_status)

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
        self.__sync_deepl_engine_preference()
        config.save()
        self.start_culling_timer()

    @staticmethod
    def __sync_deepl_engine_preference():
        api_key = config.value('api', 'deepl_key')
        src = languages.source
        dst = languages.destination
        deepl_available = bool(api_key and src and src.deepl and dst and dst.deepl)
        if deepl_available:
            config.set_value('api', 'engine', 'DeepL')
        elif config.value('api', 'engine') == 'DeepL':
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
