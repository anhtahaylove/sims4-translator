# -*- coding: utf-8 -*-

from PySide6.QtCore import QMetaObject
from PySide6.QtWidgets import QCheckBox, QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton, QRadioButton, QVBoxLayout


class Ui_ExportDialog(object):

    def setupUi(self, ExportDialog):
        ExportDialog.resize(560, 440)
        ExportDialog.setMinimumSize(500, 380)

        layout = QVBoxLayout(ExportDialog)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.header = QFrame(ExportDialog)
        self.header.setObjectName('sheetHeader')
        header_layout = QVBoxLayout(self.header)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(3)
        self.header_title = QLabel('Export translation', self.header)
        self.header_title.setObjectName('sheetTitle')
        self.header_detail = QLabel('Choose which records to write, then continue in the background.', self.header)
        self.header_detail.setObjectName('sheetHint')
        self.header_detail.setWordWrap(True)
        header_layout.addWidget(self.header_title)
        header_layout.addWidget(self.header_detail)
        layout.addWidget(self.header)

        self.gb_rec = QGroupBox(ExportDialog)
        self.gb_rec.setObjectName('sheetSection')

        layout_rec = QVBoxLayout(self.gb_rec)
        layout_rec.setContentsMargins(14, 18, 14, 12)
        layout_rec.setSpacing(8)

        self.rb_all = QRadioButton(self.gb_rec)

        self.rb_translated = QRadioButton(self.gb_rec)
        self.rb_translated.setChecked(True)

        self.rb_selection = QRadioButton(self.gb_rec)

        layout_rec.addWidget(self.rb_all)
        layout_rec.addWidget(self.rb_translated)
        layout_rec.addWidget(self.rb_selection)

        layout.addWidget(self.gb_rec)

        self.option_section = QFrame(ExportDialog)
        self.option_section.setObjectName('sheetSection')
        option_layout = QVBoxLayout(self.option_section)
        option_layout.setContentsMargins(14, 12, 14, 12)
        option_layout.setSpacing(8)

        self.cb_current_instance = QCheckBox(self.option_section)
        self.cb_separate_instances = QCheckBox(self.option_section)
        self.cb_separate_packages = QCheckBox(self.option_section)

        option_layout.addWidget(self.cb_current_instance)
        option_layout.addWidget(self.cb_separate_instances)
        option_layout.addWidget(self.cb_separate_packages)
        layout.addWidget(self.option_section)
        layout.addStretch()

        self.sheet_footer = QFrame(ExportDialog)
        self.sheet_footer.setObjectName('sheetFooter')
        layout_buttons = QHBoxLayout(self.sheet_footer)
        layout_buttons.setContentsMargins(10, 10, 10, 10)
        layout_buttons.setSpacing(8)

        self.btn_export = QPushButton(ExportDialog)
        self.btn_cancel = QPushButton(ExportDialog)
        self.btn_export.setObjectName('sheetPrimary')
        self.btn_cancel.setObjectName('sheetSecondary')

        self.btn_export.setDefault(True)
        self.btn_cancel.setAutoDefault(False)

        layout_buttons.addStretch()
        layout_buttons.addWidget(self.btn_cancel)
        layout_buttons.addWidget(self.btn_export)

        layout.addWidget(self.sheet_footer)

        QMetaObject.connectSlotsByName(ExportDialog)
