# -*- coding: utf-8 -*-

from PySide6.QtCore import QMetaObject, Qt
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QPushButton, QSplitter, QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtGui import QIcon

from widgets.comboboxes import NoWheelComboBox
from widgets.tableview import QDictionaryTableView
from widgets.editor import QTextEditor
from widgets.token_assistant import TokenAssistantWidget


class Ui_EditDialog(object):

    def setupUi(self, EditDialog):
        EditDialog.resize(1280, 820)
        EditDialog.setMinimumSize(900, 620)

        self.lbl_original = QLabel(EditDialog)
        self.lbl_original_diff = QLabel(EditDialog)
        self.lbl_translate = QLabel(EditDialog)
        self.lbl_translate_diff = QLabel(EditDialog)

        self.txt_original = QTextEditor()
        self.txt_original.setReadOnly(True)

        self.txt_original_diff = QTextEditor()
        self.txt_original_diff.setReadOnly(True)

        self.txt_translate = QTextEditor()

        self.txt_translate_diff = QTextEditor()
        self.txt_translate_diff.setReadOnly(True)

        self.txt_search = QTextEditor()
        self.txt_search.setReadOnly(True)

        self.txt_resource = QLineEdit(EditDialog)
        self.txt_resource.setReadOnly(True)
        self.txt_resource.setObjectName('editResource')

        self.tableview = QDictionaryTableView(EditDialog)

        layout = QVBoxLayout(EditDialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.edit_header = QFrame(EditDialog)
        self.edit_header.setObjectName('sheetHeader')
        header_layout = QVBoxLayout(self.edit_header)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(7)

        header_title_layout = QHBoxLayout()
        header_title_layout.setContentsMargins(0, 0, 0, 0)
        header_title_layout.setSpacing(8)
        self.edit_title = QLabel('Search and Edit', self.edit_header)
        self.edit_title.setObjectName('sheetTitle')
        self.record_status = QLabel('Status: -', self.edit_header)
        self.record_status.setObjectName('editorMetaBadge')
        self.token_status = QLabel('Token check: -', self.edit_header)
        self.token_status.setObjectName('tokenStatusBadge')
        self.btn_suggestions = QPushButton('Suggestions', self.edit_header)
        self.btn_suggestions.setObjectName('secondaryButton')
        self.btn_suggestions.setCheckable(True)
        self.btn_suggestions.setAutoDefault(False)
        self.btn_tokens = QPushButton('Tokens', self.edit_header)
        self.btn_tokens.setObjectName('secondaryButton')
        self.btn_tokens.setCheckable(True)
        self.btn_tokens.setAutoDefault(False)
        header_title_layout.addWidget(self.edit_title, 1)
        header_title_layout.addWidget(self.record_status)
        header_title_layout.addWidget(self.token_status)

        header_action_layout = QHBoxLayout()
        header_action_layout.setContentsMargins(0, 0, 0, 0)
        header_action_layout.setSpacing(8)
        header_action_layout.addStretch()
        header_action_layout.addWidget(self.btn_tokens)
        header_action_layout.addWidget(self.btn_suggestions)

        self.edit_detail = QLabel('Review suggestions, refine the draft, then approve it or mark it for review.', self.edit_header)
        self.edit_detail.setObjectName('sheetHint')
        self.edit_detail.setWordWrap(True)
        self.token_detail = QLabel('Token details will appear after a string is selected.', self.edit_header)
        self.token_detail.setObjectName('tokenDetail')
        self.token_detail.setWordWrap(True)
        self.text_metrics = QLabel('', self.edit_header)
        self.text_metrics.setObjectName('sheetHint')
        self.text_metrics.setWordWrap(True)
        header_layout.addLayout(header_title_layout)
        header_layout.addLayout(header_action_layout)
        header_layout.addWidget(self.edit_detail)
        header_layout.addWidget(self.txt_resource)
        header_layout.addWidget(self.text_metrics)
        header_layout.addWidget(self.token_detail)

        layout.addWidget(self.edit_header)

        self.token_assistant = TokenAssistantWidget(EditDialog)
        self.token_assistant.setVisible(False)
        layout.addWidget(self.token_assistant)

        left_widget = QWidget(EditDialog)
        right_widget = QWidget(EditDialog)

        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(6)
        left_layout.addWidget(self.lbl_original)
        left_layout.addWidget(self.txt_original)
        left_layout.addWidget(self.lbl_original_diff)
        left_layout.addWidget(self.txt_original_diff)

        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(6)
        right_layout.addWidget(self.lbl_translate)
        right_layout.addWidget(self.txt_translate)
        right_layout.addWidget(self.lbl_translate_diff)
        right_layout.addWidget(self.txt_translate_diff)

        self.original_panel = QFrame(EditDialog)
        self.original_panel.setObjectName('sheetPanel')
        original_layout = QVBoxLayout(self.original_panel)
        original_layout.setContentsMargins(0, 0, 0, 0)
        original_layout.addWidget(left_widget)

        self.translation_panel = QFrame(EditDialog)
        self.translation_panel.setObjectName('sheetPanel')
        translation_layout = QVBoxLayout(self.translation_panel)
        translation_layout.setContentsMargins(0, 0, 0, 0)
        translation_layout.addWidget(right_widget)

        self.dictionary_panel = QFrame(EditDialog)
        self.dictionary_panel.setObjectName('sheetPanel')
        dictionary_layout = QVBoxLayout(self.dictionary_panel)
        dictionary_layout.setContentsMargins(10, 10, 10, 10)
        dictionary_layout.setSpacing(6)
        self.dictionary_title = QLabel('Dictionary suggestions', self.dictionary_panel)
        self.dictionary_title.setObjectName('sectionLabel')
        dictionary_layout.addWidget(self.dictionary_title)
        dictionary_layout.addWidget(self.tableview)

        self.search_panel = QFrame(EditDialog)
        self.search_panel.setObjectName('sheetPanel')
        search_layout = QVBoxLayout(self.search_panel)
        search_layout.setContentsMargins(10, 10, 10, 10)
        search_layout.setSpacing(6)
        self.search_title = QLabel('Selected suggestion', self.search_panel)
        self.search_title.setObjectName('sectionLabel')
        search_layout.addWidget(self.search_title)
        search_layout.addWidget(self.txt_search)

        self.suggestions_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.suggestions_splitter.addWidget(self.dictionary_panel)
        self.suggestions_splitter.addWidget(self.search_panel)
        self.suggestions_splitter.setSizes([500, 300])
        self.suggestions_splitter.setHandleWidth(8)

        self.suggestions_dock = QFrame(EditDialog)
        self.suggestions_dock.setObjectName('suggestionsDock')
        suggestions_layout = QVBoxLayout(self.suggestions_dock)
        suggestions_layout.setContentsMargins(0, 0, 0, 0)
        suggestions_layout.setSpacing(0)
        suggestions_layout.addWidget(self.suggestions_splitter)

        self.translation_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.translation_splitter.addWidget(self.original_panel)
        self.translation_splitter.addWidget(self.translation_panel)
        self.translation_splitter.setSizes([300, 500])
        self.translation_splitter.setHandleWidth(8)

        self.edit_splitter = QSplitter(Qt.Orientation.Vertical)
        self.edit_splitter.addWidget(self.translation_splitter)
        self.edit_splitter.addWidget(self.suggestions_dock)
        self.edit_splitter.setSizes([560, 180])
        self.edit_splitter.setHandleWidth(8)

        layout.addWidget(self.edit_splitter)

        self.txt_comment = QLineEdit(EditDialog)

        self.cb_api = NoWheelComboBox(EditDialog)

        self.btn_translate = QPushButton(EditDialog)
        self.btn_translate.setIcon(QIcon(':/images/api.png'))
        self.btn_translate.setAutoDefault(False)

        self.lbl_status = QLabel(EditDialog)

        self.btn_ok = QPushButton(EditDialog)
        self.btn_review = QPushButton(EditDialog)
        self.btn_cancel = QPushButton(EditDialog)

        self.btn_ok.setDefault(True)
        self.btn_review.setAutoDefault(False)
        self.btn_cancel.setAutoDefault(False)
        self.btn_ok.setObjectName('primaryButton')
        self.btn_review.setObjectName('secondaryButton')
        self.btn_cancel.setObjectName('secondaryButton')

        self.edit_footer = QFrame(EditDialog)
        self.edit_footer.setObjectName('sheetFooter')
        footer_layout = QVBoxLayout(self.edit_footer)
        footer_layout.setContentsMargins(10, 10, 10, 10)
        footer_layout.setSpacing(8)

        hlayout = QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setSpacing(8)

        hlayout.addWidget(self.cb_api)
        hlayout.addWidget(self.btn_translate)
        hlayout.addWidget(self.lbl_status)
        hlayout.addStretch()
        hlayout.addWidget(self.btn_cancel)
        hlayout.addWidget(self.btn_review)
        hlayout.addWidget(self.btn_ok)

        footer_layout.addWidget(self.txt_comment)
        footer_layout.addLayout(hlayout)

        layout.addWidget(self.edit_footer)

        QMetaObject.connectSlotsByName(EditDialog)
