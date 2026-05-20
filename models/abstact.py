# -*- coding: utf-8 -*-

from PySide6.QtCore import QAbstractTableModel
from PySide6.QtGui import QColor

import themes.balanced as theme


class AbstractTableModel(QAbstractTableModel):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.items = []
        self.filtered = []

        self.addition_sort = -1

        self.color_null = QColor(theme.TEXT_DISABLED)

    def rowCount(self, parent=None):
        return len(self.filtered)

    def columnCount(self, parent=None):
        return 0

    def append(self, rows):
        self.beginResetModel()
        if rows:
            if isinstance(rows[0], list):
                self.items.extend(rows)
            else:
                self.items.append(rows)
        self.endResetModel()

    def replace(self, rows):
        self.beginResetModel()
        self.items.clear()
        self.filtered.clear()
        self.items = rows
        self.endResetModel()

    def filter(self, rows):
        self.beginResetModel()
        self.filtered.clear()
        self.filtered = rows
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        for item in self.items:
            item.clear()
        self.items.clear()
        self.filtered.clear()
        self.endResetModel()
