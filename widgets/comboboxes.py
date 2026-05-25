# -*- coding: utf-8 -*-

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtWidgets import QComboBox, QCompleter


class NoWheelComboBox(QComboBox):
    """Combo box that does not change selection while a parent view scrolls."""

    def wheelEvent(self, event):
        if self.view().isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()


class SearchableModelComboBox(NoWheelComboBox):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        completer = QCompleter(self.model(), self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.setCompleter(completer)
        self.lineEdit().installEventFilter(self)
        self.lineEdit().textEdited.connect(lambda _text: self.open_model_popup())

    def set_model_items(self, models, current: str = None):
        current = (current if current is not None else self.currentText()).strip()
        items = []
        for model in models:
            model = (model or '').strip()
            if model and model not in items:
                items.append(model)
        if current and current not in items:
            items.insert(0, current)

        self.blockSignals(True)
        self.clear()
        self.addItems(items)
        if current:
            self.setCurrentText(current)
        else:
            self.setCurrentIndex(-1)
            self.lineEdit().clear()
        self.blockSignals(False)

    def open_model_popup(self):
        if self.count() > 0 and not self.view().isVisible():
            self.showPopup()

    def eventFilter(self, watched, event):
        if watched is self.lineEdit():
            if event.type() == QEvent.Type.FocusIn:
                if getattr(event, 'reason', lambda: None)() != Qt.FocusReason.MouseFocusReason:
                    QTimer.singleShot(0, self.open_model_popup)
            elif event.type() == QEvent.Type.MouseButtonRelease:
                QTimer.singleShot(0, self.open_model_popup)
        return super().eventFilter(watched, event)
