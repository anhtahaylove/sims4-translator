# -*- coding: utf-8 -*-

from PySide6.QtCore import QMetaObject
from PySide6.QtWidgets import QFrame, QGroupBox, QHBoxLayout, QPushButton, QRadioButton, QVBoxLayout, \
    QLabel, QTextEdit

from widgets.comboboxes import NoWheelComboBox


class Ui_TranslateDialog(object):

    def setupUi(self, TranslateDialog):
        TranslateDialog.resize(640, 560)
        TranslateDialog.setMinimumSize(560, 500)

        layout = QVBoxLayout(TranslateDialog)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.header = QFrame(TranslateDialog)
        self.header.setObjectName('sheetHeader')
        header_layout = QVBoxLayout(self.header)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(3)
        self.header_title = QLabel('Batch translate', self.header)
        self.header_title.setObjectName('sheetTitle')
        self.header_detail = QLabel('Translate the chosen records in the background and keep the workspace responsive.', self.header)
        self.header_detail.setObjectName('sheetHint')
        self.header_detail.setWordWrap(True)
        header_layout.addWidget(self.header_title)
        header_layout.addWidget(self.header_detail)
        layout.addWidget(self.header)

        gbox = QGroupBox(TranslateDialog)
        self.scope_section = gbox
        gbox.setObjectName('sheetSection')
        vlayout = QVBoxLayout(gbox)
        vlayout.setContentsMargins(14, 18, 14, 12)
        vlayout.setSpacing(8)

        self.rb_all = QRadioButton(gbox)
        self.rb_validated = QRadioButton(gbox)
        self.rb_validated_partial = QRadioButton(gbox)
        self.rb_partial = QRadioButton(gbox)
        self.rb_selection = QRadioButton(gbox)

        self.rb_validated.setChecked(True)

        vlayout.addWidget(self.rb_all)
        vlayout.addWidget(self.rb_validated)
        vlayout.addWidget(self.rb_validated_partial)
        vlayout.addWidget(self.rb_partial)
        vlayout.addWidget(self.rb_selection)

        layout.addWidget(gbox)

        gbox2 = QGroupBox(TranslateDialog)
        self.speed_section = gbox2
        gbox2.setObjectName('sheetSection')
        vlayout2 = QVBoxLayout(gbox2)
        vlayout2.setContentsMargins(14, 18, 14, 12)
        vlayout2.setSpacing(6)

        self.rb_slow = QRadioButton(gbox2)
        self.rb_fast = QRadioButton(gbox2)

        self.lbl_slow = QLabel(gbox2)
        self.lbl_fast = QLabel(gbox2)

        self.rb_slow.setStyleSheet('margin-bottom: 0;')
        self.rb_fast.setStyleSheet('margin-bottom: 0;')
        self.lbl_slow.setStyleSheet('margin-bottom: 6px;')

        self.lbl_slow.setWordWrap(True)
        self.lbl_fast.setWordWrap(True)

        self.lbl_slow.setObjectName('muted')
        self.lbl_fast.setObjectName('muted')

        self.rb_slow.setChecked(True)

        vlayout2.addWidget(self.rb_slow)
        vlayout2.addWidget(self.lbl_slow)
        vlayout2.addWidget(self.rb_fast)
        vlayout2.addWidget(self.lbl_fast)

        layout.addWidget(gbox2)

        self.log_box = QGroupBox(TranslateDialog)
        self.log_box.setObjectName('sheetSection')
        vlayout3 = QVBoxLayout(self.log_box)
        vlayout3.setContentsMargins(12, 18, 12, 12)

        self.edt_log = QTextEdit(self.log_box)
        self.edt_log.setReadOnly(True)
        self.edt_log.setObjectName('sheetLog')

        vlayout3.addWidget(self.edt_log)

        layout.addWidget(self.log_box)

        self.sheet_footer = QFrame(TranslateDialog)
        self.sheet_footer.setObjectName('sheetFooter')
        hlayout = QHBoxLayout(self.sheet_footer)
        hlayout.setContentsMargins(10, 10, 10, 10)
        hlayout.setSpacing(8)

        self.cb_api = NoWheelComboBox(TranslateDialog)
        self.cb_api.setObjectName('sheetCombo')

        self.btn_translate = QPushButton(TranslateDialog)
        self.btn_cancel = QPushButton(TranslateDialog)
        self.btn_translate.setObjectName('sheetPrimary')
        self.btn_cancel.setObjectName('sheetSecondary')

        self.btn_translate.setDefault(True)
        self.btn_cancel.setAutoDefault(False)

        hlayout.addWidget(self.cb_api)
        hlayout.addStretch()
        hlayout.addWidget(self.btn_cancel)
        hlayout.addWidget(self.btn_translate)

        layout.addWidget(self.sheet_footer)

        QMetaObject.connectSlotsByName(TranslateDialog)
