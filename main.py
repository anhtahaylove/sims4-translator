# -*- coding: utf-8 -*-

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase

from windows.main_window import MainWindow

from singletons.state import app_state

from storages.packages import PackagesStorage
from storages.dictionaries import DictionariesStorage

from themes.stylesheet import stylesheet
from utils.app_logging import setup_app_logging
from utils.runtime_paths import resource_path

import resource_rc


def font_paths() -> list[Path]:
    return sorted(resource_path('fonts').glob('*.ttf'))


def apply_platform_style(argv: list[str], platform: str | None = None) -> None:
    if (platform or sys.platform) == 'win32':
        argv += ['-style', 'windows']


def load_application_fonts() -> None:
    for path in font_paths():
        QFontDatabase.addApplicationFont(str(path))


def show_main_window(window: MainWindow) -> None:
    window.showMaximized()


def main() -> None:
    apply_platform_style(sys.argv)
    setup_app_logging()

    app = QApplication(sys.argv)

    packages_storage = PackagesStorage()
    dictionaries_storage = DictionariesStorage()

    app_state.set_packages_storage(packages_storage)
    app_state.set_dictionaries_storage(dictionaries_storage)

    load_application_fonts()

    app.setStyleSheet(stylesheet())

    window = MainWindow()
    show_main_window(window)

    exit_status = app.exec()

    app.setStyleSheet('')

    sys.exit(exit_status)


if __name__ == '__main__':
    main()
