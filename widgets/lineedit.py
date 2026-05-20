# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QLineEdit, QProxyStyle, QStyle
from PySide6.QtGui import QIcon, QPixmap


class CustomProxyStyle(QProxyStyle):
    def standardIcon(self, standardIcon, option=None, widget=None):
        if standardIcon == QStyle.StandardPixmap.SP_LineEditClearButton:
            return QIcon(QPixmap(':/images/life/backspace.png'))
        return super().standardIcon(standardIcon, option, widget)


class QCleaningLineEdit(QLineEdit):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyle(CustomProxyStyle())
