# -*- coding: utf-8 -*-

import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QTextOption
from PySide6.QtWidgets import QApplication, QStyleOptionViewItem

from packer.resource import ResourceID
from singletons.config import config
from singletons.interface import interface
from singletons.state import app_state
from storages.dictionaries import DictionariesStorage
from storages.packages import PackagesStorage
from storages.records import MainRecord
from utils.constants import (
    FLAG_PROGRESS,
    FLAG_UNVALIDATED,
    FLAG_VALIDATED,
    RECORD_MAIN_ID,
    RECORD_MAIN_SOURCE,
    RECORD_MAIN_TRANSLATE,
)
from windows.edit_dialog import EditDialog
from windows.main_window import MainWindow
from windows.options_dialog import OptionsDialog
from widgets.delegate import MainDelegatePaint


def app():
    return QApplication.instance() or QApplication([])


def close_widget(widget):
    widget.close()
    widget.deleteLater()
    app().processEvents()


def record(flag=FLAG_PROGRESS):
    rid = ResourceID(group=0, instance=0x1234, type=0x220557DA)
    return MainRecord(
        1,
        42,
        rid.instance,
        rid.group,
        'Hello source',
        'Bonjour draft',
        flag,
        rid,
        rid,
        'sample.package',
        None,
        None,
        (1, 1, 1, 1),
        'Needs review',
    )


class PackageStub:
    key = 'sample.package'
    instances = []
    modified = False

    def __len__(self):
        return 2


class FakeWheelEvent:

    def __init__(self):
        self.ignored = False

    def ignore(self):
        self.ignored = True


class WorkspaceProShellTests(unittest.TestCase):

    def setUp(self):
        app()
        config.set_value('interface', 'language', 'en_US')
        interface.reload()
        config.set_value('translation', 'source', 'ENG_US')
        config.set_value('translation', 'destination', 'FRE_FR')
        app_state.set_packages_storage(PackagesStorage())
        app_state.set_dictionaries_storage(DictionariesStorage())

    def test_main_window_creates_workspace_pro_shell_without_losing_legacy_actions(self):
        window = MainWindow()
        try:
            self.assertEqual(window.project_sidebar.objectName(), 'projectSidebar')
            self.assertEqual(window.project_scroll.objectName(), 'projectSidebarScroll')
            self.assertEqual(window.filter_panel.objectName(), 'filterPanel')
            self.assertIs(window.filter_panel.parent(), window.table_panel)
            self.assertEqual(window.workspace_overview.objectName(), 'workspaceOverview')
            self.assertEqual(window.filter_search.objectName(), 'filterSearch')
            self.assertEqual(window.inspector_panel.objectName(), 'inspectorPanel')
            self.assertEqual(window.inspector_scroll.objectName(), 'inspectorScroll')
            self.assertEqual(window.workspace_splitter.objectName(), 'workspaceSplitter')
            self.assertIs(window.activity_drawer, window.job_drawer)
            self.assertEqual(window.workspace_project_toggle.objectName(), 'workspaceToggle')
            self.assertEqual(window.workspace_inspector_toggle.objectName(), 'workspaceToggle')
            self.assertEqual(window.workspace_activity_toggle.objectName(), 'workspaceToggle')
            self.assertEqual(window.command_file_group.objectName(), 'commandGroup')
            self.assertEqual(window.command_export_group.objectName(), 'commandGroup')
            self.assertEqual(window.command_translation_group.objectName(), 'commandGroup')
            self.assertEqual(window.command_workspace_group.objectName(), 'commandGroup')
            self.assertEqual(window.command_tools_group.objectName(), 'commandGroup')
            self.assertIs(window.filter_search, window.toolbar.edt_search)
            self.assertIs(window.filter_file, window.toolbar.cb_files)
            self.assertIs(window.filter_instance, window.toolbar.cb_instances)
            self.assertIsNot(window.filter_search.parent(), window.toolbar)
            self.assertIs(window.command_open.defaultAction(), window.action_load_file)
            self.assertIs(window.command_translate.defaultAction(), window.action_translate)
            self.assertFalse(window.inspector_apply.isEnabled())
        finally:
            close_widget(window)

    def test_minimum_window_prioritizes_table_and_panel_toggles(self):
        window = MainWindow()
        try:
            window.resize(window.minimumSize())
            window.show()
            app().processEvents()

            self.assertFalse(window.project_sidebar.isVisibleTo(window))
            self.assertFalse(window.inspector_panel.isVisibleTo(window))
            self.assertFalse(window.activity_drawer.isVisibleTo(window))
            self.assertTrue(window.table_panel.isVisibleTo(window))
            self.assertTrue(window.tableview.isVisibleTo(window))
            self.assertTrue(window.workspace_project_toggle.isVisibleTo(window))
            self.assertTrue(window.workspace_inspector_toggle.isVisibleTo(window))
            self.assertTrue(window.workspace_activity_toggle.isVisibleTo(window))
        finally:
            close_widget(window)

    def test_workspace_density_defaults_for_wide_medium_and_small(self):
        window = MainWindow()
        try:
            window.resize(1360, 760)
            window.show()
            app().processEvents()

            self.assertFalse(window.project_sidebar.isVisibleTo(window))
            self.assertFalse(window.inspector_panel.isVisibleTo(window))
            self.assertTrue(window.activity_drawer.isVisibleTo(window))
            self.assertTrue(window.table_panel.isVisibleTo(window))

            window.resize(1640, 820)
            app().processEvents()

            self.assertFalse(window.project_sidebar.isVisibleTo(window))
            self.assertTrue(window.inspector_panel.isVisibleTo(window))
            self.assertTrue(window.activity_drawer.isVisibleTo(window))

            window.resize(window.minimumSize())
            app().processEvents()

            self.assertFalse(window.project_sidebar.isVisibleTo(window))
            self.assertFalse(window.inspector_panel.isVisibleTo(window))
            self.assertFalse(window.activity_drawer.isVisibleTo(window))
            self.assertTrue(window.table_panel.isVisibleTo(window))
        finally:
            close_widget(window)

    def test_workspace_panel_toggles_reopen_collapsed_drawers_without_mutating_records(self):
        window = MainWindow()
        item = record()
        before = list(item)
        try:
            window.update_inspector_item(item)
            window.resize(window.minimumSize())
            window.show()
            app().processEvents()

            window.workspace_project_toggle.setChecked(True)
            app().processEvents()

            self.assertTrue(window.project_sidebar.isVisibleTo(window))
            self.assertFalse(window.inspector_panel.isVisibleTo(window))

            window.workspace_inspector_toggle.setChecked(True)
            app().processEvents()

            self.assertFalse(window.project_sidebar.isVisibleTo(window))
            self.assertTrue(window.inspector_panel.isVisibleTo(window))

            window.workspace_activity_toggle.setChecked(True)
            app().processEvents()

            self.assertTrue(window.activity_drawer.isVisibleTo(window))
            self.assertEqual(list(item), before)
        finally:
            close_widget(window)

    def test_command_bar_switches_to_icon_only_at_minimum_width(self):
        window = MainWindow()
        try:
            window.resize(window.minimumSize())
            window.show()
            app().processEvents()

            self.assertEqual(
                window.command_open.toolButtonStyle(),
                Qt.ToolButtonStyle.ToolButtonIconOnly
            )
            self.assertEqual(
                window.command_options.toolButtonStyle(),
                Qt.ToolButtonStyle.ToolButtonIconOnly
            )

            self.assertEqual(window.brand_title.text(), 'TS4 Translator Plus')
            self.assertFalse(window.command_file_label.isVisibleTo(window))
            self.assertFalse(window.command_workspace_label.isVisibleTo(window))

            window.resize(1500, window.height())
            app().processEvents()

            self.assertEqual(
                window.command_open.toolButtonStyle(),
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )
            self.assertEqual(window.brand_title.text(), 'The Sims 4 Translator Plus')
            self.assertTrue(window.command_file_label.isVisibleTo(window))
            self.assertTrue(window.command_workspace_label.isVisibleTo(window))
        finally:
            close_widget(window)

    def test_table_delegate_uses_dense_professional_row_height(self):
        window = MainWindow()
        try:
            delegate = MainDelegatePaint(window.tableview)
            self.assertEqual(delegate.sizeHint(QStyleOptionViewItem(), QModelIndex()).height(), 38)
        finally:
            close_widget(window)

    def test_large_filter_counts_are_readable_in_table_filter_board(self):
        window = MainWindow()
        items = [record(FLAG_UNVALIDATED) for _ in range(1234)]
        try:
            window.resize(window.minimumSize())
            window.show()
            app().processEvents()
            window.workspace_project_toggle.setChecked(True)
            app().processEvents()
            window._MainWindow__update_filter_counts(items)
            app().processEvents()

            self.assertEqual(window.filter_all.text(), 'All 1,234')
            self.assertEqual(window.filter_original.text(), 'Original 1,234')
            self.assertEqual(window.filter_translated.text(), 'Translated 0')
            self.assertEqual(window._MainWindow__format_filter_count(162527), '162.5k')
            self.assertLessEqual(
                window.filter_all.fontMetrics().horizontalAdvance(window.filter_all.text()) + 24,
                window.filter_all.width()
            )
        finally:
            close_widget(window)

    def test_filter_panel_controls_drive_existing_proxy_without_mutating_records(self):
        window = MainWindow()
        original = record(FLAG_UNVALIDATED)
        validated = record(FLAG_VALIDATED)
        validated[RECORD_MAIN_ID] = 7
        validated[RECORD_MAIN_SOURCE] = 'Done source'
        validated[RECORD_MAIN_TRANSLATE] = 'Done draft'
        before = [list(original), list(validated)]
        try:
            storage = app_state.packages_storage
            storage.packages.append(PackageStub())
            storage.model.replace([original, validated])
            storage.proxy.process_filter()
            window.set_state_menu()

            window.filter_original.setChecked(False)
            window.update_proxy()

            self.assertEqual([item.id for item in storage.model.filtered], [7])
            self.assertEqual([list(original), list(validated)], before)
            self.assertIn('All 2', window.filter_all.text())
            self.assertIn('Original 1', window.filter_original.text())
            self.assertIn('Validated 1', window.filter_validated.text())

            window.clear_filters()
            window.update_proxy()

            self.assertEqual({item.id for item in storage.model.filtered}, {42, 7})
            self.assertTrue(window.filter_original.isChecked())
            self.assertEqual(window.filter_search.text(), '')
        finally:
            close_widget(window)

    def test_package_dropdown_popup_expands_to_show_long_names(self):
        window = MainWindow()
        long_name = '[f3f983e9] very_long_mod_package_name_for_vietnamese_localization_RU.package'
        try:
            window.filter_file.clear()
            window.filter_file.addItems(['-- All files --', long_name])
            window.filter_file.resize(140, window.filter_file.height())
            window.filter_file.update_popup_width()

            self.assertGreater(window.filter_file.view().minimumWidth(), window.filter_file.width())
            self.assertEqual(window.filter_file.itemData(1, Qt.ItemDataRole.ToolTipRole), long_name)
        finally:
            close_widget(window)

    def test_package_and_instance_filters_ignore_mouse_wheel_changes(self):
        window = MainWindow()
        try:
            window.filter_file.clear()
            window.filter_file.addItems(['-- All files --', 'one.package', 'two.package'])
            window.filter_file.setCurrentIndex(1)
            file_event = FakeWheelEvent()

            window.filter_file.wheelEvent(file_event)

            self.assertTrue(file_event.ignored)
            self.assertEqual(window.filter_file.currentIndex(), 1)

            window.filter_instance.clear()
            window.filter_instance.addItems(['-- All instances --', '0x0000000000000001', '0x0000000000000002'])
            window.filter_instance.setCurrentIndex(1)
            instance_event = FakeWheelEvent()

            window.filter_instance.wheelEvent(instance_event)

            self.assertTrue(instance_event.ignored)
            self.assertEqual(window.filter_instance.currentIndex(), 1)
        finally:
            close_widget(window)

    def test_inspector_wraps_and_scrolls_without_overlapping_at_minimum_size(self):
        window = MainWindow()
        item = record()
        long_text = (
            'Mệt mỏi với những căn phòng ngột ngạt? Hãy mang cả thiên nhiên vào nhà! '
            '{0.SimFirstName} đã vượt qua nỗi sợ và đang kiểm tra một chuỗi rất dài. '
        ) * 3
        item[RECORD_MAIN_SOURCE] = long_text
        item[RECORD_MAIN_TRANSLATE] = long_text
        try:
            window.update_inspector_item(item)
            window.resize(window.minimumSize())
            window.show()
            app().processEvents()
            window.workspace_inspector_toggle.setChecked(True)
            app().processEvents()

            self.assertEqual(
                window.inspector_original.wordWrapMode(),
                QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere
            )
            self.assertEqual(
                window.inspector_translation.horizontalScrollBarPolicy(),
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.assertLess(
                window.inspector_original_label.geometry().bottom(),
                window.inspector_original.geometry().top()
            )
            self.assertLess(
                window.inspector_original.geometry().bottom(),
                window.inspector_translation_label.geometry().top()
            )
            self.assertGreaterEqual(window.inspector_scroll.verticalScrollBar().maximum(), 0)
        finally:
            close_widget(window)

    def test_inspector_populates_from_record_without_mutating_it(self):
        window = MainWindow()
        item = record()
        before = list(item)
        try:
            window.update_inspector_item(item)

            self.assertEqual(list(item), before)
            self.assertIn('0x0000002A', window.inspector_meta.text())
            self.assertEqual(window.inspector_original.toPlainText(), 'Hello source')
            self.assertEqual(window.inspector_translation.toPlainText(), 'Bonjour draft')
            self.assertEqual(window.inspector_comment.text(), 'Needs review')
            self.assertTrue(window.inspector_apply.isEnabled())
            self.assertEqual(window.inspector_panel.property('active'), True)
        finally:
            close_widget(window)

    def test_inspector_reset_and_apply_use_existing_record_state(self):
        window = MainWindow()
        item = record()
        try:
            window.update_inspector_item(item)
            window.inspector_translation.setPlainText('Salut')
            window.inspector_comment.setText('Reviewed')
            window.apply_inspector_translation()

            self.assertEqual(item.translate, 'Salut')
            self.assertEqual(item.comment, 'Reviewed')
            self.assertEqual(item.flag, FLAG_VALIDATED)

            window.update_inspector_item(item)
            window.reset_inspector_translation()

            self.assertEqual(item.translate, item.source)
            self.assertEqual(item.flag, FLAG_UNVALIDATED)
        finally:
            close_widget(window)

    def test_edit_dialog_exposes_redesigned_panels_without_losing_core_controls(self):
        dialog = EditDialog()
        try:
            self.assertEqual(dialog.edit_header.objectName(), 'editHeader')
            self.assertEqual(dialog.dictionary_panel.objectName(), 'editPanel')
            self.assertEqual(dialog.original_panel.objectName(), 'editPanel')
            self.assertEqual(dialog.translation_panel.objectName(), 'editPanel')
            self.assertEqual(dialog.edit_footer.objectName(), 'editFooter')
            self.assertTrue(dialog.btn_ok.isDefault())
            self.assertFalse(dialog.btn_translate.autoDefault())
            self.assertFalse(dialog.btn_cancel.autoDefault())
        finally:
            close_widget(dialog)

    def test_options_dialog_hides_theme_selector_for_single_theme_app(self):
        window = MainWindow()
        dialog = OptionsDialog(window)
        try:
            self.assertFalse(hasattr(dialog, 'cb_theme'))
            self.assertFalse(hasattr(dialog, 'lbl_theme'))
            self.assertTrue(hasattr(dialog, 'cb_language'))
            self.assertTrue(hasattr(dialog, 'cb_source'))
            self.assertTrue(hasattr(dialog, 'cb_dest'))
        finally:
            close_widget(dialog)
            close_widget(window)

    def test_options_dialog_defaults_legacy_english_config_to_english_locale(self):
        config.set_value('interface', 'language', 'english')
        interface.reload()
        window = MainWindow()
        dialog = OptionsDialog(window)
        try:
            self.assertEqual(config.value('interface', 'language'), 'en_US')
            self.assertEqual(dialog.cb_language.currentData(), 'en_US')
            self.assertEqual(dialog.cb_language.currentText(), 'English')
        finally:
            close_widget(dialog)
            close_widget(window)


if __name__ == '__main__':
    unittest.main()
