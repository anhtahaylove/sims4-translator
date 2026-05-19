# -*- coding: utf-8 -*-

import html
import re

from PySide6.QtCore import QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QTextDocument
from PySide6.QtWidgets import QProxyStyle, QStyle, QStyledItemDelegate, QStyleOptionHeader, QStyleOptionViewItem

import themes.light as light
import themes.dark as dark

from singletons.config import config
from singletons.state import app_state
from utils.constants import *


TOKEN_PATTERN = re.compile(r'(\{[^{}]+\}|</?[^<>]+>)')


STATUS_META = {
    FLAG_UNVALIDATED: ('Original', '#d5b75e'),
    FLAG_PROGRESS: ('In progress', '#ffd166'),
    FLAG_VALIDATED: ('Validated', '#4fe3a6'),
    FLAG_TRANSLATED: ('Translated', '#40dfff'),
    FLAG_REPLACED: ('Edited', '#f4a7df'),
}


class GridPalette:

    def __init__(self) -> None:
        colors = dark if config.is_dark_theme() else light
        self.surface = QColor(colors.SURFACE)
        self.panel = QColor(colors.PANEL)
        self.panel_alt = QColor(colors.PANEL_ALT)
        self.panel_raised = QColor(colors.PANEL_RAISED)
        self.border = QColor(colors.BORDER)
        self.accent = QColor(colors.ACCENT)
        self.muted = QColor(colors.TEXT_MUTED)
        self.text = QColor(colors.TEXT)
        self.disabled = QColor(colors.TEXT_DISABLED)
        self.selection = QColor(colors.SELECTION)
        self.selection_text = QColor(colors.SELECTION_TEXT)
        self.warning = QColor(colors.WARNING)
        self.different = QColor(colors.DIFFERENT_TABLEVIEW)

    def row_background(self, row: int, selected: bool = False) -> QColor:
        if selected:
            return self.selection
        return self.panel if row % 2 == 0 else self.panel_alt


class MainDelegatePaint(QStyledItemDelegate):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.model = app_state.packages_storage.model
        self.proxy = app_state.packages_storage.proxy
        self.palette = GridPalette()

    def paint(self, painter, option, index):
        item = self.__item(index)
        if item is None:
            super().paint(painter, option, index)
            return

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)

        selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        self.__paint_background(painter, opt, index, item, selected)

        if index.column() == COLUMN_MAIN_FLAG:
            self.__paint_status(painter, opt, item)
        elif index.column() in (COLUMN_MAIN_SOURCE, COLUMN_MAIN_TRANSLATE):
            self.__paint_rich_text(painter, opt, index, selected)
        else:
            self.__paint_text(painter, opt, index, selected)

        if opt.state & QStyle.StateFlag.State_HasFocus:
            focus_rect = opt.rect.adjusted(1, 1, -2, -2)
            painter.setPen(self.palette.accent)
            painter.drawRoundedRect(focus_rect, 4, 4)

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(super().sizeHint(option, index).width(), 38)

    def __item(self, index):
        try:
            row = self.proxy.mapToSource(index).row()
            if 0 <= row < len(self.model.filtered):
                return self.model.filtered[row]
        except (AttributeError, IndexError):
            return None
        return None

    def __paint_background(self, painter, option, index, item, selected: bool) -> None:
        color = self.palette.row_background(index.row(), selected)

        if not selected and (
                index.column() == COLUMN_MAIN_SOURCE and item.source_old or
                index.column() == COLUMN_MAIN_TRANSLATE and item.translate_old
        ):
            color = self.__mix(color, self.palette.warning, 0.18)

        painter.fillRect(option.rect, color)

        painter.setPen(self.palette.border)
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())

    def __paint_status(self, painter, option, item) -> None:
        label, color = STATUS_META.get(item.flag, ('Unknown', self.palette.muted.name()))

        pill_rect = option.rect.adjusted(8, 10, -8, -10)
        if pill_rect.width() < 28:
            pill_rect = option.rect.adjusted(4, 12, -4, -12)

        fill = QColor(color)
        fill.setAlpha(62 if config.is_dark_theme() else 42)
        border = QColor(color)

        painter.setPen(border)
        painter.setBrush(fill)
        painter.drawRoundedRect(pill_rect, pill_rect.height() / 2, pill_rect.height() / 2)

        painter.setPen(border if config.is_dark_theme() else self.palette.text)
        painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, label)

    def __paint_rich_text(self, painter, option, index, selected: bool) -> None:
        text = index.data(Qt.ItemDataRole.DisplayRole) or ''
        rect = option.rect.adjusted(10, 5, -10, -5)

        document = QTextDocument()
        document.setDocumentMargin(0)
        document.setDefaultFont(option.font)
        document.setTextWidth(rect.width())
        document.setHtml(self.__highlight_html(text, selected))

        painter.save()
        painter.translate(rect.topLeft())
        painter.setClipRect(QRectF(0, 0, rect.width(), rect.height()))
        document.drawContents(painter, QRectF(0, 0, rect.width(), rect.height()))
        painter.restore()

    def __paint_text(self, painter, option, index, selected: bool) -> None:
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if text is None:
            return

        text = str(text)
        rect = option.rect.adjusted(10, 0, -10, 0)
        color = self.palette.selection_text if selected else self.palette.text

        if text in ('[NULL]', '[SPACEBAR]'):
            color = self.palette.disabled

        painter.setPen(color)
        alignment = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        if index.column() in (COLUMN_MAIN_INDEX, COLUMN_MAIN_ID, COLUMN_MAIN_INSTANCE,
                              COLUMN_MAIN_GROUP):
            alignment = Qt.AlignmentFlag.AlignCenter

        elided = option.fontMetrics.elidedText(text, Qt.TextElideMode.ElideRight, rect.width())
        painter.drawText(rect, alignment, elided)

    def __highlight_html(self, text: str, selected: bool) -> str:
        text_color = self.palette.selection_text if selected else self.palette.text
        token_color = self.palette.selection_text if selected else self.palette.accent
        token_bg = self.__mix(self.palette.accent, self.palette.panel_raised, 0.72)

        parts = []
        pos = 0
        for match in TOKEN_PATTERN.finditer(text):
            parts.append(html.escape(text[pos:match.start()]))
            token = html.escape(match.group(0))
            parts.append(
                '<span style="'
                f'color: {token_color.name()};'
                f'background-color: {token_bg.name()};'
                'font-weight: 600;'
                'white-space: nowrap;'
                '">'
                f'{token}'
                '</span>'
            )
            pos = match.end()
        parts.append(html.escape(text[pos:]))

        return (
            '<body style="margin:0; padding:0;">'
            f'<span style="color: {text_color.name()}; line-height: 1.25;">'
            f'{"".join(parts)}'
            '</span>'
            '</body>'
        )

    @staticmethod
    def __mix(a: QColor, b: QColor, ratio: float) -> QColor:
        ratio = max(0.0, min(1.0, ratio))
        inverse = 1.0 - ratio
        return QColor(
            int(a.red() * inverse + b.red() * ratio),
            int(a.green() * inverse + b.green() * ratio),
            int(a.blue() * inverse + b.blue() * ratio),
        )


class DictionaryDelegatePaint(QStyledItemDelegate):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.palette = GridPalette()

    def paint(self, painter, option, index):
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.fillRect(option.rect, self.palette.row_background(index.row(), selected))
        super().paint(painter, option, index)


class HeaderProxy(QProxyStyle):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.theme_name = config.theme_name

        self.text_color = QColor(dark.TEXT) if self.theme_name == 'dark' else QColor(light.TEXT)

    def drawControl(self, element, option, painter, widget=None):
        if element == QStyle.ControlElement.CE_HeaderLabel:
            sort_option = option.sortIndicator
            rect = option.rect

            text_width = option.fontMetrics.horizontalAdvance(option.text)
            text_height = option.fontMetrics.height()
            text_rect = QRect(rect.left() + (rect.width() - text_width) / 2,
                              rect.top() + 1 + (rect.height() - text_height) / 2,
                              text_width, text_height)
            painter.setPen(self.text_color)
            painter.drawText(text_rect, option.text)

            sort_icon = None
            if sort_option == QStyleOptionHeader.SortIndicator.SortDown:
                sort_icon = QIcon(f':/images/{self.theme_name}/arrow_down.png').pixmap(10, 6)
            elif sort_option == QStyleOptionHeader.SortIndicator.SortUp:
                sort_icon = QIcon(f':/images/{self.theme_name}/arrow_up.png').pixmap(10, 6)

            if sort_icon:
                sort_rect = QRect(rect.left() + (rect.width() - sort_icon.width()) / 2,
                                  rect.top(), sort_icon.width(), sort_icon.height())
                painter.drawPixmap(sort_rect, sort_icon)

        else:
            super().drawControl(element, option, painter, widget)
