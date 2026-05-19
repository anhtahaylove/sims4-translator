# -*- coding: utf-8 -*-

import sys
import pyperclip
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import QApplication, QMainWindow, QMenu, QMessageBox
from PySide6.QtGui import QAction, QIcon

from .ui.main_window import Ui_MainWindow

from .edit_dialog import EditDialog
from .options_dialog import OptionsDialog
from .replace_dialog import ReplaceDialog
from .export_dialog import ExportDialog
from .import_dialog import ImportDialog
from .translate_dialog import TranslateDialog

from singletons.config import config
from singletons.interface import interface
from singletons.signals import progress_signals, window_signals
from singletons.state import app_state
from singletons.undo import undo
from utils.functions import open_supported, open_xml, save_package, save_xml, text_to_edit, text_to_stbl
from utils.constants import *


INSPECTOR_STATUS = {
    FLAG_UNVALIDATED: 'Original',
    FLAG_PROGRESS: 'In progress',
    FLAG_VALIDATED: 'Validated',
    FLAG_TRANSLATED: 'Translated',
    FLAG_REPLACED: 'Edited',
}


class ColumnAction(QAction):

    def __init__(self, parent=None, text=None, index=0) -> None:
        super().__init__(parent)

        self.main_window = parent

        self.setCheckable(True)

        self.__text = text
        self.__index = index

        name = self.config_name
        self.__checked = config.value('view', name) if name else False

        self.setChecked(self.__checked)

        self.triggered.connect(self.clicked)

    def retranslate(self):
        self.setText(interface.text('MainTableView', self.__text))

    @property
    def config_name(self):
        if self.__index == COLUMN_MAIN_ID:
            return 'id'
        elif self.__index == COLUMN_MAIN_INSTANCE:
            return 'instance'
        elif self.__index == COLUMN_MAIN_GROUP:
            return 'group'
        elif self.__index == COLUMN_MAIN_SOURCE:
            return 'source'
        elif self.__index == COLUMN_MAIN_COMMENT:
            return 'comment'
        return None

    def clicked(self):
        self.__checked = not self.__checked
        self.setChecked(self.__checked)
        self.main_window.tableview.setColumnHidden(self.__index, not self.__checked)
        name = self.config_name
        if name:
            config.set_value('view', name, self.__checked)


class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.__set_window_title()

        self.setAcceptDrops(True)
        self.__workspace_density = None
        self.__workspace_panels_updating = False

        self.tableview.doubleClicked.connect(self.edit_string)
        self.tableview.customContextMenuRequested.connect(self.generate_item_context_menu)

        self.action_load_file.triggered.connect(self.load_file)
        self.action_add_file.triggered.connect(self.add_file)
        self.action_save.triggered.connect(self.save)
        self.action_save_as.triggered.connect(self.save_as)
        self.action_finalize.triggered.connect(self.finalize)
        self.action_finalize_as.triggered.connect(self.finalize_as)
        self.action_load_bundle.triggered.connect(self.load_bundle)
        self.action_save_bundle.triggered.connect(self.save_bundle)
        self.action_import_translation.triggered.connect(self.import_translation)
        self.action_export_stbl.triggered.connect(self.export_translation_stbl)
        self.action_export_xml.triggered.connect(self.export_translation_xml)
        self.action_export_xml_dp.triggered.connect(self.export_translation_xml_dp)
        self.action_export_json_s4s.triggered.connect(self.export_translation_json_s4s)
        self.action_export_binary_s4s.triggered.connect(self.export_translation_binary_s4s)
        self.action_export_translation_hub_csv.triggered.connect(self.export_translation_hub_csv)
        self.action_save_dictionary.triggered.connect(self.save_dictionary)
        self.action_close.triggered.connect(self.close_package)
        self.action_exit.triggered.connect(sys.exit)

        self.action_replace.triggered.connect(self.replace)
        self.action_translate_from_dictionaries.triggered.connect(self.translate_from_dict)
        self.action_validate_all_translations.triggered.connect(self.validate_2_all)
        self.action_reset_all_translations.triggered.connect(self.validate_0_all)
        self.action_translate.triggered.connect(self.batch_translate)
        self.action_undo.triggered.connect(self.undo_restore)

        self.action_colorbar.triggered.connect(self.colorbar_toggle)
        self.action_colorbar.setChecked(config.value('view', 'colorbar'))

        self.action_options.triggered.connect(self.options)
        self.action_group_original.triggered.connect(self.group_original)
        self.action_group_highbit.triggered.connect(self.group_highbit)
        self.action_group_lowbit.triggered.connect(self.group_lowbit)

        self.action_group_original.setChecked(config.value('group', 'original'))
        self.action_group_highbit.setChecked(config.value('group', 'highbit'))
        self.action_group_lowbit.setChecked(config.value('group', 'lowbit'))

        self.action_about_qt.triggered.connect(self.about_qt)
        self.action_about_app = QAction(self)
        self.action_about_app.triggered.connect(self.about_app)
        self.menu_help.insertAction(self.action_about_qt, self.action_about_app)
        self.menu_help.insertSeparator(self.action_about_qt)

        self.action_num_standart.triggered.connect(self.num_standart)
        self.action_num_source.triggered.connect(self.num_source)
        self.action_num_xml_dp.triggered.connect(self.num_xml_dp)

        self.toolbar.search_toggle.triggered.connect(self.search_toggle)
        self.toolbar.filter_validate_0.triggered.connect(self.filter_timer_trigger)
        self.toolbar.filter_validate_1.triggered.connect(self.filter_timer_trigger)
        self.toolbar.filter_validate_2.triggered.connect(self.filter_timer_trigger)
        self.toolbar.filter_validate_3.triggered.connect(self.filter_timer_trigger)
        self.toolbar.filter_validate_4.triggered.connect(self.filter_timer_trigger)
        self.toolbar.edt_search.textChanged.connect(self.search_timer_trigger)
        self.toolbar.cb_files.currentIndexChanged.connect(self.change_file)
        self.toolbar.cb_instances.currentIndexChanged.connect(self.change_instance)
        self.filter_search_mode.clicked.connect(lambda _checked=False: self.search_toggle())
        self.filter_all.clicked.connect(lambda _checked=False: self.clear_status_filters())
        self.filter_original.toggled.connect(
            lambda checked: self.__filter_chip_toggled(self.toolbar.filter_validate_0, checked)
        )
        self.filter_progress.toggled.connect(
            lambda checked: self.__filter_chip_toggled(self.toolbar.filter_validate_1, checked)
        )
        self.filter_validated.toggled.connect(
            lambda checked: self.__filter_chip_toggled(self.toolbar.filter_validate_2, checked)
        )
        self.filter_translated.toggled.connect(
            lambda checked: self.__filter_chip_toggled(self.toolbar.filter_validate_3, checked)
        )
        self.filter_different.toggled.connect(
            lambda checked: self.__filter_chip_toggled(self.toolbar.filter_validate_4, checked)
        )
        self.filter_clear.clicked.connect(lambda _checked=False: self.clear_filters())
        self.workspace_project_toggle.toggled.connect(
            lambda checked: self.__workspace_panel_toggled('project', checked)
        )
        self.workspace_inspector_toggle.toggled.connect(
            lambda checked: self.__workspace_panel_toggled('inspector', checked)
        )
        self.workspace_activity_toggle.toggled.connect(
            lambda checked: self.__workspace_panel_toggled('activity', checked)
        )

        self.__search_flag = SEARCH_IN_SOURCE
        self.__sync_search_mode_label()
        self.__sync_filter_chips()
        self.__apply_workspace_density(force=True)

        self.edit_dialog = EditDialog()
        self.replace_dialog = ReplaceDialog()
        self.export_dialog = ExportDialog(self)
        self.import_dialog = ImportDialog()
        self.translate_dialog = TranslateDialog()

        self.tableview.set_model()
        self.edit_dialog.tableview.set_model()
        self.__inspector_item = None
        self.tableview.selectionModel().selectionChanged.connect(self.__selection_changed)
        self.inspector_apply.clicked.connect(self.apply_inspector_translation)
        self.inspector_reset.clicked.connect(self.reset_inspector_translation)
        self.inspector_edit.clicked.connect(self.edit_string)
        self.update_inspector_item(None)

        self.num_change()

        self.action_column = [
            ColumnAction(self, 'ID', COLUMN_MAIN_ID),
            ColumnAction(self, 'Instance', COLUMN_MAIN_INSTANCE),
            ColumnAction(self, 'Group', COLUMN_MAIN_GROUP),
            ColumnAction(self, 'Original', COLUMN_MAIN_SOURCE),
            ColumnAction(self, 'Comment', COLUMN_MAIN_COMMENT),
        ]

        for col in self.action_column:
            self.menu_view.insertAction(self.action_insert, col)
        self.menu_view.insertSeparator(self.action_insert)

        self.menu_view.removeAction(self.action_insert)
        self.action_insert = None

        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self.update_proxy)

        progress_signals.initiate.connect(self.__initiate_progress)
        progress_signals.increment.connect(self.__increment_progress)
        progress_signals.finished.connect(self.__finished_progress)

        window_signals.message.connect(self.__message)
        window_signals.log.connect(self.job_drawer.log_message)

        undo.signals.updated.connect(self.__undo_updated)
        undo.signals.restored.connect(self.__undo_restored)

        app_state.packages_storage.signals.loaded.connect(self.__packages_loaded)
        app_state.packages_storage.signals.closed.connect(self.__packages_closed)
        app_state.packages_storage.signals.cleared.connect(self.__packages_cleared)

        self.retranslate()

    def retranslate(self):
        self.action_load_file.setText(interface.text('MainWindow', 'Load file...'))
        self.action_save_as.setText(interface.text('MainWindow', 'Save as...'))
        self.action_close.setText(interface.text('MainWindow', 'Close'))
        self.action_save.setText(interface.text('MainWindow', 'Save'))
        self.action_save_dictionary.setText(interface.text('MainWindow', 'Save dictionary'))
        self.action_replace.setText(interface.text('MainWindow', 'Search and replace...'))
        self.action_validate_all_translations.setText(interface.text('MainWindow', 'Validate all translations'))
        self.action_reset_all_translations.setText(interface.text('MainWindow', 'Reset all translations'))
        self.action_exit.setText(interface.text('MainWindow', 'Exit'))
        self.action_add_file.setText(interface.text('MainWindow', 'Add file...'))
        self.action_undo.setText(interface.text('MainWindow', 'Undo'))
        self.action_about_qt.setText(interface.text('MainWindow', 'About Qt...'))
        self.action_about_app.setText(f'About {APP_NAME}...')
        self.action_options.setText(interface.text('MainWindow', 'Options...'))
        self.action_export_xml.setText(interface.text('MainWindow', 'To XML...'))
        self.action_translate_from_dictionaries.setText(interface.text('MainWindow', 'Translate from dictionaries'))
        self.action_translate.setText(interface.text('MainWindow', 'Batch translate...'))
        self.action_finalize.setText(interface.text('MainWindow', 'Finalize package'))
        self.action_finalize_as.setText(interface.text('MainWindow', 'Finalize package as...'))
        self.action_export_xml_dp.setText(interface.text('MainWindow', 'To XML (Deaderpool\'s STBL editor)...'))
        self.action_export_json_s4s.setText(interface.text('MainWindow', 'To JSON (Sims 4 Studio format)...'))
        self.action_export_binary_s4s.setText(interface.text('MainWindow', 'To Binary (Sims 4 Studio format)...'))
        self.action_export_translation_hub_csv.setText('Sims 4 Translation Hub CSV (*.csv)')
        self.action_group_original.setText(interface.text('MainWindow', 'Use original group'))
        self.action_group_highbit.setText(interface.text('MainWindow', 'Use high-bit'))
        self.action_export_stbl.setText(interface.text('MainWindow', 'To STBL...'))
        self.action_group_lowbit.setText(interface.text('MainWindow', 'Use low-bit'))
        self.action_import_translation.setText(interface.text('MainWindow', 'Import translation...'))
        self.action_save_bundle.setText(interface.text('MainWindow', 'Save bundle...'))
        self.action_load_bundle.setText(interface.text('MainWindow', 'Load bundle...'))
        self.action_num_standart.setText(interface.text('MainWindow', 'Standart'))
        self.action_num_source.setText(interface.text('MainWindow', 'From the source file'))
        self.action_num_xml.setText(interface.text('MainWindow', 'XML format'))
        self.action_num_xml_dp.setText(interface.text('MainWindow', 'XML format (Deaderpool\'s STBL editor)'))
        self.action_colorbar.setText(interface.text('MainWindow', 'Color visualization'))
        self.menu_file.setTitle(interface.text('MainWindow', 'File'))
        self.menu_export_translation.setTitle(interface.text('MainWindow', 'Export translation'))
        self.command_export.setText(interface.text('MainWindow', 'Export'))
        self.command_export.setToolTip(interface.text('MainWindow', 'Export translation'))
        self.menu_translation.setTitle(interface.text('MainWindow', 'Translation'))
        self.menu_view.setTitle(interface.text('MainWindow', 'View'))
        self.menu_numeration.setTitle(interface.text('MainWindow', 'Numeration'))
        self.menu_options.setTitle(interface.text('MainWindow', 'Options'))
        self.menu_group.setTitle(interface.text('MainWindow', 'Group'))
        self.menu_help.setTitle(interface.text('MainWindow', 'Help'))
        self.brand_title.setText(APP_NAME)
        self.brand_subtitle.setText('Mod localization workspace')
        self.project_title.setText('Project Rail')
        self.filter_title.setText('Studio Filters')
        self.filter_hint.setText('Search, status and scope stay close to the table.')
        self.filter_search_label.setText('Search')
        self.filter_status_label.setText('Status')
        self.filter_scope_label.setText('Scope')
        self.filter_file_label.setText('Package')
        self.filter_instance_label.setText('Instance')
        self.filter_clear.setText('Clear filters')
        self.workspace_hint.setText('Translation table')
        self.empty_title.setText('Ready for a package')
        self.empty_detail.setText('Load a .package, .stbl, XML, JSON, Binary, or generated synthetic smoke package.')
        self.inspector_title.setText('Focus Editor')
        self.inspector_original_label.setText('Original')
        self.inspector_translation_label.setText('Translation draft')
        self.inspector_comment_label.setText('Comment')
        self.inspector_apply.setText('Apply + Validate')
        self.inspector_reset.setText('Reset')
        self.inspector_edit.setText('Open Editor')
        self.workspace_project_toggle.setText('Project')
        self.workspace_project_toggle.setToolTip('Show or hide the Project and Filters panel')
        self.workspace_inspector_toggle.setText('Inspector')
        self.workspace_inspector_toggle.setToolTip('Show or hide the selected string Inspector')
        self.workspace_activity_toggle.setText('Activity')
        self.workspace_activity_toggle.setToolTip('Show or hide background jobs and logs')
        self.command_file_label.setText('File')
        self.command_export_label.setText('Export')
        self.command_translation_label.setText('Translation')
        self.command_workspace_label.setText('Workspace')
        self.command_tools_label.setText('Tools')

        for col in self.action_column:
            col.retranslate()

        self.update_workspace_summary()
        self.__sync_search_mode_label()
        self.__update_command_bar_density()
        self.__apply_workspace_density(force=True)

    def __set_window_title(self):
        title = f'{APP_NAME} {APP_VERSION}'
        if APP_RELEASE_CANDITATE:
            title += ' RC'
        self.setWindowTitle(title)

    def showEvent(self, event):
        app_state.set_tableview(self.tableview)
        app_state.set_monospace(self.monospace)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.__update_command_bar_density()
        self.__apply_workspace_density()

    def __update_command_bar_density(self):
        if not hasattr(self, 'command_open'):
            return

        compact = self.width() < 1440
        style = (
            Qt.ToolButtonStyle.ToolButtonIconOnly
            if compact else Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        for button in (
                self.command_open,
                self.command_save,
                self.command_import,
                self.command_export,
                self.command_translate,
                self.command_dictionary,
                self.command_options,
        ):
            button.setToolButtonStyle(style)

        self.brand_title.setText('TS4 Translator Plus' if compact else APP_NAME)
        self.brand_subtitle.setVisible(not compact)
        self.brand_badge.setVisible(not compact)
        for label in (
                self.command_file_label,
                self.command_export_label,
                self.command_translation_label,
                self.command_workspace_label,
                self.command_tools_label,
        ):
            label.setVisible(not compact)

    def __apply_workspace_density(self, force=False):
        if not hasattr(self, 'workspace_project_toggle'):
            return

        density = self.__workspace_density_for_width(self.width())
        if force or density != getattr(self, '_MainWindow__workspace_density', None):
            self.__workspace_density = density
            project, inspector, activity = self.__workspace_density_defaults(density)
            self.__set_workspace_toggle(self.workspace_project_toggle, project)
            self.__set_workspace_toggle(self.workspace_inspector_toggle, inspector)
            self.__set_workspace_toggle(self.workspace_activity_toggle, activity)

        self.__sync_workspace_panels()

    @staticmethod
    def __workspace_density_for_width(width):
        if width >= 1560:
            return 'wide'
        if width >= 1180:
            return 'medium'
        return 'small'

    @staticmethod
    def __workspace_density_defaults(density):
        if density == 'wide':
            return False, True, True
        if density == 'medium':
            return False, False, False
        return False, False, False

    def __set_workspace_toggle(self, button, checked):
        button.blockSignals(True)
        button.setChecked(checked)
        button.blockSignals(False)

    def __workspace_panel_toggled(self, panel, checked):
        if self.__workspace_panels_updating:
            return

        if self.__workspace_density == 'small' and checked:
            if panel == 'project':
                self.__set_workspace_toggle(self.workspace_inspector_toggle, False)
            elif panel == 'inspector':
                self.__set_workspace_toggle(self.workspace_project_toggle, False)

        self.__sync_workspace_panels()

    def __sync_workspace_panels(self):
        self.__workspace_panels_updating = True

        project_visible = self.workspace_project_toggle.isChecked()
        inspector_visible = self.workspace_inspector_toggle.isChecked()
        activity_visible = self.workspace_activity_toggle.isChecked()

        if self.__workspace_density == 'small' and project_visible and inspector_visible:
            inspector_visible = False
            self.__set_workspace_toggle(self.workspace_inspector_toggle, False)

        self.project_sidebar.setVisible(project_visible)
        self.inspector_panel.setVisible(inspector_visible)
        self.activity_drawer.setVisible(activity_visible)

        if self.__workspace_density == 'wide':
            sizes = [255 if project_visible else 0, 1200, 390 if inspector_visible else 0]
        elif self.__workspace_density == 'medium':
            sizes = [240 if project_visible else 0, 1120, 360 if inspector_visible else 0]
        else:
            sizes = [220 if project_visible else 0, 900, 330 if inspector_visible else 0]

        self.workspace_splitter.setSizes(sizes)
        self.command_bar.setProperty('density', self.__workspace_density)
        self.command_bar.style().unpolish(self.command_bar)
        self.command_bar.style().polish(self.command_bar)
        self.command_bar.update()

        self.__workspace_panels_updating = False

    def dragEnterEvent(self, event):
        event.setAccepted(False)
        filename = event.mimeData().text().lower()
        if filename.endswith('.package') or filename.endswith('.stbl') or filename.endswith('.xml') or filename.endswith('.json') or filename.endswith('.binary'):
            event.setAccepted(True)

    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        self.load(event.mimeData().text().replace('file:///', ''))

    def closeEvent(self, event):
        if self.check_modified(True):
            config.save()
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F1:
            if event.modifiers() and Qt.KeyboardModifier.ControlModifier:
                self.validate_2_all()
            else:
                self.validate_2()

        elif event.key() == Qt.Key.Key_F2:
            self.validate_1()

        elif event.key() == Qt.Key.Key_F4:
            if event.modifiers() and Qt.KeyboardModifier.ControlModifier:
                self.validate_0_all()
            else:
                self.validate_0()

        elif event.key() == Qt.Key.Key_C and event.modifiers() and Qt.KeyboardModifier.ControlModifier:
            self.copy()

        elif event.key() == Qt.Key.Key_V and event.modifiers() and Qt.KeyboardModifier.ControlModifier:
            self.paste()

        elif event.key() in [Qt.Key.Key_Enter, Qt.Key.Key_Return]:
            self.edit_string()

        elif event.key() == Qt.Key.Key_O and event.modifiers() and Qt.KeyboardModifier.ControlModifier:
            self.open_file()

        elif event.key() == Qt.Key.Key_S and event.modifiers() and Qt.KeyboardModifier.ControlModifier:
            self.save()

        elif event.key() == Qt.Key.Key_R and event.modifiers() and Qt.KeyboardModifier.ControlModifier:
            self.replace()

        elif event.key() == Qt.Key.Key_Z and event.modifiers() and Qt.KeyboardModifier.ControlModifier:
            self.undo_restore()

        elif event.key() == Qt.Key.Key_T and event.modifiers() and Qt.KeyboardModifier.ControlModifier:
            self.translate()

        else:
            super().keyPressEvent(event)

    def search_toggle(self):
        if self.__search_flag == SEARCH_IN_SOURCE:
            self.__search_flag = SEARCH_IN_DESTINATION
            self.toolbar.search_toggle.setIcon(QIcon(':/images/search_dest.png'))
            self.toolbar.search_toggle.setToolTip(interface.text('ToolBar', 'Search in translation'))
        elif self.__search_flag == SEARCH_IN_DESTINATION:
            self.__search_flag = SEARCH_IN_ID
            self.toolbar.search_toggle.setIcon(QIcon(':/images/search_id.png'))
            self.toolbar.search_toggle.setToolTip(interface.text('ToolBar', 'Search in ID'))
        else:
            self.__search_flag = SEARCH_IN_SOURCE
            self.toolbar.search_toggle.setIcon(QIcon(':/images/search_source.png'))
            self.toolbar.search_toggle.setToolTip(interface.text('ToolBar', 'Search in original'))

        if self.toolbar.edt_search.text():
            self.filter_timer_trigger()
        self.__sync_search_mode_label()

    def __sync_search_mode_label(self):
        if self.__search_flag == SEARCH_IN_SOURCE:
            text = 'Original'
            tooltip = interface.text('ToolBar', 'Search in original')
        elif self.__search_flag == SEARCH_IN_DESTINATION:
            text = 'Translation'
            tooltip = interface.text('ToolBar', 'Search in translation')
        else:
            text = 'ID'
            tooltip = interface.text('ToolBar', 'Search in ID')

        self.filter_search_mode.setText(text)
        self.filter_search_mode.setToolTip(tooltip)

    def update_current_file(self):
        key = None
        if self.toolbar.cb_files.currentIndex() > 0:
            key = self.toolbar.cb_files.currentText()
        elif self.toolbar.cb_files.count() == 2:
            key = self.toolbar.cb_files.itemText(1)
        app_state.set_current_package(key)

    def update_current_instance(self):
        instance = None
        if self.toolbar.cb_instances.currentIndex() > 0:
            instance = self.toolbar.cb_instances.currentText()
        elif self.toolbar.cb_instances.count() == 2:
            instance = self.toolbar.cb_instances.itemText(1)
        app_state.set_current_instance(int(instance, 16) if instance else 0)

    def build_instances_list(self):
        self.toolbar.cb_instances.blockSignals(True)
        self.toolbar.cb_instances.clear()
        self.toolbar.cb_instances.addItem(interface.text('ToolBar', '-- All instances --'))
        if app_state.current_package:
            package = app_state.packages_storage.find(app_state.current_package)
            if package:
                self.toolbar.cb_instances.addItems(package.instances)
        self.toolbar.cb_instances.blockSignals(False)

    def change_file(self):
        self.update_current_file()
        self.build_instances_list()
        self.update_current_instance()
        self.colorbar.resfesh()
        self.filter_timer_trigger()

    def change_instance(self):
        self.update_current_instance()
        self.colorbar.resfesh()
        self.filter_timer_trigger()

    def search_timer_trigger(self):
        self.filter_timer.start(250)

    def filter_timer_trigger(self):
        self.filter_timer.start(90)

    def clear_status_filters(self):
        for action in (
                self.toolbar.filter_validate_0,
                self.toolbar.filter_validate_1,
                self.toolbar.filter_validate_2,
                self.toolbar.filter_validate_3,
        ):
            action.setChecked(True)
        self.toolbar.filter_validate_4.setChecked(False)
        self.__sync_filter_chips()
        self.filter_timer_trigger()

    def clear_filters(self):
        self.toolbar.edt_search.clear()
        self.toolbar.cb_files.setCurrentIndex(0)
        self.toolbar.cb_instances.setCurrentIndex(0)
        self.clear_status_filters()

    def __filter_chip_toggled(self, action, checked):
        if action.isChecked() != checked:
            action.setChecked(checked)
        self.__sync_filter_chips()
        self.filter_timer_trigger()

    def __sync_filter_chips(self):
        pairs = (
            (self.filter_original, self.toolbar.filter_validate_0),
            (self.filter_progress, self.toolbar.filter_validate_1),
            (self.filter_validated, self.toolbar.filter_validate_2),
            (self.filter_translated, self.toolbar.filter_validate_3),
            (self.filter_different, self.toolbar.filter_validate_4),
        )
        for button, action in pairs:
            button.blockSignals(True)
            button.setChecked(action.isChecked())
            button.blockSignals(False)

        all_statuses = all(action.isChecked() for _, action in pairs[:4]) and not self.toolbar.filter_validate_4.isChecked()
        self.filter_all.blockSignals(True)
        self.filter_all.setChecked(all_statuses)
        self.filter_all.blockSignals(False)

    def update_proxy(self):
        flags = []
        if not self.toolbar.filter_validate_0.isChecked():
            flags.append(FLAG_UNVALIDATED)
        if not self.toolbar.filter_validate_1.isChecked():
            flags.append(FLAG_PROGRESS)
            flags.append(FLAG_REPLACED)
        if not self.toolbar.filter_validate_2.isChecked():
            flags.append(FLAG_VALIDATED)
        if not self.toolbar.filter_validate_3.isChecked():
            flags.append(FLAG_TRANSLATED)

        cb_instances = self.toolbar.cb_instances
        cb_files = self.toolbar.cb_files
        storage = app_state.packages_storage
        storage.proxy.filter(package=cb_files.currentText() if cb_files.currentIndex() > 0 else None,
                             instance=cb_instances.currentText() if cb_instances.currentIndex() > 0 else 0,
                             text=self.toolbar.edt_search.text(),
                             mode=self.__search_flag,
                             flags=flags,
                             different=self.toolbar.filter_validate_4.isChecked())
        self.update_workspace_summary()

    def set_state_menu(self):
        state = app_state.packages_storage.enabled

        self.action_import_translation.setEnabled(state)
        self.menu_export_translation.setEnabled(state)
        self.command_export.setEnabled(state)

        self.action_add_file.setEnabled(state)
        self.action_save.setEnabled(state)
        self.action_save_as.setEnabled(state)
        self.action_save_bundle.setEnabled(app_state.packages_storage.multiplied)
        self.action_save_dictionary.setEnabled(state)
        self.action_close.setEnabled(state)
        self.action_replace.setEnabled(state)
        self.action_translate_from_dictionaries.setEnabled(state)
        self.action_validate_all_translations.setEnabled(state)
        self.action_reset_all_translations.setEnabled(state)
        self.action_translate.setEnabled(state)

        self.action_finalize.setEnabled(state and not app_state.packages_storage.multiplied)
        self.action_finalize_as.setEnabled(state and not app_state.packages_storage.multiplied)

        self.colorbar.resfesh()
        self.colorbar.setVisible(config.value('view', 'colorbar') and state)
        self.empty_state.setVisible(not state)
        self.update_workspace_summary()
        if not state:
            self.update_inspector_item(None)

    def check_modified(self, multi: bool = False):
        package = app_state.packages_storage.current_package
        if multi and app_state.packages_storage.modified or not multi and package and package.modified:
            flags = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel

            response = QMessageBox.question(self,
                                            self.windowTitle(),
                                            interface.text('Messages', 'Save dictionary for modified packages?'),
                                            flags,
                                            QMessageBox.StandardButton.NoButton)

            if response == QMessageBox.StandardButton.Yes:
                app_state.dictionaries_storage.save(multi=multi)

            return response != QMessageBox.StandardButton.Cancel

        return True

    @staticmethod
    def load(filename: str, added: bool = False):
        if filename:
            def load_package():
                app_state.packages_storage.load(filename, added, asynchronous=True)

            if not app_state.dictionaries_storage.loaded:
                handle = app_state.dictionaries_storage.load(asynchronous=True)
                handle.result.connect(lambda _result: load_package())
            else:
                load_package()

    def open_file(self, added: bool = False):
        filename = open_supported(True)
        if filename:
            self.load(filename, added)

    def load_file(self):
        self.open_file()

    def add_file(self):
        self.open_file(True)

    def import_translation(self):
        filename = open_supported()
        if filename:
            found = False

            if filename.lower().endswith('.xml'):
                found = app_state.packages_storage.check_xml(filename)
            elif filename.lower().endswith('.stbl'):
                found = app_state.packages_storage.check_stbl(filename)
            elif filename.lower().endswith('.package'):
                found = app_state.packages_storage.check_package(filename)
            elif filename.lower().endswith('.json'):
                found = app_state.packages_storage.check_json(filename)
            elif filename.lower().endswith('.binary'):
                found = app_state.packages_storage.check_binary(filename)

            if found:
                self.import_dialog.filename = filename
                self.import_dialog.exec()
            else:
                QMessageBox.information(self, self.windowTitle(),
                                        interface.text('Messages', 'Not found text records in this file!'))

    def export_translation_stbl(self):
        self.export_dialog.stbl()

    def export_translation_xml(self):
        self.export_dialog.xml()

    def export_translation_xml_dp(self):
        self.export_dialog.xml_dp()

    def export_translation_json_s4s(self):
        self.export_dialog.json_s4s()

    def export_translation_binary_s4s(self):
        self.export_dialog.binary_s4s()

    def export_translation_hub_csv(self):
        self.export_dialog.translation_hub_csv()

    def translate_from_dict(self):
        for item in app_state.packages_storage.items():
            if item.flag == FLAG_UNVALIDATED:
                translated = app_state.dictionaries_storage.search(source=item.source)
                if translated:
                    undo.wrap(item)
                    item.translate = translated[0]
                    item.flag = FLAG_PROGRESS if len(translated) > 1 else FLAG_TRANSLATED

        self.colorbar.resfesh()
        self.tableview.refresh()
        self.update_workspace_summary()

        undo.commit()

    def batch_translate(self):
        self.translate_dialog.exec()

    def translate(self):
        self.translate_dialog.translate_selection()

    @staticmethod
    def save_dictionary():
        app_state.dictionaries_storage.save(force=True)

    def save(self):
        package = app_state.packages_storage.current_package
        if package:
            package.save()
        else:
            self.save_as()

    @staticmethod
    def save_as():
        package = app_state.packages_storage.current_package
        filename = save_package(
            package.filename if package else 'translate_merged_' + config.value('translation',
                                                                                'destination'))
        if filename:
            app_state.packages_storage.save(filename)

    @staticmethod
    def finalize():
        package = app_state.packages_storage.current_package
        if package:
            package.finalize()

    @staticmethod
    def finalize_as():
        package = app_state.packages_storage.current_package
        if package:
            filename = save_package(package.name)
            if filename:
                package.finalize(filename)

    @staticmethod
    def load_bundle():
        filename = open_xml()
        if filename:
            def load_packages():
                app_state.packages_storage.load_bundle(filename, asynchronous=True)

            if not app_state.dictionaries_storage.loaded:
                handle = app_state.dictionaries_storage.load(asynchronous=True)
                handle.result.connect(lambda _result: load_packages())
            else:
                load_packages()

    @staticmethod
    def save_bundle():
        filename = save_xml('packages_bundle')
        if filename:
            app_state.packages_storage.save_bundle(filename)

    def edit_string(self):
        item = self.tableview.selected_item()
        if item:
            self.edit_dialog.prepare(item)
            self.edit_dialog.exec()
            self.update_inspector_item(item)

    def validate_selected(self, flag):
        if not app_state.packages_storage.enabled:
            return

        items = self.tableview.selected_items()
        for item in items:
            undo.wrap(item)
            item.flag = flag
            item.translate_old = None
            if flag == FLAG_UNVALIDATED:
                item.translate = item.source

        self.colorbar.resfesh()
        self.tableview.refresh()
        self.update_workspace_summary()
        self.update_inspector_item(self.tableview.selected_item())

        undo.commit()

    def validate_all(self, flag):
        if not app_state.packages_storage.enabled:
            return

        for item in app_state.packages_storage.items():
            undo.wrap(item)
            item.flag = flag
            item.translate_old = None
            if flag == FLAG_UNVALIDATED:
                item.translate = item.source

        self.colorbar.resfesh()
        self.tableview.refresh()
        self.update_workspace_summary()
        self.update_inspector_item(self.tableview.selected_item())

        undo.commit()

    def validate_0(self):
        self.validate_selected(FLAG_UNVALIDATED)

    def validate_0_all(self):
        self.validate_all(FLAG_UNVALIDATED)

    def validate_1(self):
        self.validate_selected(FLAG_PROGRESS)

    def validate_2(self):
        self.validate_selected(FLAG_VALIDATED)

    def validate_2_all(self):
        self.validate_all(FLAG_VALIDATED)

    def copy(self):
        item = self.tableview.selected_item()
        if item:
            pyperclip.copy(item.translate)

    def paste(self):
        if not app_state.packages_storage.enabled:
            return

        paste = pyperclip.paste()
        for item in self.tableview.selected_items():
            undo.wrap(item)
            item.translate = paste
            item.translate_old = None
            item.flag = FLAG_VALIDATED

        self.colorbar.resfesh()
        self.tableview.refresh()
        self.update_workspace_summary()
        self.update_inspector_item(self.tableview.selected_item())

        undo.commit()

    def close_package(self):
        package = app_state.current_package
        if self.check_modified(package is None):
            app_state.packages_storage.close()

    def replace(self):
        if app_state.packages_storage.enabled:
            self.replace_dialog.exec()

    def options(self):
        dlg = OptionsDialog(self)
        dlg.exec()
        dlg.deleteLater()

    def colorbar_toggle(self):
        config.set_value('view', 'colorbar', self.action_colorbar.isChecked())
        self.colorbar.setVisible(config.value('view', 'colorbar') and app_state.packages_storage.enabled)

    @Slot()
    def __selection_changed(self):
        self.update_inspector_item(self.tableview.selected_item())

    def update_workspace_summary(self):
        storage = app_state.packages_storage
        if not storage or not storage.enabled:
            self.project_summary.setText('No package loaded')
            self.workspace_summary.setText('No package loaded')
            self.project_hint.setText(
                'Project details appear here after loading a file. Filters stay above the table.'
            )
            self.workspace_hint.setText('Open or drop a package to begin')
            self.__update_filter_counts(())
            return

        items = list(storage.items())
        total = len(items)
        visible = len(storage.model.filtered)
        validated = sum(1 for item in items if item.flag == FLAG_VALIDATED)
        translated = sum(1 for item in items if item.flag == FLAG_TRANSLATED)
        progress = sum(1 for item in items if item.flag in (FLAG_PROGRESS, FLAG_REPLACED))
        original = sum(1 for item in items if item.flag == FLAG_UNVALIDATED)
        package_count = len(getattr(storage, 'packages', []))

        summary_text = (
            f'{visible}/{total} shown | {package_count} package(s)\n'
            f'{validated} valid | {translated} translated\n'
            f'{progress} progress | {original} original'
        )
        self.project_summary.setText(summary_text)
        self.workspace_summary.setText(
            f'{visible}/{total} shown    {package_count} package(s)    '
            f'{validated} valid    {translated} translated    {progress} progress    {original} original'
        )
        self.project_hint.setText('Select a row to edit it in the Inspector.')
        self.workspace_hint.setText('Use filters above, edit selected rows in Inspector')
        self.__update_filter_counts(items)

    def __update_filter_counts(self, items):
        items = tuple(items)
        counts = {
            'all': len(items),
            'original': sum(1 for item in items if item.flag == FLAG_UNVALIDATED),
            'translated': sum(1 for item in items if item.flag == FLAG_TRANSLATED),
            'validated': sum(1 for item in items if item.flag == FLAG_VALIDATED),
            'progress': sum(1 for item in items if item.flag in (FLAG_PROGRESS, FLAG_REPLACED)),
            'different': sum(1 for item in items if item.source_old or item.translate_old),
        }
        labels = (
            (self.filter_all, 'All', counts['all']),
            (self.filter_original, 'Original', counts['original']),
            (self.filter_translated, 'Translated', counts['translated']),
            (self.filter_validated, 'Validated', counts['validated']),
            (self.filter_progress, 'In progress', counts['progress']),
            (self.filter_different, 'Changed', counts['different']),
        )
        for button, label, value in labels:
            button.setText(f'{label} {self.__format_filter_count(value)}')
            button.setToolTip(f'{label}: {value:,}')

    @staticmethod
    def __format_filter_count(value):
        if value >= 100000:
            return f'{value / 1000:.1f}k'
        if value >= 10000:
            return f'{value // 1000}k'
        return f'{value:,}'

    def update_inspector_item(self, item):
        self.__inspector_item = item
        enabled = item is not None

        self.inspector_panel.setProperty('active', enabled)
        self.inspector_apply.setEnabled(enabled)
        self.inspector_reset.setEnabled(enabled)
        self.inspector_edit.setEnabled(enabled)
        self.inspector_translation.setEnabled(enabled)
        self.inspector_comment.setEnabled(enabled)
        self.inspector_empty.setVisible(not enabled)
        self.inspector_status.setVisible(enabled)
        self.inspector_original_label.setVisible(enabled)
        self.inspector_original.setVisible(enabled)
        self.inspector_translation_label.setVisible(enabled)
        self.inspector_translation.setVisible(enabled)
        self.inspector_comment_label.setVisible(enabled)
        self.inspector_comment.setVisible(enabled)

        if not enabled:
            self.inspector_meta.setText('No string selected')
            self.inspector_status.setText('Idle')
            self.inspector_status.setProperty('state', 'idle')
            self.inspector_original.setPlainText('')
            self.inspector_translation.setPlainText('')
            self.inspector_comment.setText('')
            self.__refresh_inspector_status_style()
            return

        self.inspector_meta.setText(f'Selected string\n{item.id_hex} | {item.instance_hex}')
        self.inspector_status.setText(INSPECTOR_STATUS.get(item.flag, 'Unknown'))
        self.inspector_status.setProperty('state', str(item.flag))
        self.inspector_original.setPlainText(text_to_edit(item.source))
        self.inspector_translation.setPlainText(text_to_edit(item.translate))
        self.inspector_comment.setText(item.comment)
        self.__refresh_inspector_status_style()

    def apply_inspector_translation(self):
        item = self.__inspector_item
        if item is None:
            return

        wrapped = self.__wrap_for_undo(item)
        item.translate = text_to_stbl(self.inspector_translation.toPlainText())
        item.comment = self.inspector_comment.text()
        item.translate_old = None
        item.flag = FLAG_VALIDATED
        if wrapped:
            undo.commit()
        self.__sync_after_inspector_change(item)

    def reset_inspector_translation(self):
        item = self.__inspector_item
        if item is None:
            return

        wrapped = self.__wrap_for_undo(item)
        item.translate = item.source
        item.translate_old = None
        item.flag = FLAG_UNVALIDATED
        if wrapped:
            undo.commit()
        self.__sync_after_inspector_change(item)

    def __sync_after_inspector_change(self, item):
        if app_state.packages_storage.enabled and hasattr(app_state.dictionaries_storage, 'update'):
            app_state.dictionaries_storage.update(item)
        self.colorbar.resfesh()
        self.tableview.refresh()
        self.update_workspace_summary()
        self.update_inspector_item(item)

    @staticmethod
    def __wrap_for_undo(item):
        storage = app_state.packages_storage
        package = storage.find(item.package) if storage and item.package else None
        if package:
            undo.wrap(item)
            return True
        return False

    def __refresh_inspector_status_style(self):
        self.inspector_status.style().unpolish(self.inspector_status)
        self.inspector_status.style().polish(self.inspector_status)
        self.inspector_status.update()
        self.inspector_panel.style().unpolish(self.inspector_panel)
        self.inspector_panel.style().polish(self.inspector_panel)
        self.inspector_panel.update()

    def group_change(self):
        self.action_group_original.setChecked(config.value('group', 'original'))
        self.action_group_highbit.setChecked(config.value('group', 'highbit'))
        self.action_group_lowbit.setChecked(config.value('group', 'lowbit'))

        for item in app_state.packages_storage.model.items:
            rid = item[RECORD_MAIN_RESOURCE_ORIGINAL]
            if not config.group_original:
                rid = item[RECORD_MAIN_RESOURCE_ORIGINAL].convert_group(highbit=config.group_high)
            item[RECORD_MAIN_GROUP] = rid.group
            item[RECORD_MAIN_RESOURCE] = rid

    def group_original(self):
        config.set_value('group', 'original', True)
        config.set_value('group', 'highbit', False)
        config.set_value('group', 'lowbit', False)
        self.group_change()

    def group_highbit(self):
        config.set_value('group', 'original', False)
        config.set_value('group', 'highbit', True)
        config.set_value('group', 'lowbit', False)
        self.group_change()

    def group_lowbit(self):
        config.set_value('group', 'original', False)
        config.set_value('group', 'highbit', False)
        config.set_value('group', 'lowbit', True)
        self.group_change()

    def num_change(self):
        numeration = config.value('view', 'numeration')
        self.action_num_standart.setChecked(numeration == NUMERATION_STANDART)
        self.action_num_source.setChecked(numeration == NUMERATION_SOURCE)
        self.action_num_xml_dp.setChecked(numeration == NUMERATION_XML_DP)
        self.tableview.refresh()

    def num_standart(self):
        config.set_value('view', 'numeration', NUMERATION_STANDART)
        self.num_change()

    def num_source(self):
        config.set_value('view', 'numeration', NUMERATION_SOURCE)
        self.num_change()

    def num_xml(self):
        config.set_value('view', 'numeration', NUMERATION_XML)
        self.num_change()

    def num_xml_dp(self):
        config.set_value('view', 'numeration', NUMERATION_XML_DP)
        self.num_change()

    @staticmethod
    def undo_restore():
        undo.restore()

    @staticmethod
    def about_qt():
        QApplication.instance().aboutQt()

    def about_app(self):
        text = (
            f'<h2>{APP_NAME}</h2>'
            f'<p>Version {APP_VERSION}</p>'
            '<p>A community-maintained fork focused on faster package workflows, '
            'dedupe-safe exports, and a clearer translation workspace.</p>'
            f'<p>Fork: <a href="{APP_FORK_URL}">{APP_FORK_URL}</a><br>'
            f'Upstream: <a href="{APP_UPSTREAM_URL}">{APP_UPSTREAM_URL}</a></p>'
            f'<p>License: {APP_LICENSE}</p>'
            f'<p><small>{APP_DISCLAIMER}</small></p>'
        )
        QMessageBox.about(self, f'About {APP_NAME}', text)

    def generate_item_context_menu(self, position):
        index = self.sender().indexAt(position)
        if not index.isValid():
            return

        position.setY(position.y() + 22)

        context_menu = QMenu()

        edit_action = context_menu.addAction(QIcon(':/images/edit.png'), interface.text('MainWindow', 'Edit String'))
        edit_action.setShortcut('Enter')

        context_menu.addSeparator()

        validate_2_action = context_menu.addAction(QIcon(':/images/validate_2.png'),
                                                   interface.text('MainWindow', 'Validate as [translated]'))
        validate_2_action.setShortcut('F1')

        validate_1_action = context_menu.addAction(QIcon(':/images/validate_1.png'),
                                                   interface.text('MainWindow', 'Validate as [work in progress]'))
        validate_1_action.setShortcut('F2')

        validate_0_action = context_menu.addAction(QIcon(':/images/validate_0.png'),
                                                   interface.text('MainWindow', 'Cancel translation'))
        validate_0_action.setShortcut('F4')

        context_menu.addSeparator()

        copy_action = context_menu.addAction(QIcon(':/images/copy.png'), interface.text('MainWindow', 'Copy'))
        copy_action.setShortcut('Ctrl+C')

        paste_action = context_menu.addAction(QIcon(':/images/paste.png'), interface.text('MainWindow', 'Paste'))
        paste_action.setShortcut('Ctrl+V')

        context_menu.addSeparator()

        translate_action = context_menu.addAction(QIcon(':/images/api.png'), interface.text('MainWindow', 'Translate'))
        translate_action.setShortcut('Ctrl+T')

        action = context_menu.exec_(self.sender().mapToGlobal(position))
        if action is None:
            return

        if action == edit_action:
            self.edit_string()

        if action == copy_action:
            self.copy()

        if action == paste_action:
            self.paste()

        if action == translate_action:
            self.translate()

        if action == validate_2_action:
            self.validate_2()

        if action == validate_1_action:
            self.validate_1()

        if action == validate_0_action:
            self.validate_0()

    @Slot(str)
    def __message(self, text: str):
        self.job_drawer.log_message(text)
        QMessageBox.information(self, self.windowTitle(), text)

    @Slot(str, int)
    def __initiate_progress(self, message: str, value: int):
        self.job_drawer.start_legacy(message, value)

    @Slot()
    def __increment_progress(self):
        self.job_drawer.increment_legacy()

    @Slot()
    def __finished_progress(self):
        self.job_drawer.finish_legacy()

    @Slot()
    def __undo_updated(self):
        self.action_undo.setEnabled(undo.available)

    @Slot()
    def __undo_restored(self):
        self.action_undo.setEnabled(undo.available)
        self.colorbar.resfesh()
        self.tableview.refresh()

    @Slot(list)
    def __packages_loaded(self, keys: list):
        self.toolbar.cb_files.blockSignals(True)
        self.toolbar.cb_files.addItems(keys)
        if len(keys) == 1:
            self.toolbar.cb_files.setCurrentIndex(self.toolbar.cb_files.count() - 1)
        self.toolbar.cb_files.blockSignals(False)

        self.update_current_file()
        self.build_instances_list()
        self.update_current_instance()

        self.filter_timer.start()

        self.set_state_menu()

    @Slot(str)
    def __packages_closed(self, key: str):
        self.toolbar.cb_files.blockSignals(True)
        self.toolbar.cb_files.removeItem(self.toolbar.cb_files.findText(key))
        self.toolbar.cb_files.setCurrentIndex(0)
        self.toolbar.cb_files.blockSignals(False)

        self.update_current_file()
        self.build_instances_list()
        self.update_current_instance()

        self.filter_timer.start()

        self.set_state_menu()

    @Slot()
    def __packages_cleared(self):
        self.toolbar.cb_files.blockSignals(True)
        self.toolbar.cb_files.clear()
        self.toolbar.cb_files.addItem(interface.text('ToolBar', '-- All files --'))
        self.toolbar.cb_files.setCurrentIndex(0)
        self.toolbar.cb_files.blockSignals(False)

        self.toolbar.cb_instances.blockSignals(True)
        self.toolbar.cb_instances.clear()
        self.toolbar.cb_instances.addItem(interface.text('ToolBar', '-- All instances --'))
        self.toolbar.cb_instances.setCurrentIndex(0)
        self.toolbar.cb_instances.blockSignals(False)

        self.update_current_file()
        self.update_current_instance()

        self.filter_timer.start()

        self.set_state_menu()
