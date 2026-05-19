# -*- coding: utf-8 -*-

from PySide6.QtCore import QMetaObject, Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMenu,
    QMenuBar,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QGridLayout,
    QHBoxLayout,
    QWidget,
    QLineEdit,
    QSizePolicy,
)
from PySide6.QtGui import QAction, QIcon, QTextOption

from widgets.colorbar import QColorBar
from widgets.job_drawer import QJobStatusDrawer
from widgets.tableview import QMainTableView
from widgets.toolbar import QToolBar, FixedLineEdit, FilesComboBox, InstancesComboBox

from utils.constants import APP_NAME, APP_VERSION, APP_RELEASE_CANDITATE


class Ui_MainWindow(object):

    def setupUi(self, MainWindow):
        MainWindow.resize(1280, 760)
        MainWindow.setMinimumSize(900, 600)

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
        self.command_bar.setObjectName('studioHeader')
        command_layout = QHBoxLayout(self.command_bar)
        command_layout.setContentsMargins(14, 10, 14, 10)
        command_layout.setSpacing(12)

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

        self.brand_badge = QLabel('Studio', self.brand_block)
        self.brand_badge.setObjectName('studioBadge')
        brand_layout.addWidget(self.brand_badge)

        self.command_open = self.__command_button(self.action_load_file)
        self.command_save = self.__command_button(self.action_save)
        self.command_import = self.__command_button(self.action_import_translation)

        self.command_export = QToolButton(self.command_bar)
        self.command_export.setObjectName('studioCommandButton')
        self.command_export.setIcon(QIcon(':/images/export.png'))
        self.command_export.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.command_export.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.command_export.setMenu(self.menu_export_translation)
        self.command_export.setEnabled(False)

        self.command_translate = self.__command_button(self.action_translate)
        self.command_dictionary = self.__command_button(self.action_save_dictionary)
        self.workspace_project_toggle = self.__workspace_toggle('Project')
        self.workspace_inspector_toggle = self.__workspace_toggle('Inspector')
        self.workspace_activity_toggle = self.__workspace_toggle('Activity')
        self.command_options = self.__command_button(self.action_options)

        self.command_file_group, self.command_file_label = self.__command_group(
            'File',
            (self.command_open, self.command_save, self.command_import),
        )
        self.command_export_group, self.command_export_label = self.__command_group(
            'Export',
            (self.command_export,),
        )
        self.command_translation_group, self.command_translation_label = self.__command_group(
            'Translation',
            (self.command_translate, self.command_dictionary),
        )
        self.command_workspace_group, self.command_workspace_label = self.__command_group(
            'Workspace',
            (self.workspace_project_toggle, self.workspace_inspector_toggle, self.workspace_activity_toggle),
        )
        self.command_tools_group, self.command_tools_label = self.__command_group(
            'Tools',
            (self.command_options,),
        )

        self.action_hub = QFrame(self.command_bar)
        self.action_hub.setObjectName('studioActionHub')
        action_hub_layout = QHBoxLayout(self.action_hub)
        action_hub_layout.setContentsMargins(0, 0, 0, 0)
        action_hub_layout.setSpacing(8)
        action_hub_layout.addWidget(self.command_file_group)
        action_hub_layout.addWidget(self.command_translation_group)
        action_hub_layout.addWidget(self.command_export_group)
        action_hub_layout.addWidget(self.command_workspace_group)
        action_hub_layout.addStretch()
        action_hub_layout.addWidget(self.command_tools_group)

        command_layout.addWidget(self.brand_block)
        command_layout.addWidget(self.action_hub, 1)

        self.toolbar = QToolBar(MainWindow)
        self.toolbar.setObjectName('filterBar')
        self.toolbar.setOrientation(Qt.Orientation.Vertical)
        self.toolbar.setVisible(False)

        self.filter_search = FixedLineEdit(MainWindow)
        self.filter_search.adjusted_size = 220
        self.filter_search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.filter_search.setObjectName('filterSearch')
        self.filter_file = FilesComboBox(MainWindow)
        self.filter_file.adjusted_size = 260
        self.filter_file.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.filter_file.setObjectName('filterFile')
        self.filter_instance = InstancesComboBox(MainWindow)
        self.filter_instance.adjusted_size = 190
        self.filter_instance.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.filter_instance.setObjectName('filterInstance')
        self.toolbar.edt_search = self.filter_search
        self.toolbar.cb_files = self.filter_file
        self.toolbar.cb_instances = self.filter_instance

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
        button.setObjectName('studioCommandButton')
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        return button

    def __command_divider(self):
        divider = QFrame(self.command_bar)
        divider.setObjectName('commandDivider')
        return divider

    def __command_group(self, label, widgets):
        group = QFrame(self.command_bar)
        group.setObjectName('studioActionGroup')
        group_layout = QHBoxLayout(group)
        group_layout.setContentsMargins(8, 5, 8, 5)
        group_layout.setSpacing(7)

        text = QLabel(label, group)
        text.setObjectName('studioGroupLabel')
        text.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        for widget in widgets:
            row.addWidget(widget)
        group_layout.addWidget(text)
        group_layout.addLayout(row)
        return group, text

    def __workspace_toggle(self, text):
        button = QToolButton(self.command_bar)
        button.setObjectName('studioWorkspaceToggle')
        button.setText(text)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setCheckable(True)
        button.setChecked(True)
        return button

    def __project_sidebar(self, parent):
        sidebar = QFrame(parent)
        sidebar.setObjectName('projectSidebar')
        sidebar.setMinimumWidth(220)
        sidebar.setMaximumWidth(300)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.project_scroll = QScrollArea(sidebar)
        self.project_scroll.setObjectName('projectSidebarScroll')
        self.project_scroll.setWidgetResizable(True)
        self.project_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.project_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QFrame(self.project_scroll)
        content.setObjectName('projectSidebarContent')
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(10)

        self.project_title = QLabel('Project Rail', content)
        self.project_title.setObjectName('panelTitle')

        self.project_summary = QLabel('No package loaded', content)
        self.project_summary.setObjectName('projectSummary')
        self.project_summary.setWordWrap(True)

        self.project_hint = QLabel('Open a package or synthetic smoke file to begin translating.', content)
        self.project_hint.setObjectName('panelHint')
        self.project_hint.setWordWrap(True)
        self.project_hint.setMinimumHeight(56)

        content_layout.addWidget(self.project_title)
        content_layout.addWidget(self.project_summary)
        content_layout.addWidget(self.project_hint)
        content_layout.addStretch()

        self.project_scroll.setWidget(content)
        layout.addWidget(self.project_scroll)
        return sidebar

    def __filter_chip(self, text):
        button = QPushButton(text)
        button.setObjectName('filterChip')
        button.setCheckable(True)
        button.setChecked(True)
        button.setAutoDefault(False)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return button

    def __table_panel(self, parent):
        panel = QFrame(parent)
        panel.setObjectName('tablePanel')
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)

        self.workspace_overview = QFrame(panel)
        self.workspace_overview.setObjectName('workspaceOverview')
        overview_layout = QHBoxLayout(self.workspace_overview)
        overview_layout.setContentsMargins(12, 9, 12, 9)
        overview_layout.setSpacing(10)

        self.workspace_summary = QLabel('No package loaded', self.workspace_overview)
        self.workspace_summary.setObjectName('workspaceSummary')
        self.workspace_summary.setWordWrap(True)
        self.workspace_summary.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.workspace_hint = QLabel('Table-first workspace', self.workspace_overview)
        self.workspace_hint.setObjectName('workspaceHint')

        overview_layout.addWidget(self.workspace_summary, 1)
        overview_layout.addWidget(self.workspace_hint)

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

        self.filter_panel = self.__filter_board(panel)

        layout.addWidget(self.workspace_overview)
        layout.addWidget(self.filter_panel)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.colorbar)
        layout.addWidget(self.tableview, 1)
        return panel

    def __filter_board(self, parent):
        board = QFrame(parent)
        board.setObjectName('studioFilterTray')
        board.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        layout = QGridLayout(board)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setHorizontalSpacing(9)
        layout.setVerticalSpacing(7)
        layout.setColumnStretch(2, 2)
        layout.setColumnStretch(3, 2)
        layout.setColumnStretch(5, 1)
        layout.setColumnStretch(6, 1)

        self.filter_title = QLabel('Filters', board)
        self.filter_title.setObjectName('panelTitle')
        self.filter_hint = QLabel('Search, status and scope stay close to the table.', board)
        self.filter_hint.setObjectName('panelHint')
        self.filter_hint.setWordWrap(True)
        self.filter_hint.setVisible(False)

        self.filter_search_label = QLabel('Search', board)
        self.filter_search_label.setObjectName('sectionLabel')
        self.filter_search_mode = QPushButton('Original', board)
        self.filter_search_mode.setObjectName('filterModeButton')
        self.filter_search_mode.setAutoDefault(False)

        self.filter_status_label = QLabel('Status', board)
        self.filter_status_label.setObjectName('sectionLabel')
        self.filter_all = self.__filter_chip('All')
        self.filter_original = self.__filter_chip('Original')
        self.filter_translated = self.__filter_chip('Translated')
        self.filter_validated = self.__filter_chip('Validated')
        self.filter_progress = self.__filter_chip('In progress')
        self.filter_different = self.__filter_chip('Changed')
        self.filter_different.setChecked(False)

        self.filter_scope_label = QLabel('Scope', board)
        self.filter_scope_label.setObjectName('sectionLabel')
        self.filter_file_label = QLabel('Package', board)
        self.filter_file_label.setObjectName('fieldLabel')
        self.filter_instance_label = QLabel('Instance', board)
        self.filter_instance_label.setObjectName('fieldLabel')

        self.filter_clear = QPushButton('Clear filters', board)
        self.filter_clear.setObjectName('secondaryButton')
        self.filter_clear.setAutoDefault(False)

        layout.addWidget(self.filter_title, 0, 0)
        layout.addWidget(self.filter_search_label, 0, 1)
        layout.addWidget(self.filter_search, 0, 2, 1, 2)
        layout.addWidget(self.filter_search_mode, 0, 4)
        layout.addWidget(self.filter_clear, 0, 6)
        layout.addWidget(self.filter_status_label, 1, 0)
        layout.addWidget(self.filter_all, 1, 1, 1, 2)
        layout.addWidget(self.filter_original, 1, 3, 1, 2)
        layout.addWidget(self.filter_translated, 1, 5, 1, 2)
        layout.addWidget(self.filter_validated, 2, 1, 1, 2)
        layout.addWidget(self.filter_progress, 2, 3, 1, 2)
        layout.addWidget(self.filter_different, 2, 5, 1, 2)
        layout.addWidget(self.filter_scope_label, 3, 0)
        layout.addWidget(self.filter_file_label, 3, 1)
        layout.addWidget(self.filter_file, 3, 2, 1, 2)
        layout.addWidget(self.filter_instance_label, 3, 4)
        layout.addWidget(self.filter_instance, 3, 5, 1, 2)

        return board

    def __inspector_panel(self, parent):
        panel = QFrame(parent)
        panel.setObjectName('focusEditor')
        panel.setMinimumWidth(300)
        panel.setMaximumWidth(430)
        self.focus_editor_panel = panel
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.inspector_scroll = QScrollArea(panel)
        self.inspector_scroll.setObjectName('inspectorScroll')
        self.inspector_scroll.setWidgetResizable(True)
        self.inspector_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.inspector_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QFrame(self.inspector_scroll)
        content.setObjectName('inspectorContent')
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(8)

        self.inspector_title = QLabel('Focus Editor', content)
        self.inspector_title.setObjectName('panelTitle')

        self.inspector_meta = QLabel('No string selected', content)
        self.inspector_meta.setObjectName('panelHint')
        self.inspector_meta.setWordWrap(True)

        self.inspector_empty = QLabel('Select a string in the table to edit its translation here.', content)
        self.inspector_empty.setObjectName('emptyHint')
        self.inspector_empty.setWordWrap(True)

        self.inspector_status = QLabel('Idle', content)
        self.inspector_status.setObjectName('inspectorStatus')

        self.inspector_original_label = QLabel('Original', content)
        self.inspector_original_label.setObjectName('sectionLabel')
        self.inspector_original = QPlainTextEdit(content)
        self.inspector_original.setObjectName('inspectorText')
        self.inspector_original.setReadOnly(True)
        self.inspector_original.setMinimumHeight(130)

        self.inspector_translation_label = QLabel('Translation draft', content)
        self.inspector_translation_label.setObjectName('sectionLabel')
        self.inspector_translation = QPlainTextEdit(content)
        self.inspector_translation.setObjectName('inspectorText')
        self.inspector_translation.setMinimumHeight(150)

        for editor in (self.inspector_original, self.inspector_translation):
            editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
            editor.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
            editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.inspector_comment_label = QLabel('Comment', content)
        self.inspector_comment_label.setObjectName('sectionLabel')
        self.inspector_comment = QLineEdit(content)
        self.inspector_comment.setObjectName('inspectorComment')

        self.inspector_apply = QPushButton('Apply + Validate', content)
        self.inspector_apply.setObjectName('primaryButton')
        self.inspector_reset = QPushButton('Reset', content)
        self.inspector_edit = QPushButton('Open Editor', content)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(6)
        button_row.addWidget(self.inspector_reset)
        button_row.addWidget(self.inspector_edit)

        content_layout.addWidget(self.inspector_title)
        content_layout.addWidget(self.inspector_meta)
        content_layout.addWidget(self.inspector_empty)
        content_layout.addWidget(self.inspector_status)
        content_layout.addWidget(self.inspector_original_label)
        content_layout.addWidget(self.inspector_original)
        content_layout.addWidget(self.inspector_translation_label)
        content_layout.addWidget(self.inspector_translation)
        content_layout.addWidget(self.inspector_comment_label)
        content_layout.addWidget(self.inspector_comment)
        content_layout.addWidget(self.inspector_apply)
        content_layout.addLayout(button_row)
        content_layout.addStretch()

        self.inspector_scroll.setWidget(content)
        layout.addWidget(self.inspector_scroll)
        return panel
