# -*- coding: utf-8 -*-

import re
from PySide6.QtCore import QFile, QIODevice, QTextStream

import themes.balanced as balanced

from singletons.config import config


def stylesheet():
    theme_name = config.theme_name
    colors = balanced

    colors_dict = {
        '__THEME__': theme_name,

        '__WINDOW__': colors.WINDOW,
        '__SURFACE__': colors.SURFACE,
        '__PANEL__': colors.PANEL,
        '__PANEL_ALT__': colors.PANEL_ALT,
        '__PANEL_RAISED__': colors.PANEL_RAISED,
        '__BORDER__': colors.BORDER,
        '__ACCENT__': colors.ACCENT,
        '__ACCENT_HOVER__': colors.ACCENT_HOVER,
        '__MUTED__': colors.MUTED,
        '__SUCCESS__': colors.SUCCESS,
        '__WARNING__': colors.WARNING,

        '__TEXT__': colors.TEXT,
        '__TEXT_DISABLED__': colors.TEXT_DISABLED,
        '__TEXT_MUTED__': colors.TEXT_MUTED,
        '__TEXT_ERROR__': colors.TEXT_ERROR,

        '__BORDER_LIGHT__': colors.BORDER_LIGHT,
        '__BORDER_DARK__': colors.BORDER_DARK,
        '__BORDER_FOCUS__': colors.BORDER_FOCUS,

        '__LINE_EDIT__': colors.LINE_EDIT,
        '__PLAIN_EDIT__': colors.PLAIN_EDIT,
        '__COMBOBOX__': colors.COMBOBOX,
        '__PROGRESSBAR__': colors.PROGRESSBAR,

        '__BUTTON__': colors.BUTTON,
        '__BUTTON_HOVER__': colors.BUTTON_HOVER,
        '__BUTTON_PRESSED__': colors.BUTTON_PRESSED,
        '__BUTTON_DISABLED__': colors.BUTTON_DISABLED,
        '__BUTTON_DEFAULT__': colors.BUTTON_DEFAULT,
        '__BUTTON_DEFAULT_HOVER__': colors.BUTTON_DEFAULT_HOVER,

        '__SCROLLBAR__': colors.SCROLLBAR,
        '__SCROLLBAR_HOVER__': colors.SCROLLBAR_HOVER,

        '__SELECTION__': colors.SELECTION,
        '__SELECTION_TEXT__': colors.SELECTION_TEXT,

        '__TAB_INACTIVE__': colors.TAB_INACTIVE,
        '__TAB_ACTIVE__': colors.TAB_ACTIVE,
        '__TAB_ACTIVE_BORDER__': colors.TAB_ACTIVE_BORDER,

        '__TRANSLATED_BAR__': colors.TRANSLATED_BAR,
        '__VALIDATED_BAR__': colors.VALIDATED_BAR,
        '__PROGRESS_BAR__': colors.PROGRESS_BAR,
        '__UNVALIDATED_BAR__': colors.UNVALIDATED_BAR,

        '__HEADER__': colors.HEADER,

        '__FONT_SANS__': colors.FONT_SANS,
        '__FONT_MONOSPACE__': colors.FONT_MONOSPACE,
    }

    file = QFile(f':/theme.qss')
    if file.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
        stream = QTextStream(file)
        content = stream.readAll()
        file.close()
    else:
        content = ''

    keys = (re.escape(k) for k in colors_dict.keys())
    pattern = re.compile(r'\b(' + '|'.join(keys) + r')\b')
    return pattern.sub(lambda x: colors_dict[x.group()], content)
