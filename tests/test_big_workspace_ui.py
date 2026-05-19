# -*- coding: utf-8 -*-

import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QApplication, QStyleOptionViewItem

import themes.balanced as balanced
from packer.resource import ResourceID
from singletons.config import config
from singletons.interface import interface
from singletons.state import app_state
from storages.dictionaries import DictionariesStorage
from storages.packages import PackagesStorage
from storages.records import MainRecord
from utils.constants import (
    FLAG_PROGRESS,
    FLAG_REPLACED,
    FLAG_TRANSLATED,
    FLAG_UNVALIDATED,
    FLAG_VALIDATED,
    RECORD_MAIN_ID,
    RECORD_MAIN_SOURCE,
    RECORD_MAIN_TRANSLATE,
)
from windows.edit_dialog import EditDialog
from windows.export_dialog import ExportDialog
from windows.import_dialog import ImportDialog
from windows.main_window import MainWindow
from windows.options_dialog import OptionsDialog
from windows.translate_dialog import TranslateDialog
from widgets.delegate import MainDelegatePaint, STATUS_META


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


def hex_to_rgb(value):
    value = value.lstrip('#')
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def relative_luminance(value):
    channels = []
    for channel in hex_to_rgb(value):
        if channel <= 0.03928:
            channels.append(channel / 12.92)
        else:
            channels.append(((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(foreground, background):
    foreground_luminance = relative_luminance(foreground)
    background_luminance = relative_luminance(background)
    lighter = max(foreground_luminance, background_luminance)
    darker = min(foreground_luminance, background_luminance)
    return (lighter + 0.05) / (darker + 0.05)


class WorkspaceProShellTests(unittest.TestCase):

    def setUp(self):
        app()
        config.set_value('interface', 'language', 'en_US')
        interface.reload()
        config.set_value('translation', 'source', 'ENG_US')
        config.set_value('translation', 'destination', 'FRE_FR')
        config.set_value('view', 'activity_visible', True)
        config.set_value('view', 'activity_expanded', True)
        app_state.set_packages_storage(PackagesStorage())
        app_state.set_dictionaries_storage(DictionariesStorage())

    def test_main_window_creates_workspace_pro_shell_without_losing_legacy_actions(self):
        window = MainWindow()
        try:
            self.assertEqual(window.command_bar.objectName(), 'studioHeader')
            self.assertEqual(window.action_hub.objectName(), 'studioActionHub')
            self.assertEqual(window.filter_panel.objectName(), 'studioFilterTray')
            self.assertIs(window.filter_panel.parent(), window.workspace_overview)
            self.assertGreater(
                window.workspace_overview_layout.indexOf(window.filter_panel),
                window.workspace_overview_layout.indexOf(window.workspace_summary_block),
            )
            self.assertEqual(window.selection_bar.objectName(), 'selectionBar')
            self.assertEqual(window.workspace_overview.objectName(), 'workspaceOverview')
            self.assertEqual(window.filter_search.objectName(), 'filterSearch')
            self.assertEqual(window.filter_search_mode.text(), 'Hybrid')
            self.assertIn('ID', window.filter_search.placeholderText())
            self.assertIs(window.activity_drawer, window.job_drawer)
            self.assertTrue(window.action_activity_dock.isCheckable())
            self.assertIn(window.action_activity_dock, window.menu_view.actions())
            self.assertEqual(window.command_file_group.objectName(), 'studioActionGroup')
            self.assertEqual(window.command_export_group.objectName(), 'studioActionGroup')
            self.assertEqual(window.command_translation_group.objectName(), 'studioActionGroup')
            self.assertEqual(window.selection_preview.objectName(), 'selectionPreview')
            self.assertFalse(hasattr(window, 'project_sidebar'))
            self.assertFalse(hasattr(window, 'inspector_panel'))
            self.assertFalse(hasattr(window, 'workspace_splitter'))
            self.assertFalse(hasattr(window, 'workspace_project_toggle'))
            self.assertFalse(hasattr(window, 'workspace_inspector_toggle'))
            self.assertFalse(hasattr(window, 'workspace_activity_toggle'))
            self.assertFalse(hasattr(window, 'command_options'))
            self.assertFalse(hasattr(window, 'command_activity_group'))
            self.assertFalse(hasattr(window, 'command_tools_group'))
            self.assertIs(window.filter_search, window.toolbar.edt_search)
            self.assertIs(window.filter_file, window.toolbar.cb_files)
            self.assertIs(window.filter_instance, window.toolbar.cb_instances)
            self.assertIsNot(window.filter_search.parent(), window.toolbar)
            self.assertEqual(window.command_open.property('commandLabel'), 'Open')
            self.assertEqual(window.command_translate.property('commandLabel'), 'Translate')
            self.assertFalse(window.inspector_apply.isEnabled())
        finally:
            close_widget(window)

    def test_minimum_window_prioritizes_table_and_keeps_activity_visible(self):
        window = MainWindow()
        try:
            window.resize(window.minimumSize())
            window.show()
            app().processEvents()

            self.assertTrue(window.activity_drawer.isVisibleTo(window))
            self.assertTrue(window.table_panel.isVisibleTo(window))
            self.assertTrue(window.tableview.isVisibleTo(window))
            self.assertTrue(window.action_activity_dock.isChecked())
        finally:
            close_widget(window)

    def test_activity_visibility_persists_through_config(self):
        window = MainWindow()
        try:
            window.show()
            app().processEvents()

            self.assertTrue(window.activity_drawer.isVisibleTo(window))
            window.action_activity_dock.trigger()
            app().processEvents()

            self.assertFalse(window.activity_drawer.isVisibleTo(window))
            self.assertFalse(config.value('view', 'activity_visible'))
        finally:
            close_widget(window)

        restored = MainWindow()
        try:
            restored.show()
            app().processEvents()

            self.assertFalse(restored.activity_drawer.isVisibleTo(restored))
        finally:
            config.set_value('view', 'activity_visible', True)
            close_widget(restored)

    def test_activity_expanded_state_persists_through_config(self):
        window = MainWindow()
        try:
            window.show()
            app().processEvents()

            self.assertTrue(window.activity_drawer.body.isVisibleTo(window))
            window.activity_drawer.toggle_button.click()
            app().processEvents()

            self.assertFalse(window.activity_drawer.body.isVisibleTo(window))
            self.assertFalse(config.value('view', 'activity_expanded'))
        finally:
            close_widget(window)

        restored = MainWindow()
        try:
            restored.show()
            app().processEvents()

            self.assertFalse(restored.activity_drawer.body.isVisibleTo(restored))
        finally:
            config.set_value('view', 'activity_expanded', True)
            close_widget(restored)

    def test_activity_toggle_does_not_mutate_selected_record(self):
        window = MainWindow()
        item = record()
        before = list(item)
        try:
            window.update_inspector_item(item)
            window.show()
            app().processEvents()

            window.action_activity_dock.trigger()
            app().processEvents()
            window.action_activity_dock.trigger()
            app().processEvents()

            self.assertTrue(window.activity_drawer.isVisibleTo(window))
            self.assertEqual(list(item), before)
        finally:
            close_widget(window)

    def test_command_bar_keeps_icon_and_text_at_minimum_width(self):
        window = MainWindow()
        try:
            window.resize(window.minimumSize())
            window.show()
            app().processEvents()

            self.assertEqual(
                window.command_open.toolButtonStyle(),
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )
            self.assertEqual(window.command_open.text(), 'Open')
            self.assertEqual(window.command_import.text(), 'Import')
            self.assertEqual(window.command_translate.text(), 'Translate')
            self.assertEqual(window.command_dictionary.text(), 'Save Dictionary')
            self.assertIn('reuse', window.command_dictionary.toolTip())
            self.assertFalse(hasattr(window, 'command_options'))

            self.assertEqual(window.brand_title.text(), 'TS4+')
            self.assertFalse(window.brand_block.isVisibleTo(window))
            self.assertFalse(window.command_file_label.isVisibleTo(window))
            self.assertFalse(window.brand_badge.isVisibleTo(window))

            window.resize(1500, 930)
            app().processEvents()

            self.assertEqual(
                window.command_open.toolButtonStyle(),
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )
            self.assertEqual(window.brand_title.text(), 'The Sims 4 Translator Plus')
            self.assertTrue(window.brand_block.isVisibleTo(window))
            self.assertEqual(window.command_dictionary.text(), 'Save Dictionary')
            self.assertTrue(window.command_file_label.isVisibleTo(window))
        finally:
            close_widget(window)

    def test_table_delegate_uses_dense_professional_row_height(self):
        window = MainWindow()
        try:
            delegate = MainDelegatePaint(window.tableview)
            self.assertEqual(delegate.sizeHint(QStyleOptionViewItem(), QModelIndex()).height(), 38)
        finally:
            close_widget(window)

    def test_sims_inspired_theme_tokens_keep_readable_contrast(self):
        self.assertEqual(balanced.ACCENT, '#7dff5a')
        self.assertEqual(balanced.BORDER_FOCUS, '#40dfff')
        self.assertEqual(balanced.BUTTON_DEFAULT, '#009fe3')
        self.assertEqual(balanced.UNVALIDATED_BAR, '#d5b75e')

        self.assertGreaterEqual(contrast_ratio(balanced.TEXT, balanced.SURFACE), 4.5)
        self.assertGreaterEqual(contrast_ratio(balanced.TEXT_MUTED, balanced.SURFACE), 4.5)
        self.assertGreaterEqual(contrast_ratio(balanced.SURFACE, balanced.ACCENT), 4.5)
        self.assertGreaterEqual(contrast_ratio(balanced.SURFACE, balanced.BUTTON_DEFAULT), 4.5)
        self.assertGreaterEqual(contrast_ratio(balanced.TEXT, balanced.SELECTION), 4.5)

        self.assertEqual(STATUS_META[FLAG_UNVALIDATED][1], balanced.UNVALIDATED_BAR)
        self.assertEqual(STATUS_META[FLAG_PROGRESS][1], balanced.WARNING)
        self.assertEqual(STATUS_META[FLAG_VALIDATED][1], balanced.SUCCESS)
        self.assertEqual(STATUS_META[FLAG_TRANSLATED][1], balanced.BORDER_FOCUS)
        self.assertEqual(STATUS_META[FLAG_REPLACED][1], balanced.EDITOR_FEMALE)

    def test_large_filter_counts_are_readable_in_table_filter_board(self):
        window = MainWindow()
        items = [record(FLAG_UNVALIDATED) for _ in range(1234)]
        try:
            window.resize(window.minimumSize())
            window.show()
            app().processEvents()
            window._MainWindow__update_filter_counts(items)
            app().processEvents()

            self.assertEqual(window.filter_all.text(), 'All 1.2k')
            self.assertEqual(window.filter_original.text(), 'Original 1.2k')
            self.assertEqual(window.filter_translated.text(), 'Translated 0')
            self.assertEqual(window._MainWindow__format_filter_count(162527), '162.5k')
            self.assertLessEqual(
                window.filter_all.fontMetrics().horizontalAdvance(window.filter_all.text()) + 10,
                window.filter_all.width()
            )
        finally:
            close_widget(window)

    def test_short_height_density_compacts_filters_selection_and_activity(self):
        window = MainWindow()
        try:
            window.resize(900, 620)
            window.show()
            app().processEvents()

            self.assertEqual(window.command_bar.property('density'), 'short')
            self.assertEqual(window.filter_panel.property('density'), 'short')
            self.assertFalse(window.filter_title.isVisibleTo(window))
            self.assertEqual(window.filter_file_label.text(), 'Package')
            self.assertEqual(window.filter_instance_label.text(), 'Instance')
            self.assertTrue(window.activity_drawer.isVisibleTo(window))
            self.assertTrue(window.activity_drawer.body.isVisibleTo(window))
            self.assertFalse(window.selection_validate.isVisibleTo(window))

            window.activity_drawer.toggle_button.click()
            app().processEvents()

            self.assertFalse(window.activity_drawer.body.isVisibleTo(window))
        finally:
            close_widget(window)

    def test_wide_low_height_window_uses_short_density_for_laptop_screens(self):
        window = MainWindow()
        try:
            window.resize(1580, 840)
            window.show()
            app().processEvents()

            self.assertEqual(window.command_bar.property('density'), 'short')
            self.assertFalse(window.brand_block.isVisibleTo(window))
            self.assertFalse(window.command_file_label.isVisibleTo(window))
            self.assertTrue(window.activity_drawer.body.isVisibleTo(window))

            window.resize(1580, 930)
            app().processEvents()

            self.assertEqual(window.command_bar.property('density'), 'spacious')
            self.assertTrue(window.brand_block.isVisibleTo(window))
            self.assertTrue(window.command_file_label.isVisibleTo(window))
        finally:
            close_widget(window)

    def test_large_filter_counts_use_compact_labels_with_full_tooltips_in_short_mode(self):
        window = MainWindow()
        items = [record(FLAG_UNVALIDATED)] * 162527
        try:
            window.resize(900, 620)
            window.show()
            app().processEvents()
            window._MainWindow__update_filter_counts(items)

            self.assertEqual(window.filter_all.text(), 'All 162.5k')
            self.assertEqual(window.filter_original.text(), 'Original 162.5k')
            self.assertEqual(window.filter_original.toolTip(), 'Original: 162,527')
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

    def test_hybrid_search_matches_id_original_and_translated_without_mode_switching(self):
        window = MainWindow()
        by_id = record(FLAG_UNVALIDATED)
        by_id[RECORD_MAIN_ID] = 0xB586D7F4
        by_id[RECORD_MAIN_SOURCE] = 'Garden chair'
        by_id[RECORD_MAIN_TRANSLATE] = 'Chaise de jardin'
        by_source = record(FLAG_UNVALIDATED)
        by_source[RECORD_MAIN_ID] = 0x12345678
        by_source[RECORD_MAIN_SOURCE] = 'Needle appears in original text'
        by_source[RECORD_MAIN_TRANSLATE] = 'Draft without marker'
        by_translation = record(FLAG_UNVALIDATED)
        by_translation[RECORD_MAIN_ID] = 0x87654321
        by_translation[RECORD_MAIN_SOURCE] = 'Source without marker'
        by_translation[RECORD_MAIN_TRANSLATE] = 'Needle appears in translated text'
        try:
            storage = app_state.packages_storage
            storage.packages.append(PackageStub())
            storage.model.replace([by_id, by_source, by_translation])
            storage.proxy.process_filter()
            window.set_state_menu()

            self.assertEqual(window.filter_search_mode.text(), 'Hybrid')

            window.filter_search.setText('0xB586D7F4')
            window.update_proxy()
            self.assertEqual([item.id for item in storage.model.filtered], [0xB586D7F4])

            window.filter_search.setText('original text')
            window.update_proxy()
            self.assertEqual([item.id for item in storage.model.filtered], [0x12345678])

            window.filter_search.setText('translated text')
            window.update_proxy()
            self.assertEqual([item.id for item in storage.model.filtered], [0x87654321])
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

    def test_selection_bar_handles_long_vietnamese_selection_without_overlapping(self):
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

            self.assertTrue(window.selection_bar.isVisibleTo(window))
            self.assertLess(window.selection_meta.geometry().right(), window.selection_status.geometry().left())
            self.assertLess(window.selection_status.geometry().right(), window.selection_preview_toggle.geometry().left())
            self.assertEqual(window.selection_original_text.toPlainText(), long_text)
            self.assertEqual(window.selection_translation_text.toPlainText(), long_text)
            self.assertTrue(window.selection_preview.isVisibleTo(window))
        finally:
            close_widget(window)

    def test_short_selection_bar_restores_actions_after_row_selection(self):
        window = MainWindow()
        item = record()
        try:
            window.resize(900, 620)
            window.show()
            app().processEvents()

            self.assertFalse(window.selection_validate.isVisibleTo(window))
            self.assertFalse(window.selection_preview.isVisibleTo(window))
            window.update_inspector_item(item)
            app().processEvents()

            self.assertTrue(window.selection_validate.isVisibleTo(window))
            self.assertTrue(window.selection_reset.isVisibleTo(window))
            self.assertTrue(window.selection_edit.isVisibleTo(window))
            self.assertTrue(window.selection_preview.isVisibleTo(window))
        finally:
            close_widget(window)

    def test_selection_bar_populates_from_record_without_mutating_it(self):
        window = MainWindow()
        item = record()
        before = list(item)
        try:
            window.update_inspector_item(item)

            self.assertEqual(list(item), before)
            self.assertIn('0x0000002A', window.inspector_meta.text())
            self.assertEqual(window.inspector_status.text(), 'In progress')
            self.assertTrue(window.inspector_apply.isEnabled())
            self.assertEqual(window.selection_bar.property('active'), True)
            self.assertEqual(window.selection_original_text.toPlainText(), item.source)
            self.assertEqual(window.selection_translation_text.toPlainText(), item.translate)

            window.toggle_selection_preview()
            self.assertTrue(window.selection_preview.isHidden())
            window.toggle_selection_preview()
            self.assertFalse(window.selection_preview.isHidden())
        finally:
            close_widget(window)

    def test_selection_bar_reset_and_validate_use_existing_record_state(self):
        window = MainWindow()
        item = record()
        try:
            window.update_inspector_item(item)
            window.apply_inspector_translation()

            self.assertEqual(item.translate, 'Bonjour draft')
            self.assertEqual(item.comment, 'Needs review')
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
            self.assertEqual(dialog.edit_header.objectName(), 'sheetHeader')
            self.assertEqual(dialog.dictionary_panel.objectName(), 'sheetPanel')
            self.assertEqual(dialog.original_panel.objectName(), 'sheetPanel')
            self.assertEqual(dialog.translation_panel.objectName(), 'sheetPanel')
            self.assertEqual(dialog.edit_footer.objectName(), 'sheetFooter')
            self.assertEqual(dialog.edit_detail.objectName(), 'sheetHint')
            self.assertTrue(dialog.btn_ok.isDefault())
            self.assertFalse(dialog.btn_translate.autoDefault())
            self.assertFalse(dialog.btn_cancel.autoDefault())
        finally:
            close_widget(dialog)

    def test_edit_dialog_recovers_space_when_dictionary_suggestions_are_empty(self):
        dialog = EditDialog()
        try:
            dialog.prepare(record())
            dialog.show()
            app().processEvents()

            self.assertFalse(dialog.suggestions_splitter.isVisibleTo(dialog))
            self.assertTrue(dialog.translation_splitter.isVisibleTo(dialog))
            self.assertTrue(dialog.btn_ok.isDefault())
            self.assertFalse(dialog.btn_translate.autoDefault())
        finally:
            close_widget(dialog)

    def test_guided_sheet_dialogs_share_the_same_shell_contract(self):
        window = MainWindow()
        dialogs = [
            ImportDialog(),
            TranslateDialog(),
            ExportDialog(window),
        ]
        try:
            for dialog in dialogs:
                self.assertEqual(dialog.header.objectName(), 'sheetHeader')
                self.assertEqual(dialog.header_title.objectName(), 'sheetTitle')
                self.assertEqual(dialog.header_detail.objectName(), 'sheetHint')
                self.assertEqual(dialog.sheet_footer.objectName(), 'sheetFooter')
        finally:
            for dialog in dialogs:
                close_widget(dialog)
            close_widget(window)

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
