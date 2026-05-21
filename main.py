# -*- coding: utf-8 -*-

import os
import sys
import glob
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase

from windows.main_window import MainWindow

from singletons.state import app_state

from storages.packages import PackagesStorage
from storages.dictionaries import DictionariesStorage

from themes.stylesheet import stylesheet
from utils.app_logging import setup_app_logging

import resource_rc


def show_main_window(window: MainWindow) -> None:
    window.showMaximized()


def main():
    sys.argv += ['-style', 'windows']
    setup_app_logging()

    app = QApplication(sys.argv)

    packages_storage = PackagesStorage()
    dictionaries_storage = DictionariesStorage()

    app_state.set_packages_storage(packages_storage)
    app_state.set_dictionaries_storage(dictionaries_storage)

    for path in glob.glob('fonts/*.ttf'):
        QFontDatabase.addApplicationFont(os.path.abspath(path))

    app.setStyleSheet(stylesheet())

    window = MainWindow()
    show_main_window(window)

    exit_status = app.exec()

    app.setStyleSheet('')

    sys.exit(exit_status)


if __name__ == '__main__':
    main()
