# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QToolBar as ToolBar, QComboBox, QWidget, QSizePolicy
from PySide6.QtGui import QAction, QIcon

from widgets.lineedit import QCleaningLineEdit

from singletons.interface import interface


class QToolBar(ToolBar):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMovable(False)
        self.setIconSize(QSize(18, 18))
        self.setFloatable(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)

        self.search_toggle = QAction(QIcon(':/images/search_source'), None)

        self.filter_validate_3 = QAction(QIcon(':/images/validate_3'), None)
        self.filter_validate_3.setCheckable(True)
        self.filter_validate_3.setChecked(True)

        self.filter_validate_0 = QAction(QIcon(':/images/validate_0'), None)
        self.filter_validate_0.setCheckable(True)
        self.filter_validate_0.setChecked(True)

        self.filter_validate_2 = QAction(QIcon(':/images/validate_2'), None)
        self.filter_validate_2.setCheckable(True)
        self.filter_validate_2.setChecked(True)

        self.filter_validate_1 = QAction(QIcon(':/images/validate_1'), None)
        self.filter_validate_1.setCheckable(True)
        self.filter_validate_1.setChecked(True)

        self.filter_validate_4 = QAction(QIcon(':/images/validate_4'), None)
        self.filter_validate_4.setCheckable(True)

        self.edt_search = FixedLineEdit()
        self.cb_files = FilesComboBox()
        self.cb_instances = InstancesComboBox()

        self.addSeparator()
        self.addWidget(self.edt_search)
        self.addSeparator()
        self.addAction(self.search_toggle)

        self.addSeparator()

        self.addAction(self.filter_validate_3)
        self.addAction(self.filter_validate_0)
        self.addAction(self.filter_validate_2)
        self.addAction(self.filter_validate_1)

        self.addSeparator()

        self.addAction(self.filter_validate_4)

        self.addSeparator()

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.addWidget(spacer)

        self.addWidget(self.cb_files)
        self.addSeparator()
        self.addWidget(self.cb_instances)
        self.addSeparator()

        self.retranslate()

    def retranslate(self):
        self.search_toggle.setToolTip('Search ID, original and translation')
        self.filter_validate_0.setToolTip('Untranslated')
        self.filter_validate_1.setToolTip('Needs review')
        self.filter_validate_2.setToolTip('Approved')
        self.filter_validate_3.setToolTip('Draft')
        self.filter_validate_4.setToolTip('Modified strings')

        self.edt_search.setPlaceholderText(interface.text('ToolBar', 'Search...'))
        self.cb_instances.setItemText(0, interface.text('ToolBar', '-- All instances --'))
        self.cb_files.setItemText(0, interface.text('ToolBar', '-- All files --'))


class FixedLineEdit(QCleaningLineEdit):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.adjusted_size = 200

        self.setClearButtonEnabled(True)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        self.setContentsMargins(0, 0, 0, 0)

    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        return QSize(self.adjusted_size, 26)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.clear()


class ExpandingComboBox(QComboBox):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.adjusted_size = 200
        self.popup_min_width = 220
        self.popup_max_width = 720

    def update_popup_width(self):
        width = max(self.width(), self.adjusted_size, self.popup_min_width)
        metrics = self.fontMetrics()
        for index in range(self.count()):
            text = self.itemText(index)
            if text:
                self.setItemData(index, text, Qt.ItemDataRole.ToolTipRole)
                width = max(width, metrics.horizontalAdvance(text) + 44)
        self.view().setMinimumWidth(min(width, self.popup_max_width))

    def showPopup(self):
        self.update_popup_width()
        super().showPopup()

    def wheelEvent(self, event):
        event.ignore()

    def addItem(self, *args, **kwargs):
        super().addItem(*args, **kwargs)
        self.update_popup_width()

    def addItems(self, texts):
        super().addItems(texts)
        self.update_popup_width()

    def setItemText(self, index, text):
        super().setItemText(index, text)
        self.update_popup_width()

    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        return QSize(self.adjusted_size, 26)


class InstancesComboBox(ExpandingComboBox):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.adjusted_size = 200
        self.popup_min_width = 260

        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        self.setContentsMargins(0, 0, 0, 0)

        self.addItem('')


class FilesComboBox(ExpandingComboBox):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.adjusted_size = 470
        self.popup_min_width = 420

        size_policy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.setSizePolicy(size_policy)
        self.setContentsMargins(0, 0, 0, 0)

        self.addItem('')
