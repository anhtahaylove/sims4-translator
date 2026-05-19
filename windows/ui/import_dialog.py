# -*- coding: utf-8 -*-

from PySide6.QtCore import QMetaObject
from PySide6.QtWidgets import QCheckBox, QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton, QRadioButton, QVBoxLayout


class Ui_ImportDialog(object):

    def setupUi(self, ImportDialog):
        ImportDialog.resize(560, 430)
        ImportDialog.setMinimumSize(520, 390)

        layout = QVBoxLayout(ImportDialog)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.header = QFrame(ImportDialog)
        self.header.setObjectName('sheetHeader')
        header_layout = QVBoxLayout(self.header)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(3)
        self.header_title = QLabel('Import translation', self.header)
        self.header_title.setObjectName('sheetTitle')
        self.header_detail = QLabel('Apply matching translations while keeping validated work protected.', self.header)
        self.header_detail.setObjectName('sheetHint')
        self.header_detail.setWordWrap(True)
        header_layout.addWidget(self.header_title)
        header_layout.addWidget(self.header_detail)
        layout.addWidget(self.header)

        self.gb_overwrite = QGroupBox(ImportDialog)
        self.gb_overwrite.setObjectName('sheetSection')

        layout_over = QVBoxLayout(self.gb_overwrite)
        layout_over.setContentsMargins(14, 18, 14, 12)
        layout_over.setSpacing(8)

        self.rb_all = QRadioButton(self.gb_overwrite)
        self.rb_validated = QRadioButton(self.gb_overwrite)
        self.rb_validated_partial = QRadioButton(self.gb_overwrite)
        self.rb_partial = QRadioButton(self.gb_overwrite)
        self.rb_selection = QRadioButton(self.gb_overwrite)

        self.rb_validated.setChecked(True)

        layout_over.addWidget(self.rb_all)
        layout_over.addWidget(self.rb_validated)
        layout_over.addWidget(self.rb_validated_partial)
        layout_over.addWidget(self.rb_partial)
        layout_over.addWidget(self.rb_selection)

        layout.addWidget(self.gb_overwrite)

        self.cb_replace = QCheckBox(ImportDialog)
        self.cb_replace.setChecked(True)

        self.import_summary = QLabel('Ready to import matching strings.', ImportDialog)
        self.import_summary.setObjectName('sheetSummary')
        self.import_summary.setWordWrap(True)

        layout.addWidget(self.import_summary)
        layout.addStretch()

        self.btn_import = QPushButton(ImportDialog)
        self.btn_cancel = QPushButton(ImportDialog)
        self.btn_import.setObjectName('sheetPrimary')
        self.btn_cancel.setObjectName('sheetSecondary')

        self.btn_import.setDefault(True)
        self.btn_cancel.setAutoDefault(False)

        self.sheet_footer = QFrame(ImportDialog)
        self.sheet_footer.setObjectName('sheetFooter')
        layout_buttons = QHBoxLayout(self.sheet_footer)
        layout_buttons.setContentsMargins(10, 10, 10, 10)
        layout_buttons.setSpacing(8)

        layout_buttons.addWidget(self.cb_replace)
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.btn_cancel)
        layout_buttons.addWidget(self.btn_import)

        layout.addWidget(self.sheet_footer)

        QMetaObject.connectSlotsByName(ImportDialog)
