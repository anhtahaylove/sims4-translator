# -*- coding: utf-8 -*-

from PySide6.QtCore import QMetaObject, QSize, Qt
from PySide6.QtWidgets import QWidget, QAbstractItemView, QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel, \
    QLineEdit, QPushButton, QTableView, QVBoxLayout, QTabWidget, QHeaderView


class Ui_OptionsDialog(object):

    def setupUi(self, OptionsDialog):
        OptionsDialog.resize(840, 680)
        OptionsDialog.setMinimumSize(760, 580)
        OptionsDialog.setObjectName('optionsDialog')

        layout = QVBoxLayout(OptionsDialog)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.tab_general = QWidget()
        self.tab_dictionaries = QWidget()

        self.tabs = QTabWidget(OptionsDialog)
        self.tabs.addTab(self.tab_general, '')
        self.tabs.addTab(self.tab_dictionaries, '')

        layout.addWidget(self.tabs)

        self.build_general_tab()
        self.build_dictionaries_tab()

        QMetaObject.connectSlotsByName(OptionsDialog)

    def build_general_tab(self):
        vlayout = QVBoxLayout(self.tab_general)
        vlayout.setContentsMargins(8, 8, 8, 8)
        vlayout.setSpacing(10)

        self.gb_interface = QGroupBox(self.tab_general)
        self.gb_interface.setObjectName('optionsSection')

        layout_group = QVBoxLayout(self.gb_interface)
        layout_group.setSpacing(8)

        layout_lang = QHBoxLayout()
        self.lbl_language = QLabel(self.gb_interface)
        self.lbl_language_authors = QLabel(self.gb_interface)
        self.lbl_language_hint = QLabel(self.gb_interface)
        self.cb_language = QComboBox(self.gb_interface)

        self.lbl_language_hint.setWordWrap(True)
        self.lbl_language_hint.setObjectName('muted')

        self.lbl_language.setMinimumHeight(26)

        layout_lang_lbl = QVBoxLayout()
        layout_lang_authors = QHBoxLayout()
        layout_lang_hint = QVBoxLayout()

        layout_lang_authors.addWidget(self.cb_language)
        layout_lang_authors.addWidget(self.lbl_language_authors)
        layout_lang_authors.addStretch()

        layout_lang_lbl.addWidget(self.lbl_language)
        layout_lang_lbl.addStretch()

        layout_lang_hint.addLayout(layout_lang_authors)
        layout_lang_hint.addWidget(self.lbl_language_hint)

        layout_lang.addLayout(layout_lang_lbl)
        layout_lang.addLayout(layout_lang_hint)

        self.lbl_language.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.lbl_language.setMinimumWidth(75)

        layout_group.addLayout(layout_lang)

        vlayout.addWidget(self.gb_interface)

        self.gb_safety = QGroupBox(self.tab_general)
        self.gb_safety.setObjectName('optionsSection')
        layout_group = QVBoxLayout(self.gb_safety)
        layout_group.setSpacing(7)

        self.cb_backup = QCheckBox(self.gb_safety)
        self.cb_experemental = QCheckBox(self.gb_safety)
        self.cb_strong = QCheckBox(self.gb_safety)
        self.lbl_safety_hint = QLabel(self.gb_safety)
        self.lbl_safety_hint.setObjectName('optionsHint')
        self.lbl_safety_hint.setWordWrap(True)

        layout_group.addWidget(self.cb_backup)
        layout_group.addWidget(self.cb_experemental)
        layout_group.addWidget(self.cb_strong)
        layout_group.addWidget(self.lbl_safety_hint)

        vlayout.addWidget(self.gb_safety)

        self.gb_lang = QGroupBox(self.tab_general)
        self.gb_lang.setObjectName('optionsSection')

        layout_lang = QHBoxLayout(self.gb_lang)
        layout_lang.setSpacing(10)

        self.label_source = QLabel(self.gb_lang)
        self.label_dest = QLabel(self.gb_lang)

        self.cb_source = QComboBox(self.gb_lang)
        self.cb_dest = QComboBox(self.gb_lang)

        layout_lang.addStretch()
        layout_lang.addWidget(self.label_source)
        layout_lang.addWidget(self.cb_source)
        layout_lang.addStretch()
        layout_lang.addWidget(self.label_dest)
        layout_lang.addWidget(self.cb_dest)
        layout_lang.addStretch()

        vlayout.addWidget(self.gb_lang)

        self.gb_deepl = QGroupBox(self.tab_general)
        self.gb_deepl.setObjectName('optionsSection')

        layout_deepl = QVBoxLayout(self.gb_deepl)
        layout_deepl.setSpacing(8)

        self.txt_deepl_key = QLineEdit(self.gb_deepl)
        self.txt_deepl_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_deepl_key.setPlaceholderText('DeepL API key')
        self.txt_deepl_glossary_id = QLineEdit(self.gb_deepl)
        self.txt_deepl_glossary_id.setPlaceholderText('Optional glossary ID')
        layout_deepl_actions = QHBoxLayout()
        self.btn_deepl_test = QPushButton(self.gb_deepl)
        self.btn_deepl_usage = QPushButton(self.gb_deepl)
        self.btn_deepl_test.setAutoDefault(False)
        self.btn_deepl_usage.setAutoDefault(False)
        self.btn_deepl_test.setIconSize(QSize(20, 20))
        self.btn_deepl_usage.setIconSize(QSize(20, 20))
        layout_deepl_actions.addWidget(self.btn_deepl_test)
        layout_deepl_actions.addWidget(self.btn_deepl_usage)
        layout_deepl_actions.addStretch()
        self.lbl_deepl_hint = QLabel(self.gb_deepl)
        self.lbl_deepl_hint.setObjectName('muted')
        self.lbl_deepl_hint.setWordWrap(True)
        self.lbl_deepl_autosave = QLabel(self.gb_deepl)
        self.lbl_deepl_autosave.setObjectName('muted')
        self.lbl_deepl_status = QLabel(self.gb_deepl)
        self.lbl_deepl_status.setObjectName('muted')
        self.lbl_deepl_status.setWordWrap(True)

        layout_deepl.addWidget(self.txt_deepl_key)
        layout_deepl.addWidget(self.txt_deepl_glossary_id)
        layout_deepl.addLayout(layout_deepl_actions)
        layout_deepl.addWidget(self.lbl_deepl_hint)
        layout_deepl.addWidget(self.lbl_deepl_autosave)
        layout_deepl.addWidget(self.lbl_deepl_status)

        vlayout.addWidget(self.gb_deepl)

        self.gb_cache = QGroupBox(self.tab_general)
        self.gb_cache.setObjectName('optionsSection')

        layout_cache = QVBoxLayout(self.gb_cache)
        layout_cache.setSpacing(8)

        self.cb_translation_cache = QCheckBox(self.gb_cache)
        self.lbl_translation_cache_hint = QLabel(self.gb_cache)
        self.lbl_translation_cache_hint.setObjectName('muted')
        self.lbl_translation_cache_hint.setWordWrap(True)
        self.lbl_translation_cache_status = QLabel(self.gb_cache)
        self.lbl_translation_cache_status.setObjectName('muted')
        self.btn_translation_cache_clear = QPushButton(self.gb_cache)
        self.btn_translation_cache_clear.setAutoDefault(False)
        self.btn_translation_cache_clear.setIconSize(QSize(20, 20))

        layout_cache.addWidget(self.cb_translation_cache)
        layout_cache.addWidget(self.lbl_translation_cache_hint)
        layout_cache.addWidget(self.lbl_translation_cache_status)
        layout_cache.addWidget(self.btn_translation_cache_clear)

        vlayout.addWidget(self.gb_cache)

        vlayout.addStretch()

    def build_dictionaries_tab(self):
        vlayout = QVBoxLayout(self.tab_dictionaries)
        vlayout.setContentsMargins(8, 8, 8, 8)
        vlayout.setSpacing(10)

        self.gb_path = QGroupBox(self.tab_dictionaries)
        self.gb_path.setObjectName('optionsSection')

        layout_path_group = QVBoxLayout(self.gb_path)
        layout_path_group.setSpacing(8)
        layout_path = QHBoxLayout()
        layout_path.setSpacing(8)

        self.txt_path = QLineEdit(self.gb_path)

        self.btn_path = QPushButton(self.gb_path)
        self.btn_path.setText('Browse...')
        self.btn_path.setAutoDefault(False)
        self.btn_path.setIconSize(QSize(20, 20))

        layout_path.addWidget(self.txt_path)
        layout_path.addWidget(self.btn_path)
        layout_path_group.addLayout(layout_path)

        self.lbl_path_hint = QLabel(self.gb_path)
        self.lbl_path_hint.setObjectName('packHintLabel')
        self.lbl_path_hint.setWordWrap(True)
        layout_path_group.addWidget(self.lbl_path_hint)

        vlayout.addWidget(self.gb_path)

        self.gb_pack_manager = QGroupBox(self.tab_dictionaries)
        self.gb_pack_manager.setObjectName('optionsSection')
        layout_pack_manager = QVBoxLayout(self.gb_pack_manager)
        layout_pack_manager.setSpacing(8)

        layout_summary = QHBoxLayout()
        layout_summary.setSpacing(8)

        self.txt_pack_search = QLineEdit(self.gb_pack_manager)
        self.txt_pack_search.setObjectName('packSearch')
        self.cb_pack_category = QComboBox(self.gb_pack_manager)
        self.cb_pack_category.setObjectName('packCategory')

        self.lbl_pack_summary = QLabel(self.gb_pack_manager)
        self.lbl_pack_summary.setObjectName('packSummaryLabel')
        self.lbl_pack_summary.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout_summary.addWidget(self.txt_pack_search, 1)
        layout_summary.addWidget(self.cb_pack_category)
        layout_summary.addWidget(self.lbl_pack_summary)

        layout_pack_manager.addLayout(layout_summary)

        self.lbl_pack_empty = QLabel(self.gb_pack_manager)
        self.lbl_pack_empty.setObjectName('packHintLabel')
        self.lbl_pack_empty.setWordWrap(True)
        self.lbl_pack_empty.setVisible(False)
        layout_pack_manager.addWidget(self.lbl_pack_empty)

        self.tableview = QTableView(self.gb_pack_manager)
        self.tableview.setObjectName('packManagerTable')
        self.tableview.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tableview.setAutoScroll(False)
        self.tableview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableview.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tableview.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableview.setShowGrid(False)
        self.tableview.setGridStyle(Qt.PenStyle.NoPen)
        self.tableview.setWordWrap(False)
        self.tableview.horizontalHeader().setVisible(False)

        header = self.tableview.verticalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setDefaultSectionSize(32)
        header.setVisible(False)
        
        self.btn_build = QPushButton(self.gb_pack_manager)
        self.btn_build.setObjectName('packBuildButton')
        self.btn_build.setAutoDefault(False)
        self.btn_build.setIconSize(QSize(22, 22))

        layout_pack_manager.addWidget(self.tableview)
        layout_pack_manager.addWidget(self.btn_build)
        vlayout.addWidget(self.gb_pack_manager)
