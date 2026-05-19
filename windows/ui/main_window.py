# -*- coding: utf-8 -*-

from PySide6.QtCore import QMetaObject, Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMenu,
    QMenuBar,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QGridLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QWidget,
    QLineEdit,
    QSizePolicy,
)
from PySide6.QtGui import QAction, QIcon

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
        self.action_activity_dock = QAction(MainWindow)
        self.action_activity_dock.setCheckable(True)

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
        self.menu_view.addAction(self.action_activity_dock)
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
        self.command_layout = QHBoxLayout(self.command_bar)
        self.command_layout.setContentsMargins(14, 10, 14, 10)
        self.command_layout.setSpacing(12)

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
        self.command_export.setMinimumWidth(94)

        self.command_translate = self.__command_button(self.action_translate)
        self.command_dictionary = self.__command_button(self.action_save_dictionary)

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

        self.action_hub = QFrame(self.command_bar)
        self.action_hub.setObjectName('studioActionHub')
        self.action_hub_layout = QHBoxLayout(self.action_hub)
        self.action_hub_layout.setContentsMargins(0, 0, 0, 0)
        self.action_hub_layout.setSpacing(8)
        self.action_hub_layout.addWidget(self.command_file_group)
        self.action_hub_layout.addWidget(self.command_translation_group)
        self.action_hub_layout.addWidget(self.command_export_group)
        self.action_hub_layout.addStretch()

        self.command_layout.addWidget(self.brand_block)
        self.command_layout.addWidget(self.action_hub, 1)

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

        self.central_layout = QVBoxLayout(centralwidget)
        self.central_layout.setContentsMargins(8, 8, 8, 8)
        self.central_layout.setSpacing(8)
        self.central_layout.addWidget(self.command_bar)

        self.table_panel = self.__table_panel(MainWindow)
        self.central_layout.addWidget(self.table_panel, 1)

        self.monospace = QLineEdit(MainWindow)
        self.monospace.setObjectName('monospace')
        self.monospace.setVisible(False)

        self.central_layout.addWidget(self.monospace)
        self.central_layout.addWidget(self.activity_drawer)

        QMetaObject.connectSlotsByName(MainWindow)

    def __command_button(self, action):
        button = QToolButton(self.command_bar)
        button.setObjectName('studioCommandButton')
        button.setIcon(action.icon())
        button.setEnabled(action.isEnabled())
        button.clicked.connect(action.trigger)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setMinimumWidth(82)
        action.changed.connect(lambda action=action, button=button: self.__sync_command_button(button, action))
        return button

    @staticmethod
    def __sync_command_button(button, action):
        button.setIcon(action.icon())
        button.setEnabled(action.isEnabled())
        label = button.property('commandLabel')
        button.setText(label if label else action.text())
        button.setToolTip(action.text())

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
        self.table_panel_layout = QVBoxLayout(panel)
        self.table_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.table_panel_layout.setSpacing(7)

        self.workspace_overview = QFrame(panel)
        self.workspace_overview.setObjectName('workspaceOverview')
        self.workspace_overview_layout = QHBoxLayout(self.workspace_overview)
        self.workspace_overview_layout.setContentsMargins(12, 9, 12, 9)
        self.workspace_overview_layout.setSpacing(10)

        self.workspace_summary = QLabel('No package loaded', self.workspace_overview)
        self.workspace_summary.setObjectName('workspaceSummary')
        self.workspace_summary.setWordWrap(True)
        self.workspace_summary.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.workspace_hint = QLabel('Table-first workspace', self.workspace_overview)
        self.workspace_hint.setObjectName('workspaceHint')

        self.workspace_overview_layout.addWidget(self.workspace_summary, 1)
        self.workspace_overview_layout.addWidget(self.workspace_hint)

        self.empty_state = QFrame(panel)
        self.empty_state.setObjectName('emptyState')
        self.empty_layout = QVBoxLayout(self.empty_state)
        self.empty_layout.setContentsMargins(16, 14, 16, 14)
        self.empty_layout.setSpacing(3)

        self.empty_title = QLabel('Ready for a package', self.empty_state)
        self.empty_title.setObjectName('emptyTitle')
        self.empty_detail = QLabel('Load a .package, .stbl, XML, JSON, Binary, or generated synthetic smoke package.', self.empty_state)
        self.empty_detail.setObjectName('panelHint')
        self.empty_detail.setWordWrap(True)

        self.empty_layout.addWidget(self.empty_title)
        self.empty_layout.addWidget(self.empty_detail)

        self.filter_panel = self.__filter_board(panel)
        self.selection_bar = self.__selection_bar(panel)

        self.table_panel_layout.addWidget(self.workspace_overview)
        self.table_panel_layout.addWidget(self.filter_panel)
        self.table_panel_layout.addWidget(self.empty_state)
        self.table_panel_layout.addWidget(self.selection_bar)
        self.table_panel_layout.addWidget(self.colorbar)
        self.table_panel_layout.addWidget(self.tableview, 1)
        return panel

    def __selection_bar(self, parent):
        bar = QFrame(parent)
        bar.setObjectName('selectionBar')
        self.selection_layout = QVBoxLayout(bar)
        self.selection_layout.setContentsMargins(12, 8, 12, 8)
        self.selection_layout.setSpacing(7)

        self.selection_header = QFrame(bar)
        self.selection_header.setObjectName('selectionPreviewHeader')
        self.selection_header_layout = QHBoxLayout(self.selection_header)
        self.selection_header_layout.setContentsMargins(0, 0, 0, 0)
        self.selection_header_layout.setSpacing(10)

        self.selection_meta = QLabel('No string selected', bar)
        self.selection_meta.setObjectName('selectionMeta')
        self.selection_meta.setWordWrap(True)
        self.selection_meta.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.selection_status = QLabel('Idle', bar)
        self.selection_status.setObjectName('selectionStatus')
        self.selection_status.setMinimumWidth(92)
        self.selection_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.selection_validate = QPushButton('Validate', bar)
        self.selection_validate.setObjectName('primaryButton')
        self.selection_reset = QPushButton('Reset', bar)
        self.selection_reset.setObjectName('secondaryButton')
        self.selection_edit = QPushButton('Open Editor', bar)
        self.selection_edit.setObjectName('secondaryButton')
        self.selection_preview_toggle = QPushButton('Collapse preview', bar)
        self.selection_preview_toggle.setObjectName('secondaryButton')
        self.selection_preview_toggle.setAutoDefault(False)

        self.selection_header_layout.addWidget(self.selection_meta, 1)
        self.selection_header_layout.addWidget(self.selection_status)
        self.selection_header_layout.addWidget(self.selection_preview_toggle)
        self.selection_header_layout.addWidget(self.selection_validate)
        self.selection_header_layout.addWidget(self.selection_reset)
        self.selection_header_layout.addWidget(self.selection_edit)

        self.selection_preview = QFrame(bar)
        self.selection_preview.setObjectName('selectionPreview')
        self.selection_preview_layout = QHBoxLayout(self.selection_preview)
        self.selection_preview_layout.setContentsMargins(0, 0, 0, 0)
        self.selection_preview_layout.setSpacing(8)

        self.selection_original_panel = self.__preview_panel('Original', bar)
        self.selection_translation_panel = self.__preview_panel('Translated', bar)
        self.selection_preview_layout.addWidget(self.selection_original_panel, 1)
        self.selection_preview_layout.addWidget(self.selection_translation_panel, 1)

        self.selection_layout.addWidget(self.selection_header)
        self.selection_layout.addWidget(self.selection_preview)

        self.inspector_meta = self.selection_meta
        self.inspector_status = self.selection_status
        self.inspector_apply = self.selection_validate
        self.inspector_reset = self.selection_reset
        self.inspector_edit = self.selection_edit
        return bar

    def __preview_panel(self, title, parent):
        panel = QFrame(parent)
        panel.setObjectName('selectionPreviewPanel')
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label = QLabel(title, panel)
        label.setObjectName('fieldLabel')

        text = QPlainTextEdit(panel)
        text.setObjectName('selectionPreviewText')
        text.setReadOnly(True)
        text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        text.setMaximumHeight(92)
        text.setPlaceholderText('Select a string to preview full text.')

        layout.addWidget(label)
        layout.addWidget(text)

        if title == 'Original':
            self.selection_original_text = text
        else:
            self.selection_translation_text = text

        return panel

    def __filter_board(self, parent):
        board = QFrame(parent)
        board.setObjectName('studioFilterTray')
        board.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.filter_layout = QGridLayout(board)
        self.filter_layout.setContentsMargins(12, 9, 12, 9)
        self.filter_layout.setHorizontalSpacing(9)
        self.filter_layout.setVerticalSpacing(7)
        self.filter_layout.setColumnStretch(2, 2)
        self.filter_layout.setColumnStretch(3, 2)
        self.filter_layout.setColumnStretch(5, 1)
        self.filter_layout.setColumnStretch(6, 1)

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

        self.filter_layout.addWidget(self.filter_title, 0, 0)
        self.filter_layout.addWidget(self.filter_search_label, 0, 1)
        self.filter_layout.addWidget(self.filter_search, 0, 2, 1, 2)
        self.filter_layout.addWidget(self.filter_search_mode, 0, 4)
        self.filter_layout.addWidget(self.filter_clear, 0, 6)
        self.filter_layout.addWidget(self.filter_status_label, 1, 0)
        self.filter_layout.addWidget(self.filter_all, 1, 1, 1, 2)
        self.filter_layout.addWidget(self.filter_original, 1, 3, 1, 2)
        self.filter_layout.addWidget(self.filter_translated, 1, 5, 1, 2)
        self.filter_layout.addWidget(self.filter_validated, 2, 1, 1, 2)
        self.filter_layout.addWidget(self.filter_progress, 2, 3, 1, 2)
        self.filter_layout.addWidget(self.filter_different, 2, 5, 1, 2)
        self.filter_layout.addWidget(self.filter_scope_label, 3, 0)
        self.filter_layout.addWidget(self.filter_file_label, 3, 1)
        self.filter_layout.addWidget(self.filter_file, 3, 2, 1, 2)
        self.filter_layout.addWidget(self.filter_instance_label, 3, 4)
        self.filter_layout.addWidget(self.filter_instance, 3, 5, 1, 2)

        return board
