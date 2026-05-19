# -*- coding: utf-8 -*-

from PySide6.QtCore import QMetaObject
from PySide6.QtWidgets import QCheckBox, QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton, QRadioButton, QVBoxLayout


class Ui_ImportDialog(object):

    def setupUi(self, ImportDialog):
        ImportDialog.setMinimumSize(470, 0)

        layout = QVBoxLayout(ImportDialog)

        self.header = QFrame(ImportDialog)
        self.header.setObjectName('dialogHeader')
        header_layout = QVBoxLayout(self.header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(2)
        self.header_title = QLabel('Import translation', self.header)
        self.header_title.setObjectName('dialogTitle')
        self.header_detail = QLabel('Apply matching translations while keeping validated work protected.', self.header)
        self.header_detail.setObjectName('dialogHint')
        self.header_detail.setWordWrap(True)
        header_layout.addWidget(self.header_title)
        header_layout.addWidget(self.header_detail)
        layout.addWidget(self.header)

        self.gb_overwrite = QGroupBox(ImportDialog)

        layout_over = QVBoxLayout(self.gb_overwrite)

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
        layout.addStretch()

        self.cb_replace = QCheckBox(ImportDialog)
        self.cb_replace.setChecked(True)

        self.btn_import = QPushButton(ImportDialog)
        self.btn_cancel = QPushButton(ImportDialog)

        self.btn_import.setDefault(True)
        self.btn_cancel.setAutoDefault(False)

        layout_buttons = QHBoxLayout()
        layout_buttons.setContentsMargins(0, 4, 0, 0)

        layout_buttons.addWidget(self.cb_replace)
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.btn_cancel)
        layout_buttons.addWidget(self.btn_import)

        layout.addLayout(layout_buttons)

        ImportDialog.adjustSize()
        ImportDialog.setMinimumSize(ImportDialog.size())

        QMetaObject.connectSlotsByName(ImportDialog)
