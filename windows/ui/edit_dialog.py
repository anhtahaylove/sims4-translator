# -*- coding: utf-8 -*-

from PySide6.QtCore import QMetaObject, Qt
from PySide6.QtWidgets import QComboBox, QFrame, QLabel, QLineEdit, QPushButton, QSplitter, QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtGui import QIcon

from widgets.tableview import QDictionaryTableView
from widgets.editor import QTextEditor


class Ui_EditDialog(object):

    def setupUi(self, EditDialog):
        EditDialog.resize(1009, 663)
        EditDialog.setMinimumSize(961, 611)

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
        self.edit_header.setObjectName('editHeader')
        header_layout = QVBoxLayout(self.edit_header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(6)
        self.edit_title = QLabel('Search and Edit', self.edit_header)
        self.edit_title.setObjectName('dialogTitle')
        header_layout.addWidget(self.edit_title)
        header_layout.addWidget(self.txt_resource)

        layout.addWidget(self.edit_header)

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
        self.original_panel.setObjectName('editPanel')
        original_layout = QVBoxLayout(self.original_panel)
        original_layout.setContentsMargins(0, 0, 0, 0)
        original_layout.addWidget(left_widget)

        self.translation_panel = QFrame(EditDialog)
        self.translation_panel.setObjectName('editPanel')
        translation_layout = QVBoxLayout(self.translation_panel)
        translation_layout.setContentsMargins(0, 0, 0, 0)
        translation_layout.addWidget(right_widget)

        self.dictionary_panel = QFrame(EditDialog)
        self.dictionary_panel.setObjectName('editPanel')
        dictionary_layout = QVBoxLayout(self.dictionary_panel)
        dictionary_layout.setContentsMargins(10, 10, 10, 10)
        dictionary_layout.setSpacing(6)
        self.dictionary_title = QLabel('Dictionary suggestions', self.dictionary_panel)
        self.dictionary_title.setObjectName('sectionLabel')
        dictionary_layout.addWidget(self.dictionary_title)
        dictionary_layout.addWidget(self.tableview)

        self.search_panel = QFrame(EditDialog)
        self.search_panel.setObjectName('editPanel')
        search_layout = QVBoxLayout(self.search_panel)
        search_layout.setContentsMargins(10, 10, 10, 10)
        search_layout.setSpacing(6)
        self.search_title = QLabel('Selected suggestion', self.search_panel)
        self.search_title.setObjectName('sectionLabel')
        search_layout.addWidget(self.search_title)
        search_layout.addWidget(self.txt_search)

        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.addWidget(self.dictionary_panel)
        top_splitter.addWidget(self.search_panel)
        top_splitter.setSizes([500, 300])
        top_splitter.setHandleWidth(8)

        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        bottom_splitter.addWidget(self.original_panel)
        bottom_splitter.addWidget(self.translation_panel)
        bottom_splitter.setSizes([300, 500])
        bottom_splitter.setHandleWidth(8)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(top_splitter)
        splitter.addWidget(bottom_splitter)
        splitter.setSizes([200, 350])
        splitter.setHandleWidth(8)

        layout.addWidget(splitter)

        self.txt_comment = QLineEdit(EditDialog)

        self.cb_api = QComboBox(EditDialog)

        self.btn_translate = QPushButton(EditDialog)
        self.btn_translate.setIcon(QIcon(':/images/api.png'))
        self.btn_translate.setAutoDefault(False)

        self.lbl_status = QLabel(EditDialog)

        self.btn_ok = QPushButton(EditDialog)
        self.btn_cancel = QPushButton(EditDialog)

        self.btn_ok.setDefault(True)
        self.btn_cancel.setAutoDefault(False)

        self.edit_footer = QFrame(EditDialog)
        self.edit_footer.setObjectName('editFooter')
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
        hlayout.addWidget(self.btn_ok)

        footer_layout.addWidget(self.txt_comment)
        footer_layout.addLayout(hlayout)

        layout.addWidget(self.edit_footer)

        QMetaObject.connectSlotsByName(EditDialog)
