# -*- coding: utf-8 -*-

from PySide6.QtCore import QMetaObject, Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMenu,
    QMenuBar,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
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
        command_layout.addWidget(self.__command_divider())
        command_layout.addWidget(self.command_translate)
        command_layout.addWidget(self.__command_divider())
        command_layout.addWidget(self.command_dictionary)

        command_spacer = QWidget(self.command_bar)
        command_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        command_layout.addWidget(command_spacer)

        self.command_options = self.__command_button(self.action_options)
        command_layout.addWidget(self.command_options)

        self.toolbar = QToolBar(MainWindow)
        self.toolbar.setObjectName('filterBar')
        self.toolbar.setOrientation(Qt.Orientation.Vertical)
        self.toolbar.edt_search.adjusted_size = 220
        self.toolbar.cb_files.adjusted_size = 220
        self.toolbar.cb_instances.adjusted_size = 220

        self.tableview = QMainTableView(MainWindow)
        self.colorbar = QColorBar(MainWindow)
        self.job_drawer = QJobStatusDrawer(MainWindow)
        self.activity_drawer = self.job_drawer

        self.colorbar.setVisible(False)

        layout = QVBoxLayout(centralwidget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self.command_bar)

        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal, MainWindow)
        self.workspace_splitter.setObjectName('workspaceSplitter')
        self.workspace_splitter.setChildrenCollapsible(False)

        self.project_sidebar = self.__project_sidebar(MainWindow)
        self.table_panel = self.__table_panel(MainWindow)
        self.inspector_panel = self.__inspector_panel(MainWindow)

        self.workspace_splitter.addWidget(self.project_sidebar)
        self.workspace_splitter.addWidget(self.table_panel)
        self.workspace_splitter.addWidget(self.inspector_panel)
        self.workspace_splitter.setSizes([260, 680, 310])

        layout.addWidget(self.workspace_splitter, 1)

        self.monospace = QLineEdit(MainWindow)
        self.monospace.setObjectName('monospace')
        self.monospace.setVisible(False)

        layout.addWidget(self.monospace)
        layout.addWidget(self.activity_drawer)

        QMetaObject.connectSlotsByName(MainWindow)

    def __command_button(self, action):
        button = QToolButton(self.command_bar)
        button.setObjectName('commandButton')
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        return button

    def __command_divider(self):
        divider = QFrame(self.command_bar)
        divider.setObjectName('commandDivider')
        return divider

    def __project_sidebar(self, parent):
        sidebar = QFrame(parent)
        sidebar.setObjectName('projectSidebar')
        sidebar.setMinimumWidth(238)
        sidebar.setMaximumWidth(310)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.project_title = QLabel('Project', sidebar)
        self.project_title.setObjectName('panelTitle')

        self.project_summary = QLabel('No package loaded', sidebar)
        self.project_summary.setObjectName('projectSummary')
        self.project_summary.setWordWrap(True)

        self.project_hint = QLabel('Open a package or synthetic smoke file to begin translating.', sidebar)
        self.project_hint.setObjectName('panelHint')
        self.project_hint.setWordWrap(True)

        self.filter_title = QLabel('Filters', sidebar)
        self.filter_title.setObjectName('panelTitle')

        layout.addWidget(self.project_title)
        layout.addWidget(self.project_summary)
        layout.addWidget(self.project_hint)
        layout.addSpacing(8)
        layout.addWidget(self.filter_title)
        layout.addWidget(self.toolbar)
        layout.addStretch()
        return sidebar

    def __table_panel(self, parent):
        panel = QFrame(parent)
        panel.setObjectName('tablePanel')
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.empty_state = QFrame(panel)
        self.empty_state.setObjectName('emptyState')
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(16, 14, 16, 14)
        empty_layout.setSpacing(3)

        self.empty_title = QLabel('Ready for a package', self.empty_state)
        self.empty_title.setObjectName('emptyTitle')
        self.empty_detail = QLabel('Load a .package, .stbl, XML, JSON, Binary, or generated synthetic smoke package.', self.empty_state)
        self.empty_detail.setObjectName('panelHint')
        self.empty_detail.setWordWrap(True)

        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_detail)

        layout.addWidget(self.empty_state)
        layout.addWidget(self.colorbar)
        layout.addWidget(self.tableview, 1)
        return panel

    def __inspector_panel(self, parent):
        panel = QFrame(parent)
        panel.setObjectName('inspectorPanel')
        panel.setMinimumWidth(286)
        panel.setMaximumWidth(380)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.inspector_title = QLabel('Inspector', panel)
        self.inspector_title.setObjectName('panelTitle')

        self.inspector_meta = QLabel('No string selected', panel)
        self.inspector_meta.setObjectName('panelHint')
        self.inspector_meta.setWordWrap(True)

        self.inspector_status = QLabel('Idle', panel)
        self.inspector_status.setObjectName('inspectorStatus')

        self.inspector_original_label = QLabel('Original', panel)
        self.inspector_original_label.setObjectName('sectionLabel')
        self.inspector_original = QPlainTextEdit(panel)
        self.inspector_original.setObjectName('inspectorText')
        self.inspector_original.setReadOnly(True)

        self.inspector_translation_label = QLabel('Translation draft', panel)
        self.inspector_translation_label.setObjectName('sectionLabel')
        self.inspector_translation = QPlainTextEdit(panel)
        self.inspector_translation.setObjectName('inspectorText')

        self.inspector_comment_label = QLabel('Comment', panel)
        self.inspector_comment_label.setObjectName('sectionLabel')
        self.inspector_comment = QLineEdit(panel)
        self.inspector_comment.setObjectName('inspectorComment')

        self.inspector_apply = QPushButton('Apply + Validate', panel)
        self.inspector_apply.setObjectName('primaryButton')
        self.inspector_reset = QPushButton('Reset', panel)
        self.inspector_edit = QPushButton('Open Editor', panel)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(6)
        button_row.addWidget(self.inspector_reset)
        button_row.addWidget(self.inspector_edit)

        layout.addWidget(self.inspector_title)
        layout.addWidget(self.inspector_meta)
        layout.addWidget(self.inspector_status)
        layout.addWidget(self.inspector_original_label)
        layout.addWidget(self.inspector_original, 1)
        layout.addWidget(self.inspector_translation_label)
        layout.addWidget(self.inspector_translation, 1)
        layout.addWidget(self.inspector_comment_label)
        layout.addWidget(self.inspector_comment)
        layout.addWidget(self.inspector_apply)
        layout.addLayout(button_row)
        layout.addStretch()
        return panel
