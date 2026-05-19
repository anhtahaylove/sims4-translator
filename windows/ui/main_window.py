# -*- coding: utf-8 -*-

from PySide6.QtCore import QMetaObject, Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMenu,
    QMenuBar,
    QToolButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLineEdit,
    QSizePolicy,
)
from PySide6.QtGui import QAction, QIcon

from widgets.colorbar import QColorBar
from widgets.job_drawer import QJobStatusDrawer
from widgets.tableview import QMainTableView
from widgets.toolbar import QToolBar

from utils.constants import APP_NAME, APP_VERSION, APP_RELEASE_CANDITATE


class Ui_MainWindow(object):

    def setupUi(self, MainWindow):
        MainWindow.resize(1125, 723)
        MainWindow.setMinimumSize(935, 620)

        title = f'{APP_NAME} {APP_VERSION}'
        if APP_RELEASE_CANDITATE:
            title += ' RC'

        MainWindow.setWindowTitle(title)
        MainWindow.setWindowIcon(QIcon(':/logo.ico'))
        
        self.action_load_file = QAction(MainWindow)
        self.action_load_file.setIcon(QIcon(':/images/load.png'))
        self.action_load_file.setShortcut('Ctrl+O')

        self.action_save_as = QAction(MainWindow)
        self.action_save_as.setEnabled(False)
        self.action_save_as.setIcon(QIcon(':/images/dict.png'))

        self.action_close = QAction(MainWindow)
        self.action_close.setEnabled(False)
        self.action_close.setIcon(QIcon(':/images/close.png'))

        self.action_save = QAction(MainWindow)
        self.action_save.setEnabled(False)
        self.action_save.setIcon(QIcon(':/images/dict.png'))
        self.action_save.setShortcut('Ctrl+S')

        self.action_save_dictionary = QAction(MainWindow)
        self.action_save_dictionary.setEnabled(False)
        self.action_save_dictionary.setIcon(QIcon(':/images/export.png'))

        self.action_replace = QAction(MainWindow)
        self.action_replace.setEnabled(False)
        self.action_replace.setIcon(QIcon(':/images/replace.png'))
        self.action_replace.setShortcut('Ctrl+R')

        self.action_validate_all_translations = QAction(MainWindow)
        self.action_validate_all_translations.setEnabled(False)
        self.action_validate_all_translations.setIcon(QIcon(':/images/validate_2.png'))
        self.action_validate_all_translations.setShortcut('Ctrl+F1')

        self.action_reset_all_translations = QAction(MainWindow)
        self.action_reset_all_translations.setEnabled(False)
        self.action_reset_all_translations.setIcon(QIcon(':/images/validate_0.png'))
        self.action_reset_all_translations.setShortcut('Ctrl+F4')

        self.action_add_file = QAction(MainWindow)
        self.action_add_file.setEnabled(False)
        self.action_add_file.setIcon(QIcon(':/images/load.png'))

        self.action_exit = QAction(MainWindow)

        self.action_undo = QAction(MainWindow)
        self.action_undo.setEnabled(False)
        self.action_undo.setIcon(QIcon(':/images/undo.png'))
        self.action_undo.setShortcut('Ctrl+Z')

        self.action_about_qt = QAction(MainWindow)

        self.action_options = QAction(MainWindow)
        self.action_options.setIcon(QIcon(':/images/options.png'))

        self.action_translate_from_dictionaries = QAction(MainWindow)
        self.action_translate_from_dictionaries.setEnabled(False)
        self.action_translate_from_dictionaries.setIcon(QIcon(':/images/translate.png'))

        self.action_translate = QAction(MainWindow)
        self.action_translate.setEnabled(False)
        self.action_translate.setIcon(QIcon(':/images/api.png'))

        self.action_import_translation = QAction(MainWindow)
        self.action_import_translation.setEnabled(False)
        self.action_import_translation.setIcon(QIcon(':/images/import.png'))

        self.action_save_bundle = QAction(MainWindow)
        self.action_save_bundle.setEnabled(False)
        self.action_save_bundle.setIcon(QIcon(':/images/export_xml.png'))

        self.action_load_bundle = QAction(MainWindow)
        self.action_load_bundle.setIcon(QIcon(':/images/import.png'))

        self.action_finalize = QAction(MainWindow)
        self.action_finalize.setEnabled(False)
        self.action_finalize.setIcon(QIcon(':/images/dict.png'))

        self.action_finalize_as = QAction(MainWindow)
        self.action_finalize_as.setEnabled(False)
        self.action_finalize_as.setIcon(QIcon(':/images/dict.png'))

        self.action_export_xml = QAction(MainWindow)
        self.action_export_xml.setIcon(QIcon(':/images/export_xml.png'))

        self.action_export_xml_dp = QAction(MainWindow)
        self.action_export_xml_dp.setIcon(QIcon(':/images/export_xml.png'))

        self.action_export_stbl = QAction(MainWindow)
        self.action_export_stbl.setIcon(QIcon(':/images/export.png'))

        self.action_export_json_s4s = QAction(MainWindow)
        self.action_export_json_s4s.setIcon(QIcon(':/images/export_xml.png'))

        self.action_export_binary_s4s = QAction(MainWindow)
        self.action_export_binary_s4s.setIcon(QIcon(':/images/export.png'))

        self.action_export_translation_hub_csv = QAction(MainWindow)
        self.action_export_translation_hub_csv.setIcon(QIcon(':/images/export_xml.png'))

        self.action_group_original = QAction(MainWindow)
        self.action_group_original.setCheckable(True)
        self.action_group_highbit = QAction(MainWindow)
        self.action_group_highbit.setCheckable(True)
        self.action_group_lowbit = QAction(MainWindow)
        self.action_group_lowbit.setCheckable(True)

        self.action_num_standart = QAction(MainWindow)
        self.action_num_standart.setCheckable(True)
        self.action_num_source = QAction(MainWindow)
        self.action_num_source.setCheckable(True)
        self.action_num_xml = QAction(MainWindow)
        self.action_num_xml.setCheckable(True)
        self.action_num_xml_dp = QAction(MainWindow)
        self.action_num_xml_dp.setCheckable(True)

        self.action_insert = QAction(MainWindow)

        self.action_colorbar = QAction(MainWindow)
        self.action_colorbar.setCheckable(True)

        self.menubar = QMenuBar(MainWindow)

        self.menu_file = QMenu(self.menubar)
        self.menu_export_translation = QMenu(self.menu_file)
        self.menu_export_translation.setEnabled(False)
        self.menu_export_translation.setIcon(QIcon(':/images/export_xml.png'))
        self.menu_translation = QMenu(self.menubar)
        self.menu_view = QMenu(self.menubar)
        self.menu_numeration = QMenu(self.menu_view)
        self.menu_options = QMenu(self.menubar)
        self.menu_group = QMenu(self.menu_options)
        self.menu_help = QMenu(self.menubar)

        self.menubar.addAction(self.menu_file.menuAction())
        self.menubar.addAction(self.menu_translation.menuAction())
        self.menubar.addAction(self.menu_view.menuAction())
        self.menubar.addAction(self.menu_options.menuAction())
        self.menubar.addAction(self.menu_help.menuAction())
        self.menu_file.addAction(self.action_load_file)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_add_file)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_save)
        self.menu_file.addAction(self.action_save_as)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_finalize)
        self.menu_file.addAction(self.action_finalize_as)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_load_bundle)
        self.menu_file.addAction(self.action_save_bundle)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_import_translation)
        self.menu_file.addAction(self.menu_export_translation.menuAction())
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_save_dictionary)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_close)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_exit)
        self.menu_export_translation.addAction(self.action_export_stbl)
        self.menu_export_translation.addAction(self.action_export_xml)
        self.menu_export_translation.addAction(self.action_export_xml_dp)
        self.menu_export_translation.addAction(self.action_export_json_s4s)
        self.menu_export_translation.addAction(self.action_export_binary_s4s)
        self.menu_export_translation.addAction(self.action_export_translation_hub_csv)
        self.menu_translation.addAction(self.action_replace)
        self.menu_translation.addSeparator()
        self.menu_translation.addAction(self.action_translate_from_dictionaries)
        self.menu_translation.addSeparator()
        self.menu_translation.addAction(self.action_validate_all_translations)
        self.menu_translation.addAction(self.action_reset_all_translations)
        self.menu_translation.addSeparator()
        self.menu_translation.addAction(self.action_translate)
        self.menu_translation.addSeparator()
        self.menu_translation.addAction(self.action_undo)
        self.menu_view.addAction(self.action_insert)
        self.menu_view.addAction(self.action_colorbar)
        self.menu_view.addSeparator()
        self.menu_view.addAction(self.menu_numeration.menuAction())
        self.menu_numeration.addAction(self.action_num_standart)
        self.menu_numeration.addAction(self.action_num_source)
        self.menu_numeration.addAction(self.action_num_xml_dp)
        self.menu_options.addAction(self.action_options)
        self.menu_options.addSeparator()
        self.menu_options.addAction(self.menu_group.menuAction())
        self.menu_group.addAction(self.action_group_original)
        self.menu_group.addAction(self.action_group_highbit)
        self.menu_group.addAction(self.action_group_lowbit)
        self.menu_help.addAction(self.action_about_qt)

        MainWindow.setMenuBar(self.menubar)

        centralwidget = QWidget(MainWindow)
        MainWindow.setCentralWidget(centralwidget)

        self.command_bar = QFrame(MainWindow)
        self.command_bar.setObjectName('commandBar')
        command_layout = QHBoxLayout(self.command_bar)
        command_layout.setContentsMargins(12, 9, 12, 9)
        command_layout.setSpacing(8)

        self.brand_block = QFrame(self.command_bar)
        brand_layout = QVBoxLayout(self.brand_block)
        brand_layout.setContentsMargins(0, 0, 4, 0)
        brand_layout.setSpacing(1)
        self.brand_title = QLabel(APP_NAME, self.brand_block)
        self.brand_title.setObjectName('brandTitle')
        self.brand_subtitle = QLabel('Mod localization workspace', self.brand_block)
        self.brand_subtitle.setObjectName('brandSubtitle')
        brand_layout.addWidget(self.brand_title)
        brand_layout.addWidget(self.brand_subtitle)

        self.brand_divider = QFrame(self.command_bar)
        self.brand_divider.setObjectName('brandDivider')

        self.command_open = self.__command_button(self.action_load_file)
        self.command_save = self.__command_button(self.action_save)
        self.command_import = self.__command_button(self.action_import_translation)

        self.command_export = QToolButton(self.command_bar)
        self.command_export.setObjectName('commandButton')
        self.command_export.setIcon(QIcon(':/images/export.png'))
        self.command_export.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.command_export.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.command_export.setMenu(self.menu_export_translation)
        self.command_export.setEnabled(False)

        self.command_translate = self.__command_button(self.action_translate)
        self.command_dictionary = self.__command_button(self.action_save_dictionary)

        command_layout.addWidget(self.brand_block)
        command_layout.addWidget(self.brand_divider)
        command_layout.addWidget(self.command_open)
        command_layout.addWidget(self.command_save)
        command_layout.addWidget(self.command_import)
        command_layout.addWidget(self.command_export)
        command_layout.addWidget(self.command_translate)
        command_layout.addWidget(self.command_dictionary)

        command_spacer = QWidget(self.command_bar)
        command_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        command_layout.addWidget(command_spacer)

        self.command_options = self.__command_button(self.action_options)
        command_layout.addWidget(self.command_options)

        self.toolbar = QToolBar(MainWindow)
        self.toolbar.setObjectName('filterBar')
        self.tableview = QMainTableView(MainWindow)
        self.colorbar = QColorBar(MainWindow)
        self.job_drawer = QJobStatusDrawer(MainWindow)

        self.colorbar.setVisible(False)

        layout = QVBoxLayout(centralwidget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self.command_bar)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.colorbar)
        layout.addWidget(self.tableview, 1)

        self.monospace = QLineEdit(MainWindow)
        self.monospace.setObjectName('monospace')
        self.monospace.setVisible(False)

        layout.addWidget(self.monospace)
        layout.addWidget(self.job_drawer)

        QMetaObject.connectSlotsByName(MainWindow)

    def __command_button(self, action):
        button = QToolButton(self.command_bar)
        button.setObjectName('commandButton')
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        return button
