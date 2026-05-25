# -*- coding: utf-8 -*-

import os
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QModelIndex, Qt, QEvent, QEventLoop, QThread, QTimer
from PySide6.QtGui import QIcon, QKeyEvent
from PySide6.QtWidgets import QApplication, QMessageBox, QHeaderView, QStyleOptionViewItem
from unittest.mock import patch

import resource_rc
import themes.balanced as balanced
from main import show_main_window
from packer.resource import ResourceID
from singletons.config import ConfigManager, config
from singletons.interface import interface
from singletons.state import app_state
from singletons.translator import DeepLUsage, OLLAMA_RECOMMENDED_MODEL, Response
from storages.dictionaries import DictionariesStorage
from storages.packages import PackagesStorage
from storages.records import MainRecord
from utils.constants import (
    EXPORT_JSON_S4S,
    FLAG_PROGRESS,
    FLAG_REPLACED,
    FLAG_TRANSLATED,
    FLAG_UNVALIDATED,
    FLAG_VALIDATED,
    RECORD_MAIN_ID,
    RECORD_MAIN_SOURCE,
    RECORD_MAIN_TRANSLATE,
)
from utils.release_validation import (
    PROFILE_SOFT,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    ValidationIssue,
    ValidationReport,
)
from utils.ollama_setup import OLLAMA_DOWNLOAD_URL, OllamaPullResult, OllamaSetupStatus
from utils.workspace_warnings import workspace_warnings_report
from windows.edit_dialog import EditDialog
from windows.export_dialog import ExportDialog
from windows.import_dialog import ImportDialog
from windows.main_window import MainWindow
from windows.options_dialog import OptionsDialog
from windows.release_validation_dialog import ReleaseValidationDialog
from windows.translate_dialog import TranslateDialog
from widgets.delegate import MainDelegatePaint, STATUS_META, TABLE_ROW_HEIGHTS


def app():
    return QApplication.instance() or QApplication([])


def close_widget(widget):
    widget.close()
    widget.deleteLater()
    app().processEvents()


def wait_for_handle(handle, timeout=3000):
    loop = QEventLoop()
    handle.finished.connect(lambda _cancelled: loop.quit())
    QTimer.singleShot(timeout, loop.quit)
    loop.exec()
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
    name = 'sample'
    filename = 'sample.package'
    instances = []
    modified = False

    def __init__(self):
        self.saved = False
        self.finalized = False
        self.finalize_path = None

    def __len__(self):
        return 2

    def modify(self, state=True):
        self.modified = state

    def save(self):
        self.saved = True

    def finalize(self, path=None):
        self.finalized = True
        self.finalize_path = path


class FakeWheelEvent:

    def __init__(self):
        self.ignored = False

    def ignore(self):
        self.ignored = True


class FakeStartupWindow:

    def __init__(self):
        self.maximized = False
        self.normal_show = False

    def showMaximized(self):
        self.maximized = True

    def show(self):
        self.normal_show = True


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
        config.set_value('api', 'engine', 'Google')
        config.set_value('api', 'deepl_key', '')
        config.set_value('api', 'deepl_glossary_id', '')
        config.set_value('api', 'gemini_key', '')
        config.set_value('api', 'gemini_model', 'gemini-2.5-flash')
        config.set_value('api', 'openai_key', '')
        config.set_value('api', 'openai_base_url', 'https://api.openai.com')
        config.set_value('api', 'openai_model', 'gpt-4o-mini')
        config.set_value('api', 'ollama_enabled', False)
        config.set_value('api', 'ollama_base_url', 'http://localhost:11434')
        config.set_value('api', 'ollama_model', 'translategemma:12b')
        config.set_value('view', 'activity_visible', True)
        config.set_value('view', 'activity_expanded', True)
        config.set_value('view', 'row_density', 'comfortable')
        app_state.set_packages_storage(PackagesStorage())
        app_state.set_dictionaries_storage(DictionariesStorage())
        app_state.set_current_package(None)
        app_state.set_current_instance(0)

    def test_main_window_creates_workspace_pro_shell_without_losing_legacy_actions(self):
        window = MainWindow()
        try:
            self.assertEqual(window.command_bar.objectName(), 'studioHeader')
            self.assertEqual(window.action_hub.objectName(), 'studioActionHub')
            self.assertEqual(window.filter_panel.objectName(), 'studioFilterTray')
            self.assertIs(window.filter_panel.parent(), window.workspace_overview)
            self.assertEqual(window.workspace_stats_bar.objectName(), 'workspaceStatsBar')
            self.assertIs(window.workspace_summary_block.parent(), window.workspace_stats_bar)
            self.assertIs(window.workspace_stats_bar.parent(), window.activity_drawer.header)
            self.assertNotEqual(window.activity_drawer.header_layout.indexOf(window.workspace_stats_bar), -1)
            self.assertEqual(window.table_panel_layout.indexOf(window.workspace_stats_bar), -1)
            self.assertEqual(window.workspace_overview_layout.indexOf(window.workspace_summary_block), -1)
            self.assertLessEqual(window.workspace_stats_bar.maximumWidth(), 560)
            self.assertEqual(window.selection_bar.objectName(), 'selectionBar')
            self.assertEqual(window.workspace_overview.objectName(), 'workspaceOverview')
            self.assertFalse(hasattr(window, 'empty_state'))
            self.assertFalse(hasattr(window, 'empty_open_button'))
            self.assertEqual(window.filter_search.objectName(), 'filterSearch')
            self.assertFalse(window.filter_search_mode.isVisibleTo(window))
            self.assertEqual(window.filter_search_mode.text(), '')
            self.assertIn('ID', window.filter_search.placeholderText())
            self.assertIn('original', window.filter_search.toolTip())
            self.assertIs(window.activity_drawer, window.job_drawer)
            self.assertTrue(window.action_activity_dock.isCheckable())
            self.assertIn(window.action_activity_dock, window.menu_view.actions())
            self.assertIn(window.action_validate_release, window.menu_translation.actions())
            self.assertFalse(window.action_validate_release.isEnabled())
            self.assertEqual(window.command_validate_release.property('commandLabel'), 'Release QA')
            self.assertFalse(window.command_validate_release.isEnabled())
            self.assertFalse(window.command_validate_release.icon().isNull())
            self.assertEqual(window.command_file_group.objectName(), 'studioActionGroup')
            self.assertEqual(window.command_export_group.objectName(), 'studioActionGroup')
            self.assertEqual(window.command_translation_group.objectName(), 'studioActionGroup')
            self.assertEqual(window.command_scope_group.objectName(), 'studioScopeGroup')
            self.assertGreater(
                window.command_layout.indexOf(window.command_scope_group),
                window.command_layout.indexOf(window.action_hub),
            )
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
            self.assertFalse(window.brand_block.isVisibleTo(window))
            self.assertFalse(window.inspector_apply.isEnabled())
        finally:
            close_widget(window)

    def test_app_startup_opens_main_window_maximized(self):
        window = FakeStartupWindow()

        show_main_window(window)

        self.assertTrue(window.maximized)
        self.assertFalse(window.normal_show)

    def test_manual_validate_release_shows_report_without_mutating_records(self):
        item = record(FLAG_VALIDATED)
        storage = app_state.packages_storage
        storage.model.replace([item])
        storage.model.filter([item])
        storage.packages.append(PackageStub())
        app_state.set_current_package(PackageStub.key)

        window = MainWindow()
        try:
            original_translation = item.translate
            with patch('windows.main_window.QInputDialog.getItem', return_value=(PROFILE_SOFT.name, True)), \
                    patch('windows.main_window.ReleaseValidationDialog.confirm', return_value=False) as confirm:
                window.validate_release()
                wait_for_handle(window._MainWindow__validation_handle)

            self.assertTrue(confirm.called)
            self.assertEqual(confirm.call_args.args[1].profile.name, PROFILE_SOFT.name)
            self.assertEqual(item.translate, original_translation)
            self.assertEqual(item.flag, FLAG_VALIDATED)
        finally:
            close_widget(window)

    def test_save_package_validation_cancel_prevents_existing_save_path(self):
        item = record(FLAG_VALIDATED)
        storage = app_state.packages_storage
        storage.model.replace([item])
        storage.model.filter([item])
        package = PackageStub()
        storage.packages.append(package)
        app_state.set_current_package(package.key)

        window = MainWindow()
        try:
            with patch('windows.main_window.ReleaseValidationDialog.confirm', return_value=False):
                window.save()
                wait_for_handle(window._MainWindow__validation_handle)

            self.assertFalse(package.saved)
        finally:
            close_widget(window)

    def test_manual_validate_release_cancellation_does_not_open_report(self):
        item = record(FLAG_VALIDATED)
        storage = app_state.packages_storage
        storage.model.replace([item])
        storage.model.filter([item])
        storage.packages.append(PackageStub())

        def slow_validation(token, _reporter, _request):
            for _index in range(100):
                token.raise_if_cancelled()
                QThread.msleep(1)
            return None

        window = MainWindow()
        try:
            with patch('windows.main_window.QInputDialog.getItem', return_value=(PROFILE_SOFT.name, True)), \
                    patch('windows.main_window.validate_release_task', slow_validation), \
                    patch('windows.main_window.ReleaseValidationDialog.confirm') as confirm:
                window.validate_release()
                handle = window._MainWindow__validation_handle
                handle.cancel()
                wait_for_handle(handle)

            confirm.assert_not_called()
        finally:
            close_widget(window)

    def test_finalize_validation_continue_starts_existing_finalize_path(self):
        item = record(FLAG_VALIDATED)
        storage = app_state.packages_storage
        storage.model.replace([item])
        storage.model.filter([item])
        package = PackageStub()
        storage.packages.append(package)
        app_state.set_current_package(package.key)

        window = MainWindow()
        try:
            with patch('windows.main_window.ReleaseValidationDialog.confirm', return_value=True):
                window.finalize()
                wait_for_handle(window._MainWindow__validation_handle)

            self.assertTrue(package.finalized)
            self.assertIsNone(package.finalize_path)
        finally:
            close_widget(window)

    def test_release_validation_dialog_defaults_to_back_for_critical_report(self):
        report = ValidationReport(
            mode='Export JSON',
            profile=PROFILE_SOFT,
            destination_locale='VI_VN',
            include_untranslated=True,
            conflict_free=False,
            total_records=1,
            written_records=1,
            package_count=1,
            resource_count=1,
            status_counts=(('Approved', 1),),
            issues=(ValidationIssue(
                SEVERITY_CRITICAL,
                'pkg.package',
                '0x0000000000000001',
                '0x0000002A',
                'Approved',
                'Missing source token(s): {0.SimFirstName}',
                '{0.SimFirstName}',
                '',
            ),),
        )

        dialog = ReleaseValidationDialog(report)
        try:
            self.assertTrue(dialog.btn_back.isDefault())
            self.assertEqual(dialog.btn_continue.text(), 'Continue anyway')
            self.assertEqual(dialog.tabs.tabText(0), 'Critical (1)')
            self.assertIsNotNone(dialog.issue_model.data(
                dialog.issue_model.index(0, 0),
                Qt.ItemDataRole.ForegroundRole,
            ))
            self.assertTrue(dialog.issue_model.data(
                dialog.issue_model.index(0, 0),
                Qt.ItemDataRole.FontRole,
            ).bold())
        finally:
            close_widget(dialog)

    def test_release_validation_dialog_uses_vietnamese_interface_labels(self):
        report = ValidationReport(
            mode='Export JSON',
            profile=PROFILE_SOFT,
            destination_locale='VI_VN',
            include_untranslated=True,
            conflict_free=False,
            total_records=1,
            written_records=1,
            package_count=1,
            resource_count=1,
            status_counts=(('Approved', 1),),
            issues=(ValidationIssue(
                SEVERITY_CRITICAL,
                'pkg.package',
                '0x0000000000000001',
                '0x0000002A',
                'Approved',
                'Missing source token(s): {0.SimFirstName}',
                '{0.SimFirstName}',
                '',
                None,
                'MISSING_TOKEN',
                'Token safety',
            ),),
        )

        config.set_value('interface', 'language', 'vi_VN')
        interface.reload()
        dialog = ReleaseValidationDialog(report)
        try:
            self.assertEqual(dialog.windowTitle(), 'Báo cáo kiểm tra trước khi phát hành')
            self.assertEqual(dialog.btn_back.text(), 'Quay lại sửa')
            self.assertEqual(dialog.btn_continue.text(), 'Vẫn tiếp tục')
            self.assertIn('Nghiêm trọng', dialog.tabs.tabText(0))
            self.assertEqual(
                dialog.issue_model.headerData(
                    7,
                    Qt.Orientation.Horizontal,
                    Qt.ItemDataRole.DisplayRole,
                ),
                'Lý do',
            )
            self.assertEqual(dialog.issue_model.data(dialog.issue_model.index(0, 0)), 'Nghiêm trọng')
            self.assertEqual(dialog.issue_model.data(dialog.issue_model.index(0, 2)), 'An toàn token')
        finally:
            close_widget(dialog)
            config.set_value('interface', 'language', 'en_US')
            interface.reload()

    def test_release_validation_dialog_double_click_opens_existing_record_callback(self):
        item = record(FLAG_PROGRESS)
        opened = []
        report = ValidationReport(
            mode='Manual validation',
            profile=PROFILE_SOFT,
            destination_locale='VI_VN',
            include_untranslated=True,
            conflict_free=False,
            total_records=1,
            written_records=1,
            package_count=1,
            resource_count=1,
            status_counts=(('Needs review', 1),),
            issues=(ValidationIssue(
                SEVERITY_INFO,
                'pkg.package',
                item.instance_hex,
                item.id_hex,
                'Needs review',
                'Sample info',
                item.source,
                item.translate,
                item,
            ),),
        )

        dialog = ReleaseValidationDialog(report, opened.append)
        try:
            dialog.tabs.setCurrentIndex(2)
            proxy_index = dialog.issue_proxy.index(0, 0)
            dialog.issue_table.doubleClicked.emit(proxy_index)
            self.assertEqual(opened, [item])
        finally:
            close_widget(dialog)

    def test_release_validation_dialog_category_and_search_filters_without_mutating_records(self):
        item = record(FLAG_PROGRESS)
        before = list(item)
        report = ValidationReport(
            mode='Manual validation',
            profile=PROFILE_SOFT,
            destination_locale='VI_VN',
            include_untranslated=True,
            conflict_free=False,
            total_records=2,
            written_records=2,
            package_count=1,
            resource_count=1,
            status_counts=(('Needs review', 1),),
            issues=(
                ValidationIssue(
                    SEVERITY_CRITICAL,
                    'pkg.package',
                    item.instance_hex,
                    item.id_hex,
                    'Needs review',
                    'Missing source token(s): {0.SimFirstName}',
                    '{0.SimFirstName}',
                    '',
                    item,
                    'MISSING_TOKEN',
                    'Token safety',
                ),
                ValidationIssue(
                    SEVERITY_INFO,
                    'pkg.package',
                    item.instance_hex,
                    '0x00000007',
                    '-',
                    'Summary',
                    '',
                    '',
                    None,
                    'SUMMARY',
                    'Summary',
                ),
            ),
        )

        dialog = ReleaseValidationDialog(report)
        try:
            dialog.category_filter.setCurrentText('Token safety')
            self.assertEqual(dialog.issue_proxy.rowCount(), 1)
            dialog.search_filter.setText(item.id_hex)
            self.assertEqual(dialog.issue_proxy.rowCount(), 1)
            dialog.search_filter.setText('not-found')
            self.assertEqual(dialog.issue_proxy.rowCount(), 0)
            self.assertEqual(list(item), before)
        finally:
            close_widget(dialog)

    def test_release_validation_dialog_review_columns_prioritize_reason(self):
        report = ValidationReport(
            mode='Manual validation',
            profile=PROFILE_SOFT,
            destination_locale='VI_VN',
            include_untranslated=True,
            conflict_free=False,
            total_records=1,
            written_records=1,
            package_count=1,
            resource_count=1,
            status_counts=(('Approved', 1),),
            issues=(ValidationIssue(
                SEVERITY_CRITICAL,
                'very-long-package-name.package',
                '0x0000000000000001',
                '0x0000002A',
                'Approved',
                'Missing source token(s): {0.SimFirstName}; this reason must remain readable.',
                '{0.SimFirstName} says hello',
                'Xin chao',
                None,
                'MISSING_TOKEN',
                'Token safety',
            ),),
        )

        dialog = ReleaseValidationDialog(report)
        try:
            dialog.show()
            app().processEvents()

            self.assertTrue(dialog.issue_table.isColumnHidden(1))
            self.assertTrue(dialog.issue_table.isColumnHidden(2))
            self.assertEqual(
                dialog.issue_table.horizontalHeader().sectionResizeMode(7),
                QHeaderView.ResizeMode.Stretch,
            )
            self.assertGreater(dialog.issue_table.columnWidth(7), dialog.issue_table.columnWidth(0))
            self.assertGreater(dialog.issue_table.columnWidth(7), dialog.issue_table.columnWidth(5))
            self.assertGreaterEqual(dialog.issue_table.columnWidth(8), 300)
            self.assertGreaterEqual(dialog.issue_table.columnWidth(9), 300)
        finally:
            close_widget(dialog)

    def test_release_validation_dialog_copies_selected_issue_details(self):
        report = ValidationReport(
            mode='Manual validation',
            profile=PROFILE_SOFT,
            destination_locale='VI_VN',
            include_untranslated=True,
            conflict_free=False,
            total_records=1,
            written_records=1,
            package_count=1,
            resource_count=1,
            status_counts=(('Approved', 1),),
            issues=(ValidationIssue(
                SEVERITY_CRITICAL,
                'pkg.package',
                '0x0000000000000001',
                '0x0000002A',
                'Approved',
                'Missing source token(s): {0.SimFirstName}',
                '{0.SimFirstName}',
                '',
                None,
                'MISSING_TOKEN',
                'Token safety',
            ),),
        )

        dialog = ReleaseValidationDialog(report)
        try:
            dialog.show()
            app().processEvents()
            dialog.issue_table.selectRow(0)
            dialog.copy_selected_issue()

            copied = QApplication.clipboard().text()
            self.assertIn('Critical', copied)
            self.assertIn('MISSING_TOKEN', copied)
            self.assertIn('Token safety', copied)
            self.assertIn('0x0000002A', copied)
            self.assertIn('Missing source token', copied)
        finally:
            close_widget(dialog)

    def test_workspace_warnings_report_detects_token_empty_duplicate_and_modified_records(self):
        first = record(FLAG_VALIDATED)
        first[RECORD_MAIN_ID] = 0x100
        first[RECORD_MAIN_SOURCE] = '{0.SimFirstName} says hello'
        first[RECORD_MAIN_TRANSLATE] = ''
        second = record(FLAG_PROGRESS)
        second[RECORD_MAIN_ID] = 0x100
        second[RECORD_MAIN_SOURCE] = 'Duplicate key'
        second[RECORD_MAIN_TRANSLATE] = 'Different translation'
        third = record(FLAG_TRANSLATED)
        third[RECORD_MAIN_ID] = 0x300
        third[RECORD_MAIN_SOURCE] = 'Changed source'
        third[RECORD_MAIN_TRANSLATE] = 'Repeated text'
        third.source_old = 'Old source'
        fourth = record(FLAG_TRANSLATED)
        fourth[RECORD_MAIN_ID] = 0x301
        fourth[RECORD_MAIN_TRANSLATE] = 'Repeated text'

        report = workspace_warnings_report((first, second, third, fourth), 'VI_VN')
        codes = {issue.code for issue in report.issues}

        self.assertIn('WORKSPACE_EMPTY_TRANSLATION', codes)
        self.assertIn('WORKSPACE_TOKEN_MISMATCH', codes)
        self.assertIn('WORKSPACE_DUPLICATE_OUTPUT_TEXT', codes)
        self.assertIn('WORKSPACE_MODIFIED_RECORD', codes)
        self.assertIn('WORKSPACE_REPEATED_TRANSLATION', codes)
        self.assertGreaterEqual(report.count(SEVERITY_WARNING), 1)

    def test_workspace_warnings_action_uses_report_dialog_without_mutating_records(self):
        window = MainWindow()
        item = record(FLAG_VALIDATED)
        item[RECORD_MAIN_SOURCE] = '{0.SimFirstName} arrives'
        item.translate = 'arrives'
        try:
            storage = app_state.packages_storage
            storage.packages.append(PackageStub())
            storage.model.replace([item])
            window.set_state_menu()

            opened = []

            def fake_confirm(_parent, report, _open_issue=None):
                opened.append(report)
                return False

            with patch.object(ReleaseValidationDialog, 'confirm', side_effect=fake_confirm):
                window.workspace_warnings()

            self.assertEqual(len(opened), 1)
            self.assertEqual(opened[0].mode, 'Workspace Warnings')
            self.assertEqual(item.translate, 'arrives')
            self.assertEqual(item.flag, FLAG_VALIDATED)
        finally:
            close_widget(window)

    def test_rebranded_icon_resource_and_dialog_window_icons_load(self):
        self.assertFalse(QIcon(':/logo.ico').isNull())
        self.assertFalse(QIcon(':/images/life_status.png').isNull())
        self.assertFalse(QIcon(':/images/life_scope.png').isNull())
        self.assertFalse(QIcon(':/images/life_validate.png').isNull())

        window = MainWindow()
        report = ValidationReport(
            mode='Manual validation',
            profile=PROFILE_SOFT,
            destination_locale='VI_VN',
            include_untranslated=True,
            conflict_free=False,
            total_records=0,
            written_records=0,
            package_count=0,
            resource_count=0,
            status_counts=(),
            issues=(),
        )
        dialogs = [
            ReleaseValidationDialog(report),
            TranslateDialog(window),
            EditDialog(window),
            ImportDialog(window),
            ExportDialog(window),
            OptionsDialog(window),
        ]
        try:
            self.assertFalse(window.windowIcon().isNull())
            for dialog in dialogs:
                self.assertFalse(dialog.windowIcon().isNull(), dialog.windowTitle())
        finally:
            for dialog in dialogs:
                close_widget(dialog)
            close_widget(window)

    def test_single_life_asset_system_replaces_dark_light_resources(self):
        root = Path(__file__).resolve().parents[1]
        qrc_path = root / 'resources' / 'resource.qrc'
        qss_path = root / 'resources' / 'theme.qss'

        qrc_text = qrc_path.read_text(encoding='utf-8')
        qss_text = qss_path.read_text(encoding='utf-8')

        for forbidden in ('images/dark/', 'images/light/', '__THEME__'):
            self.assertNotIn(forbidden, qrc_text)
            self.assertNotIn(forbidden, qss_text)

        self.assertFalse((root / 'resources' / 'images' / 'dark').exists())
        self.assertFalse((root / 'resources' / 'images' / 'light').exists())

        files = [
            element.text
            for element in ElementTree.parse(qrc_path).findall('.//file')
            if element.text and element.text.startswith('images/') and element.text.endswith('.png')
        ]
        self.assertIn('images/life/backspace.png', files)
        self.assertIn('images/life/checkbox_checked.png', files)
        self.assertIn('images/life/radio_checked.png', files)

        for file_path in files:
            self.assertFalse(QIcon(f':/{file_path}').isNull(), file_path)

        forbidden_imports = ('import themes.dark', 'import themes.light', 'from themes import dark',
                             'from themes import light')
        for source_root in ('models', 'widgets', 'windows', 'themes'):
            for path in (root / source_root).rglob('*.py'):
                text = path.read_text(encoding='utf-8')
                for forbidden in forbidden_imports:
                    self.assertNotIn(forbidden, text, str(path))

    def test_export_validation_cancel_does_not_start_export_task(self):
        item = record(FLAG_VALIDATED)
        storage = app_state.packages_storage
        storage.model.replace([item])
        storage.model.filter([item])
        storage.packages.append(PackageStub())

        dialog = ExportDialog()
        try:
            dialog._ExportDialog__export = EXPORT_JSON_S4S
            dialog.rb_all.setChecked(True)

            with patch('windows.export_dialog.ReleaseValidationDialog.confirm', return_value=False):
                handle = dialog.export_structured([item], filename='release.json')
                wait_for_handle(handle)

            self.assertIsNotNone(handle)
            self.assertIsNone(dialog._ExportDialog__export_handle)
            self.assertTrue(dialog._ExportDialog__validation_cancelled)
        finally:
            close_widget(dialog)

    def test_export_validation_continue_starts_existing_export_path(self):
        item = record(FLAG_VALIDATED)
        storage = app_state.packages_storage
        storage.model.replace([item])
        storage.model.filter([item])
        storage.packages.append(PackageStub())

        dialog = ExportDialog()
        try:
            dialog._ExportDialog__export = EXPORT_JSON_S4S
            dialog.rb_all.setChecked(True)

            with patch('windows.export_dialog.ReleaseValidationDialog.confirm', return_value=True), \
                    patch.object(dialog, '_ExportDialog__start_structured_export', return_value=None) as start:
                handle = dialog.export_structured([item], filename='release.json')
                wait_for_handle(handle)

            start.assert_called_once()
            self.assertFalse(dialog._ExportDialog__validation_cancelled)
        finally:
            close_widget(dialog)

    def test_open_command_loads_first_file_then_adds_next_file(self):
        window = MainWindow()
        try:
            with patch('windows.main_window.open_supported', return_value='first.package'), \
                    patch.object(window, 'load') as load_mock:
                window.open_hybrid_file()

            load_mock.assert_called_once_with('first.package', False)

            app_state.packages_storage.packages.append(PackageStub())
            window.set_state_menu()

            with patch('windows.main_window.open_supported', return_value='second.package'), \
                    patch.object(window, 'load') as load_mock:
                window.open_hybrid_file()

            load_mock.assert_called_once_with('second.package', True)
            self.assertEqual(window.command_open.text(), 'Open')
            self.assertIn('Add file', window.command_open.toolTip())
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
            self.assertEqual(window.command_dictionary.text(), 'Dictionary')
            self.assertEqual(window.command_validate_release.text(), 'Release QA')
            self.assertGreaterEqual(window.command_open.iconSize().width(), 22)
            self.assertGreaterEqual(window.command_translate.iconSize().height(), 22)
            self.assertIn('reuse', window.command_dictionary.toolTip())
            self.assertIn('Validate Release', window.command_validate_release.toolTip())
            self.assertFalse(hasattr(window, 'command_options'))

            self.assertFalse(window.brand_block.isVisibleTo(window))
            self.assertTrue(window.command_file_label.isVisibleTo(window))
            self.assertFalse(window.brand_badge.isVisibleTo(window))

            window.resize(1500, 930)
            app().processEvents()

            self.assertEqual(
                window.command_open.toolButtonStyle(),
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )
            self.assertFalse(window.brand_block.isVisibleTo(window))
            self.assertEqual(window.command_dictionary.text(), 'Dictionary')
            self.assertTrue(window.command_file_label.isVisibleTo(window))
        finally:
            close_widget(window)

    def test_table_delegate_supports_comfortable_and_compact_row_density(self):
        window = MainWindow()
        try:
            delegate = MainDelegatePaint(window.tableview)
            self.assertEqual(delegate.row_density, 'comfortable')
            self.assertEqual(
                delegate.sizeHint(QStyleOptionViewItem(), QModelIndex()).height(),
                TABLE_ROW_HEIGHTS['comfortable'],
            )

            compact = MainDelegatePaint(window.tableview, row_density='compact')
            self.assertEqual(compact.row_density, 'compact')
            self.assertEqual(
                compact.sizeHint(QStyleOptionViewItem(), QModelIndex()).height(),
                TABLE_ROW_HEIGHTS['compact'],
            )
        finally:
            close_widget(window)

    def test_main_table_applies_configured_row_density_without_mutating_records(self):
        config.set_value('view', 'row_density', 'compact')
        window = MainWindow()
        item = record(FLAG_UNVALIDATED)
        before = list(item)
        try:
            storage = app_state.packages_storage
            storage.packages.append(PackageStub())
            storage.model.replace([item])
            storage.proxy.process_filter()
            window.tableview.set_model()

            self.assertEqual(window.tableview.property('rowDensity'), 'compact')
            self.assertEqual(
                window.tableview.verticalHeader().defaultSectionSize(),
                TABLE_ROW_HEIGHTS['compact'],
            )
            self.assertEqual(list(item), before)
        finally:
            close_widget(window)

    def test_sims_inspired_theme_tokens_keep_readable_contrast(self):
        self.assertEqual(balanced.ACCENT, '#a9f76b')
        self.assertEqual(balanced.BORDER_FOCUS, '#72f4d8')
        self.assertEqual(balanced.BUTTON_DEFAULT, '#9bf26a')
        self.assertEqual(balanced.UNVALIDATED_BAR, '#d8d66a')

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
        self.assertEqual(STATUS_META[FLAG_UNVALIDATED][0], 'Untranslated')
        self.assertEqual(STATUS_META[FLAG_PROGRESS][0], 'Needs review')
        self.assertEqual(STATUS_META[FLAG_VALIDATED][0], 'Approved')
        self.assertEqual(STATUS_META[FLAG_TRANSLATED][0], 'Draft')

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
            self.assertEqual(window.filter_original.text(), 'Untranslated 1.2k')
            self.assertEqual(window.filter_translated.text(), 'Draft 0')
            self.assertFalse(window.filter_translated.isVisibleTo(window))
            self.assertEqual(window.filter_layout.indexOf(window.filter_translated), -1)
            self.assertEqual(window._MainWindow__format_filter_count(162527), '162.5k')
            self.assertLessEqual(
                window.filter_all.fontMetrics().horizontalAdvance(window.filter_all.text()) + 10,
                window.filter_all.width()
            )
        finally:
            close_widget(window)

    def test_draft_status_is_display_only_not_a_primary_filter_chip(self):
        window = MainWindow()
        try:
            window.resize(window.minimumSize())
            window.show()
            app().processEvents()

            window._MainWindow__update_filter_counts([record(FLAG_UNVALIDATED)])
            app().processEvents()

            self.assertFalse(window.filter_translated.isVisibleTo(window))
            self.assertEqual(window.filter_layout.indexOf(window.filter_translated), -1)

            window._MainWindow__update_filter_counts([record(FLAG_TRANSLATED)])
            app().processEvents()

            self.assertFalse(window.filter_translated.isVisibleTo(window))
            self.assertEqual(window.filter_layout.indexOf(window.filter_translated), -1)
            self.assertEqual(window.filter_translated.text(), 'Draft 1')
        finally:
            close_widget(window)

    def test_short_height_density_compacts_filters_selection_and_activity(self):
        window = MainWindow()
        try:
            window.resize(900, 620)
            window.show()
            app().processEvents()

            self.assertEqual(window.command_bar.property('density'), 'spacious')
            self.assertEqual(window.filter_panel.property('density'), 'spacious')
            self.assertTrue(window.command_scope_group.isVisibleTo(window))
            self.assertFalse(hasattr(window, 'filter_title'))
            self.assertEqual(window.filter_file_label.text(), 'Package')
            self.assertEqual(window.filter_instance_label.text(), 'Instance')
            self.assertEqual(window.filter_layout.indexOf(window.filter_file), -1)
            self.assertEqual(window.filter_layout.indexOf(window.filter_instance), -1)
            self.assertEqual(window.filter_layout.indexOf(window.filter_different), -1)
            self.assertNotEqual(window.command_scope_layout.indexOf(window.filter_file), -1)
            self.assertNotEqual(window.command_scope_layout.indexOf(window.filter_instance), -1)
            self.assertNotEqual(window.command_scope_layout.indexOf(window.filter_different), -1)
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

            self.assertEqual(window.command_bar.property('density'), 'spacious')
            self.assertFalse(window.brand_block.isVisibleTo(window))
            self.assertTrue(window.command_file_label.isVisibleTo(window))
            self.assertTrue(window.activity_drawer.body.isVisibleTo(window))

            window.resize(1580, 930)
            app().processEvents()

            self.assertEqual(window.command_bar.property('density'), 'spacious')
            self.assertFalse(window.brand_block.isVisibleTo(window))
            self.assertTrue(window.command_file_label.isVisibleTo(window))
            self.assertTrue(window.command_scope_group.isVisibleTo(window))
        finally:
            close_widget(window)

    def test_spacious_workspace_uses_header_scope_block_for_secondary_filters(self):
        window = MainWindow()
        try:
            window.resize(1640, 930)
            window.show()
            app().processEvents()

            self.assertEqual(window.command_bar.property('density'), 'spacious')
            self.assertTrue(window.command_scope_group.isVisibleTo(window))
            self.assertNotEqual(window.command_scope_layout.indexOf(window.filter_file), -1)
            self.assertNotEqual(window.command_scope_layout.indexOf(window.filter_instance), -1)
            self.assertNotEqual(window.command_scope_layout.indexOf(window.filter_different), -1)
            self.assertNotEqual(window.command_scope_layout.indexOf(window.filter_clear), -1)
            self.assertEqual(window.filter_layout.indexOf(window.filter_file), -1)
            self.assertEqual(window.filter_layout.indexOf(window.filter_instance), -1)
            self.assertEqual(window.filter_layout.indexOf(window.filter_different), -1)
            self.assertEqual(window.filter_layout.indexOf(window.filter_clear), -1)
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
            self.assertEqual(window.filter_original.text(), 'Untranslated 162.5k')
            self.assertEqual(window.filter_original.toolTip(), 'Untranslated: 162,527')
        finally:
            close_widget(window)

    def test_workspace_stats_skip_zero_draft_and_spell_out_package(self):
        window = MainWindow()
        original = record(FLAG_UNVALIDATED)
        approved = record(FLAG_VALIDATED)
        approved[RECORD_MAIN_ID] = 7
        draft = record(FLAG_TRANSLATED)
        draft[RECORD_MAIN_ID] = 9
        try:
            storage = app_state.packages_storage
            storage.packages.append(PackageStub())
            storage.model.replace([original, approved])
            storage.proxy.process_filter()

            window.update_workspace_summary()

            self.assertIn('1 package', window.workspace_summary.text())
            self.assertIn(' · ', window.workspace_summary.text())
            self.assertNotIn('|', window.workspace_summary.text())
            self.assertNotIn('pkg', window.workspace_summary.text())
            self.assertNotIn('draft', window.workspace_summary.text().lower())
            self.assertNotIn('draft', window.workspace_summary.toolTip().lower())

            storage.model.replace([original, approved, draft])
            storage.proxy.process_filter()
            window.update_workspace_summary()

            self.assertIn('1 draft', window.workspace_summary.text())
            self.assertIn('1 draft', window.workspace_summary.toolTip())
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
            self.assertIn('Untranslated 1', window.filter_original.text())
            self.assertIn('Approved 1', window.filter_validated.text())

            window.clear_filters()
            window.update_proxy()

            self.assertEqual({item.id for item in storage.model.filtered}, {42, 7})
            self.assertTrue(window.filter_original.isChecked())
            self.assertEqual(window.filter_search.text(), '')
        finally:
            close_widget(window)

    def test_modified_only_filter_uses_diff_logic_outside_main_status_chips(self):
        window = MainWindow()
        normal = record(FLAG_UNVALIDATED)
        modified = record(FLAG_UNVALIDATED)
        modified[RECORD_MAIN_ID] = 99
        modified.translate_old = 'Previous draft'
        try:
            storage = app_state.packages_storage
            storage.packages.append(PackageStub())
            storage.model.replace([normal, modified])
            storage.proxy.process_filter()
            window.set_state_menu()

            self.assertEqual(window.filter_different.text(), 'Modified only 1')
            self.assertEqual(window.filter_layout.indexOf(window.filter_different), -1)
            self.assertNotEqual(window.command_scope_layout.indexOf(window.filter_different), -1)

            window.filter_different.setChecked(True)
            window.update_proxy()

            self.assertEqual([item.id for item in storage.model.filtered], [99])
        finally:
            close_widget(window)

    def test_resize_keeps_loaded_rows_selection_and_scope_filter_widgets_stable(self):
        window = MainWindow()
        first = record(FLAG_UNVALIDATED)
        second = record(FLAG_VALIDATED)
        second[RECORD_MAIN_ID] = 7
        try:
            storage = app_state.packages_storage
            storage.packages.append(PackageStub())
            storage.model.replace([first, second])
            storage.proxy.process_filter()
            window.set_state_menu()
            window.clear_filters()
            window.update_proxy()
            window.resize(900, 620)
            window.show()
            app().processEvents()

            window.tableview.selectRow(0)
            app().processEvents()
            selected_before = window.tableview.selected_item()
            self.assertIsNotNone(selected_before)

            for size in ((1640, 930), (900, 620), (1500, 760)):
                window.resize(*size)
                app().processEvents()

                self.assertEqual(len(storage.model.filtered), 2)
                self.assertIs(window.tableview.selected_item(), selected_before)
                self.assertNotEqual(window.command_scope_layout.indexOf(window.filter_file), -1)
                self.assertNotEqual(window.command_scope_layout.indexOf(window.filter_instance), -1)
                self.assertNotEqual(window.command_scope_layout.indexOf(window.filter_clear), -1)
                self.assertEqual(window.filter_layout.indexOf(window.filter_file), -1)
                self.assertEqual(window.filter_layout.indexOf(window.filter_clear), -1)
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

            self.assertFalse(window.filter_search_mode.isVisibleTo(window))

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

    def test_advanced_search_modes_filter_without_mutating_records(self):
        window = MainWindow()
        starts = record(FLAG_UNVALIDATED)
        starts[RECORD_MAIN_ID] = 0x11111111
        starts[RECORD_MAIN_SOURCE] = 'Alpha begins here'
        starts[RECORD_MAIN_TRANSLATE] = 'Draft one'
        exact = record(FLAG_UNVALIDATED)
        exact[RECORD_MAIN_ID] = 0x22222222
        exact[RECORD_MAIN_SOURCE] = 'Middle text'
        exact[RECORD_MAIN_TRANSLATE] = 'Exact target'
        ends = record(FLAG_UNVALIDATED)
        ends[RECORD_MAIN_ID] = 0x33333333
        ends[RECORD_MAIN_SOURCE] = 'Line ends with Omega'
        ends[RECORD_MAIN_TRANSLATE] = 'Draft three'
        try:
            storage = app_state.packages_storage
            storage.packages.append(PackageStub())
            storage.model.replace([starts, exact, ends])
            storage.proxy.process_filter()
            window.set_state_menu()

            window.filter_advanced_toggle.setChecked(True)
            self.assertFalse(window.advanced_search_panel.isHidden())
            row, _column, _row_span, _column_span = window.filter_layout.getItemPosition(
                window.filter_layout.indexOf(window.advanced_search_panel)
            )
            self.assertEqual(row, 0)

            window.advanced_search_mode.setCurrentText('Exact')
            window.filter_search.setText('Exact target')
            window.update_proxy()
            self.assertEqual([item.id for item in storage.model.filtered], [0x22222222])

            window.advanced_search_mode.setCurrentText('Begins with')
            window.filter_search.setText('alpha')
            window.update_proxy()
            self.assertEqual([item.id for item in storage.model.filtered], [0x11111111])

            window.advanced_search_mode.setCurrentText('Ends with')
            window.filter_search.setText('omega')
            window.update_proxy()
            self.assertEqual([item.id for item in storage.model.filtered], [0x33333333])

            window.advanced_search_mode.setCurrentText('ID equals')
            window.filter_search.setText('0x22222222')
            window.update_proxy()
            self.assertEqual([item.id for item in storage.model.filtered], [0x22222222])
            self.assertEqual(exact.translate, 'Exact target')
        finally:
            close_widget(window)

    def test_advanced_regex_search_reports_invalid_pattern_without_crashing(self):
        window = MainWindow()
        item = record(FLAG_UNVALIDATED)
        try:
            storage = app_state.packages_storage
            storage.packages.append(PackageStub())
            storage.model.replace([item])
            storage.proxy.process_filter()
            window.set_state_menu()

            window.filter_advanced_toggle.setChecked(True)
            window.advanced_search_mode.setCurrentText('Regex')
            window.filter_search.setText('[')
            window.update_proxy()

            self.assertEqual(storage.model.filtered, [])
            self.assertIn('Invalid regex', window.advanced_search_warning.text())
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
            self.assertGreaterEqual(window.selection_original_text.height(), 64)
            self.assertGreaterEqual(window.selection_translation_text.height(), 64)
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
            self.assertEqual(window.inspector_status.text(), 'Needs review')
            self.assertEqual(window.inspector_apply.text(), 'Approve')
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
            self.assertEqual(dialog.suggestions_dock.objectName(), 'suggestionsDock')
            self.assertEqual(dialog.dictionary_panel.objectName(), 'sheetPanel')
            self.assertEqual(dialog.original_panel.objectName(), 'sheetPanel')
            self.assertEqual(dialog.translation_panel.objectName(), 'sheetPanel')
            self.assertEqual(dialog.edit_footer.objectName(), 'sheetFooter')
            self.assertEqual(dialog.edit_detail.objectName(), 'sheetHint')
            self.assertEqual(dialog.record_status.objectName(), 'editorMetaBadge')
            self.assertEqual(dialog.token_status.objectName(), 'tokenStatusBadge')
            self.assertEqual(dialog.token_detail.objectName(), 'tokenDetail')
            self.assertEqual(dialog.btn_ok.text(), 'Approve (Ctrl+Enter)')
            self.assertEqual(dialog.btn_review.text(), 'Needs Review')
            self.assertEqual(dialog.btn_tokens.text(), 'Tokens')
            self.assertEqual(dialog.token_assistant.objectName(), 'tokenAssistantPanel')
            self.assertFalse(dialog.token_assistant.isVisibleTo(dialog))
            self.assertTrue(dialog.btn_suggestions.isCheckable())
            self.assertTrue(dialog.btn_ok.isDefault())
            self.assertFalse(dialog.btn_review.autoDefault())
            self.assertFalse(dialog.btn_translate.autoDefault())
            self.assertFalse(dialog.btn_cancel.autoDefault())
        finally:
            close_widget(dialog)

    def test_edit_dialog_token_assistant_inserts_into_translation_only_and_refreshes_check(self):
        dialog = EditDialog()
        item = record(FLAG_PROGRESS)
        item[RECORD_MAIN_SOURCE] = '{0.SimFirstName} arrived'
        item.translate = 'arrived'
        try:
            dialog.prepare(item)
            original = dialog.txt_original.toPlainText()

            dialog.btn_tokens.setChecked(True)
            dialog.token_assistant.index.setValue(0)
            dialog.insert_token(dialog.token_assistant.current_token())

            self.assertEqual(dialog.txt_original.toPlainText(), original)
            self.assertIn('{0.SimFirstName}', dialog.txt_translate.toPlainText())
            self.assertIn('Token check: OK', dialog.token_status.text())

            dialog.token_assistant.male.setText('he')
            dialog.token_assistant.female.setText('she')
            self.assertEqual(dialog.token_assistant.current_token(), '{M0.he}{F0.she}')
            dialog.copy_token(dialog.token_assistant.current_token())
            self.assertEqual(QApplication.clipboard().text(), '{M0.he}{F0.she}')
        finally:
            close_widget(dialog)

    def test_edit_dialog_recovers_space_when_dictionary_suggestions_are_empty(self):
        dialog = EditDialog()
        try:
            dialog.prepare(record())
            dialog.show()
            app().processEvents()

            self.assertFalse(dialog.suggestions_splitter.isVisibleTo(dialog))
            self.assertFalse(dialog.suggestions_dock.isVisibleTo(dialog))
            self.assertTrue(dialog.translation_splitter.isVisibleTo(dialog))
            self.assertFalse(dialog.btn_suggestions.isEnabled())
            self.assertTrue(dialog.btn_ok.isDefault())
            self.assertFalse(dialog.btn_translate.autoDefault())
        finally:
            close_widget(dialog)

    def test_edit_dialog_suggestions_dock_can_expand_when_dictionary_data_exists(self):
        app_state.dictionaries_storage.model.append([['sample', 'Hello source', 'Bonjour dictionary', 12]])
        app_state.dictionaries_storage.proxy.filter('Hello')
        dialog = EditDialog()
        try:
            dialog.prepare(record())

            self.assertTrue(dialog.btn_suggestions.isEnabled())
            self.assertTrue(dialog.suggestions_dock.isHidden())

            dialog.btn_suggestions.setChecked(True)
            app().processEvents()

            self.assertFalse(dialog.suggestions_dock.isHidden())
            self.assertFalse(dialog.dictionary_panel.isHidden())
            self.assertFalse(dialog.search_panel.isHidden())
        finally:
            close_widget(dialog)

    def test_edit_dialog_keeps_escape_tokens_visible_for_highlighting(self):
        dialog = EditDialog()
        item = record()
        item[RECORD_MAIN_SOURCE] = 'Hello\\n\\n{0.SimFirstName}<b></b>'
        item[RECORD_MAIN_TRANSLATE] = 'Xin chao\\n{1.Money}<i></i>'
        try:
            dialog.prepare(item)

            self.assertIn('\\n\\n', dialog.txt_original.toPlainText())
            self.assertIn('{0.SimFirstName}', dialog.txt_original.toPlainText())
            self.assertIn('\\n', dialog.txt_translate.toPlainText())
            self.assertIn('{1.Money}', dialog.txt_translate.toPlainText())
        finally:
            close_widget(dialog)

    def test_edit_dialog_can_save_as_needs_review_or_approved(self):
        storage = app_state.packages_storage
        storage.packages.append(PackageStub())
        review_dialog = EditDialog()
        review_item = record(FLAG_UNVALIDATED)
        try:
            review_dialog.prepare(review_item)
            review_dialog.txt_translate.setPlainText('Needs more review')
            review_dialog.txt_comment.setText('Check token order')
            review_dialog.needs_review_click()

            self.assertEqual(review_item.translate, 'Needs more review')
            self.assertEqual(review_item.comment, 'Check token order')
            self.assertEqual(review_item.flag, FLAG_PROGRESS)
        finally:
            close_widget(review_dialog)

        approve_dialog = EditDialog()
        approved_item = record(FLAG_PROGRESS)
        try:
            approve_dialog.prepare(approved_item)
            approve_dialog.txt_translate.setPlainText('Ready text')
            approve_dialog.ok_click()

            self.assertEqual(approved_item.translate, 'Ready text')
            self.assertEqual(approved_item.flag, FLAG_VALIDATED)
        finally:
            close_widget(approve_dialog)

    def test_edit_dialog_approve_uses_soft_confirm_for_token_warning(self):
        storage = app_state.packages_storage
        storage.packages.append(PackageStub())
        item = record(FLAG_PROGRESS)
        item[RECORD_MAIN_SOURCE] = 'Hello\\n{0.SimFirstName}'
        item[RECORD_MAIN_TRANSLATE] = 'Bonjour'
        dialog = EditDialog()
        try:
            dialog.prepare(item)

            with patch('PySide6.QtWidgets.QMessageBox.question') as question, \
                    patch('PySide6.QtWidgets.QMessageBox.exec',
                          return_value=QMessageBox.StandardButton.No) as warning:
                dialog.ok_click()

            question.assert_not_called()
            warning.assert_called_once()
            self.assertEqual(item.flag, FLAG_PROGRESS)
            self.assertIn('Missing', dialog.token_status.text())
            self.assertIn('Continue only if', dialog.token_detail.text())

            box = dialog._EditDialog__build_token_warning_box('Approved', 'Missing tokens')
            try:
                self.assertEqual(box.button(QMessageBox.StandardButton.Yes).text(), 'Continue and Approve')
                self.assertEqual(box.button(QMessageBox.StandardButton.No).text(), 'Back to Edit')
            finally:
                close_widget(box)

            with patch('PySide6.QtWidgets.QMessageBox.exec',
                       return_value=QMessageBox.StandardButton.Yes) as warning:
                dialog.ok_click()

            warning.assert_called_once()
            self.assertEqual(item.flag, FLAG_VALIDATED)
            self.assertEqual(item.translate, 'Bonjour')
        finally:
            close_widget(dialog)

    def test_edit_dialog_needs_review_uses_soft_confirm_for_token_warning(self):
        storage = app_state.packages_storage
        storage.packages.append(PackageStub())
        item = record(FLAG_UNVALIDATED)
        item[RECORD_MAIN_SOURCE] = 'Hello {0.SimFirstName}'
        item[RECORD_MAIN_TRANSLATE] = 'Bonjour'
        dialog = EditDialog()
        try:
            dialog.prepare(item)

            with patch('PySide6.QtWidgets.QMessageBox.question') as question, \
                    patch('PySide6.QtWidgets.QMessageBox.exec',
                          return_value=QMessageBox.StandardButton.No) as warning:
                dialog.needs_review_click()

            question.assert_not_called()
            warning.assert_called_once()
            self.assertEqual(item.flag, FLAG_UNVALIDATED)
            self.assertIn('Missing', dialog.token_status.text())
            self.assertIn('Continue only if', dialog.token_detail.text())

            box = dialog._EditDialog__build_token_warning_box('Needs Review', 'Missing tokens')
            try:
                self.assertEqual(
                    box.button(QMessageBox.StandardButton.Yes).text(),
                    'Continue and Mark Needs Review',
                )
                self.assertEqual(box.button(QMessageBox.StandardButton.No).text(), 'Back to Edit')
            finally:
                close_widget(box)

            with patch('PySide6.QtWidgets.QMessageBox.exec',
                       return_value=QMessageBox.StandardButton.Yes) as warning:
                dialog.needs_review_click()

            warning.assert_called_once()
            self.assertEqual(item.flag, FLAG_PROGRESS)
        finally:
            close_widget(dialog)

    def test_edit_dialog_shortcuts_approve_and_needs_review(self):
        storage = app_state.packages_storage
        storage.packages.append(PackageStub())

        approve_item = record(FLAG_PROGRESS)
        approve_item[RECORD_MAIN_SOURCE] = 'Hello {0.SimFirstName}'
        approve_item[RECORD_MAIN_TRANSLATE] = 'Bonjour {0.SimFirstName}'
        approve_dialog = EditDialog()
        try:
            approve_dialog.prepare(approve_item)
            approve_dialog.keyPressEvent(QKeyEvent(
                QEvent.Type.KeyPress,
                Qt.Key.Key_Return,
                Qt.KeyboardModifier.ControlModifier,
            ))

            self.assertEqual(approve_item.flag, FLAG_VALIDATED)
        finally:
            close_widget(approve_dialog)

        review_item = record(FLAG_UNVALIDATED)
        review_dialog = EditDialog()
        try:
            review_dialog.prepare(review_item)
            review_dialog.keyPressEvent(QKeyEvent(
                QEvent.Type.KeyPress,
                Qt.Key.Key_Return,
                Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
            ))

            self.assertEqual(review_item.flag, FLAG_PROGRESS)
        finally:
            close_widget(review_dialog)

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
            self.assertTrue(hasattr(dialog, 'lbl_deepl_hint'))
            self.assertTrue(hasattr(dialog, 'txt_deepl_glossary_id'))
            self.assertTrue(hasattr(dialog, 'btn_deepl_test'))
            self.assertTrue(hasattr(dialog, 'btn_deepl_usage'))
            self.assertFalse(hasattr(dialog, 'btn_save'))
        finally:
            close_widget(dialog)
            close_widget(window)

    def test_options_dialog_life_studio_sections_and_action_icons_are_legible(self):
        window = MainWindow()
        dialog = OptionsDialog(window)
        try:
            self.assertGreaterEqual(dialog.minimumWidth(), 760)
            self.assertEqual(dialog.gb_safety.objectName(), 'optionsSection')
            self.assertEqual(dialog.gb_pack_manager.objectName(), 'optionsSection')
            self.assertEqual(dialog.tabs.count(), 3)
            self.assertEqual(dialog.tabs.tabText(dialog.tabs.indexOf(dialog.tab_general)), 'General')
            self.assertEqual(dialog.tabs.tabText(dialog.tabs.indexOf(dialog.tab_providers)), 'Providers')
            self.assertEqual(dialog.tabs.tabText(dialog.tabs.indexOf(dialog.tab_dictionaries)), 'Dictionaries')
            self.assertTrue(dialog.providers_scroll.widgetResizable())
            self.assertIs(dialog.providers_scroll.widget(), dialog.providers_content)
            self.assertIs(dialog.gb_deepl.parent(), dialog.providers_content)
            self.assertIs(dialog.gb_cache.parent(), dialog.providers_content)
            self.assertIsNot(dialog.gb_deepl.parent(), dialog.tab_general)
            self.assertEqual(dialog.gb_provider_deepl.objectName(), 'providerCard')
            self.assertEqual(dialog.gb_provider_gemini.objectName(), 'providerCard')
            self.assertEqual(dialog.gb_provider_openai.objectName(), 'providerCard')
            self.assertEqual(dialog.gb_provider_ollama.objectName(), 'providerCard')
            self.assertEqual(dialog.gb_provider_limits.objectName(), 'providerCard')
            self.assertEqual(dialog.tableview.objectName(), 'packManagerTable')
            self.assertGreaterEqual(dialog.tableview.verticalHeader().defaultSectionSize(), 32)

            for button, min_size in (
                    (dialog.btn_path, 20),
                    (dialog.btn_deepl_test, 20),
                    (dialog.btn_deepl_usage, 20),
                    (dialog.btn_gemini_test, 20),
                    (dialog.btn_openai_test, 20),
                    (dialog.btn_ollama_refresh, 20),
                    (dialog.btn_ollama_test, 20),
                    (dialog.btn_ollama_download, 20),
                    (dialog.btn_ollama_pull, 20),
                    (dialog.btn_ollama_cancel_pull, 20),
                    (dialog.btn_build, 22),
            ):
                self.assertFalse(button.icon().isNull())
                self.assertGreaterEqual(button.iconSize().width(), min_size)
                self.assertGreaterEqual(button.iconSize().height(), min_size)

            self.assertIn('·', dialog.lbl_pack_summary.text())
            self.assertTrue(dialog.lbl_safety_hint.wordWrap())
        finally:
            close_widget(dialog)
            close_widget(window)

    def test_options_dialog_uses_clear_safety_labels_and_dictionary_defaults(self):
        config.set_value('save', 'backup', ConfigManager.DEFAULTS['save']['backup'])
        config.set_value('save', 'experemental', ConfigManager.DEFAULTS['save']['experemental'])
        config.set_value('dictionaries', 'strong', ConfigManager.DEFAULTS['dictionaries']['strong'])

        window = MainWindow()
        dialog = OptionsDialog(window)
        try:
            self.assertTrue(ConfigManager.DEFAULTS['save']['backup'])
            self.assertFalse(ConfigManager.DEFAULTS['save']['experemental'])
            self.assertFalse(ConfigManager.DEFAULTS['dictionaries']['strong'])
            self.assertEqual(dialog.cb_backup.text(), 'Create backup before Finalize')
            self.assertEqual(dialog.cb_experemental.text(), 'Use conflict-free save mode (experimental)')
            self.assertEqual(dialog.cb_strong.text(), 'Only use exact dictionary matches')
            self.assertTrue(dialog.cb_backup.isChecked())
            self.assertFalse(dialog.cb_experemental.isChecked())
            self.assertFalse(dialog.cb_strong.isChecked())
            self.assertIn('.package.backup', dialog.cb_backup.toolTip())
            self.assertIn('fallback matches', dialog.cb_strong.toolTip())
        finally:
            close_widget(dialog)
            close_widget(window)

    def test_options_dialog_persists_language_pair_and_deepl_key_on_change(self):
        window = MainWindow()
        dialog = OptionsDialog(window)
        try:
            with patch.object(config, 'save') as save_mock:
                dialog.cb_dest.setCurrentText('VI_VN')
                dialog.language_change()
                dialog.txt_deepl_key.setText('sample:fx')
                dialog.change_deepl_key()
                dialog.txt_deepl_glossary_id.setText('glossary-123')
                dialog.change_deepl_glossary_id()
                dialog.txt_gemini_key.setText('gemini-secret')
                dialog.txt_gemini_model.setText('gemini-test')
                dialog.txt_openai_key.setText('openai-secret')
                dialog.txt_openai_base_url.setText('https://example.test')
                dialog.txt_openai_model.setText('openai-test')
                dialog.cb_ollama_enabled.setChecked(True)
                dialog.txt_ollama_base_url.setText('http://localhost:11434')
                dialog.cb_ollama_model.setCurrentText('translategemma:12b')
                dialog.txt_ai_session_cap.setText('1234')
                dialog.txt_ai_daily_cap.setText('5678')
                dialog.change_ai_provider_settings()
                dialog.cb_backup.setChecked(True)
                dialog.checkbox_click()

            self.assertEqual(config.value('translation', 'source'), 'ENG_US')
            self.assertEqual(config.value('translation', 'destination'), 'VI_VN')
            self.assertEqual(config.value('api', 'deepl_key'), 'sample:fx')
            self.assertEqual(config.value('api', 'deepl_glossary_id'), 'glossary-123')
            self.assertEqual(config.value('api', 'gemini_key'), 'gemini-secret')
            self.assertEqual(config.value('api', 'gemini_model'), 'gemini-test')
            self.assertEqual(config.value('api', 'openai_key'), 'openai-secret')
            self.assertEqual(config.value('api', 'openai_base_url'), 'https://example.test')
            self.assertEqual(config.value('api', 'openai_model'), 'openai-test')
            self.assertTrue(config.value('api', 'ollama_enabled'))
            self.assertEqual(config.value('api', 'ollama_base_url'), 'http://localhost:11434')
            self.assertEqual(config.value('api', 'ollama_model'), 'translategemma:12b')
            self.assertEqual(config.value('api', 'ai_session_character_cap'), 1234)
            self.assertEqual(config.value('api', 'ai_daily_character_cap'), 5678)
            self.assertEqual(config.value('api', 'engine'), 'DeepL')
            self.assertTrue(config.value('save', 'backup'))
            self.assertGreaterEqual(save_mock.call_count, 5)
        finally:
            close_widget(dialog)
            close_widget(window)

    def test_main_window_options_refreshes_existing_translation_provider_lists(self):
        class FakeOptionsDialog:

            def __init__(self, _parent):
                pass

            def exec(self):
                pass

            def deleteLater(self):
                pass

        window = MainWindow()
        try:
            with patch('windows.main_window.OptionsDialog', FakeOptionsDialog), \
                    patch.object(window.edit_dialog, 'refresh_api_list') as edit_refresh, \
                    patch.object(window.translate_dialog, 'refresh_api_list') as translate_refresh:
                window.options()

            edit_refresh.assert_called_once()
            translate_refresh.assert_called_once()
        finally:
            close_widget(window)

    def test_configured_providers_refresh_into_batch_and_translation_studio_lists(self):
        config.set_value('translation', 'source', 'ENG_US')
        config.set_value('translation', 'destination', 'VI_VN')
        config.set_value('api', 'deepl_key', 'sample:fx')
        config.set_value('api', 'gemini_key', 'gemini-secret')
        config.set_value('api', 'gemini_model', 'gemini-test')
        config.set_value('api', 'openai_key', 'openai-secret')
        config.set_value('api', 'openai_base_url', 'https://example.test')
        config.set_value('api', 'openai_model', 'openai-test')
        config.set_value('api', 'ollama_enabled', True)
        config.set_value('api', 'ollama_model', OLLAMA_RECOMMENDED_MODEL)

        translate_dialog = TranslateDialog()
        edit_dialog = EditDialog()
        try:
            translate_dialog.refresh_api_list()
            edit_dialog.refresh_api_list()
            translate_engines = [
                translate_dialog.cb_api.itemText(index)
                for index in range(translate_dialog.cb_api.count())
            ]
            edit_engines = [
                edit_dialog.cb_api.itemText(index)
                for index in range(edit_dialog.cb_api.count())
            ]

            for engine in ('DeepL', 'Gemini', 'OpenAI-compatible', 'Ollama'):
                self.assertIn(engine, translate_engines)
                self.assertIn(engine, edit_engines)
        finally:
            close_widget(edit_dialog)
            close_widget(translate_dialog)

    def test_options_dialog_refreshes_ollama_models_and_keeps_recommended_hint(self):
        window = MainWindow()
        dialog = OptionsDialog(window)
        try:
            dialog.show()
            app().processEvents()
            dialog.txt_ollama_base_url.setText('http://localhost:11434')
            dialog.cb_ollama_model.setCurrentText('custom-model:latest')
            dialog._OptionsDialog__apply_ollama_status(OllamaSetupStatus(
                installed=True,
                executable='C:/Program Files/Ollama/ollama.exe',
                server_reachable=True,
                models=('gemma4:e4b',),
                recommended_model_installed=False,
                message='Recommended model missing.',
            ))

            self.assertGreaterEqual(dialog.cb_ollama_model.findText('custom-model:latest'), 0)
            self.assertGreaterEqual(dialog.cb_ollama_model.findText('translategemma:12b'), 0)
            self.assertGreaterEqual(dialog.cb_ollama_model.findText('gemma4:e4b'), 0)
            self.assertEqual(dialog.cb_ollama_model.currentText(), 'custom-model:latest')
            self.assertIn('Recommended model missing', dialog.lbl_ollama_status.text())
            self.assertFalse(dialog.btn_ollama_pull.isHidden())
            self.assertTrue(dialog.btn_ollama_pull.isEnabled())
            self.assertTrue(dialog.btn_ollama_download.isHidden())
        finally:
            close_widget(dialog)
            close_widget(window)

    def test_options_dialog_shows_download_ollama_when_executable_is_missing(self):
        window = MainWindow()
        dialog = OptionsDialog(window)
        try:
            dialog.show()
            app().processEvents()
            dialog._OptionsDialog__apply_ollama_status(OllamaSetupStatus(
                installed=False,
                executable='',
                server_reachable=False,
                models=(),
                recommended_model_installed=False,
                message='Ollama missing.',
            ))

            self.assertIn('Ollama missing', dialog.lbl_ollama_status.text())
            self.assertFalse(dialog.btn_ollama_download.isHidden())
            self.assertTrue(dialog.btn_ollama_pull.isHidden())
            self.assertFalse(dialog.btn_ollama_test.isEnabled())
        finally:
            close_widget(dialog)
            close_widget(window)

    def test_options_dialog_download_ollama_button_opens_official_url(self):
        window = MainWindow()
        dialog = OptionsDialog(window)
        try:
            with patch('windows.options_dialog.QDesktopServices.openUrl', return_value=True) as open_url:
                dialog.download_ollama()

            open_url.assert_called_once()
            self.assertEqual(open_url.call_args.args[0].toString(), OLLAMA_DOWNLOAD_URL)
            self.assertIn('official Ollama download page', dialog.lbl_ollama_status.text())
        finally:
            close_widget(dialog)
            close_widget(window)

    def test_options_dialog_pull_success_selects_and_enables_recommended_model(self):
        window = MainWindow()
        dialog = OptionsDialog(window)
        try:
            fake_handle = object()
            dialog.cb_ollama_enabled.setChecked(False)
            setattr(dialog, '_OptionsDialog__ollama_pull_handle', fake_handle)
            dialog._OptionsDialog__ollama_pull_result(
                OllamaPullResult(True, 'translategemma:12b', 'Downloaded translategemma:12b.'),
                fake_handle,
            )

            self.assertTrue(dialog.cb_ollama_enabled.isChecked())
            self.assertEqual(dialog.cb_ollama_model.currentText(), 'translategemma:12b')
            self.assertTrue(config.value('api', 'ollama_enabled'))
            self.assertEqual(config.value('api', 'ollama_model'), 'translategemma:12b')
            self.assertIn('Downloaded translategemma:12b', dialog.lbl_ollama_status.text())
        finally:
            close_widget(dialog)
            close_widget(window)

    def test_options_dialog_tests_provider_in_background_without_blocking_ui(self):
        window = MainWindow()
        dialog = OptionsDialog(window)
        try:
            with patch.object(dialog._OptionsDialog__provider_runner, 'start') as start:
                handle = type('Handle', (), {
                    'result': type('Signal', (), {'connect': lambda self, fn: None})(),
                    'error': type('Signal', (), {'connect': lambda self, fn: None})(),
                    'finished': type('Signal', (), {'connect': lambda self, fn: None})(),
                })()
                start.return_value = handle
                dialog.test_ai_provider('Ollama')

            start.assert_called_once()
            self.assertEqual(start.call_args.args[1], 'Ollama')
            self.assertEqual(start.call_args.args[2], 20)
            self.assertFalse(dialog.btn_ollama_test.isEnabled())
            self.assertIn('Checking Ollama', dialog.lbl_ollama_status.text())
        finally:
            close_widget(dialog)
            close_widget(window)

    def test_options_dialog_deepl_test_and_usage_render_usage_status(self):
        window = MainWindow()
        dialog = OptionsDialog(window)
        try:
            usage = DeepLUsage(200, 2500, 10000, '')
            dialog._OptionsDialog__set_deepl_usage_status(usage, validation_only=True)
            self.assertIn('Valid key', dialog.lbl_deepl_status.text())
            self.assertIn('2,500 / 10,000', dialog.lbl_deepl_status.text())

            dialog._OptionsDialog__set_deepl_usage_status(usage, validation_only=False)
            self.assertIn('DeepL usage', dialog.lbl_deepl_status.text())

            dialog._OptionsDialog__set_deepl_usage_status(
                DeepLUsage(403, 0, 0, 'Invalid API key.'),
                validation_only=True,
            )
            self.assertIn('Invalid API key', dialog.lbl_deepl_status.text())
        finally:
            close_widget(dialog)
            close_widget(window)

    def test_options_dialog_ollama_ready_status_distinguishes_disabled_and_enabled(self):
        window = MainWindow()
        dialog = OptionsDialog(window)
        try:
            dialog._OptionsDialog__apply_ollama_status(OllamaSetupStatus(
                installed=True,
                executable='C:/Program Files/Ollama/ollama.exe',
                server_reachable=True,
                models=(OLLAMA_RECOMMENDED_MODEL,),
                recommended_model_installed=True,
                message='Ready.',
            ))

            self.assertIn('disabled', dialog.lbl_ollama_status.text())
            self.assertIn('Enable', dialog.lbl_ollama_status.text())

            dialog.cb_ollama_enabled.setChecked(True)
            dialog.change_ai_provider_settings()

            self.assertIn('ready and enabled', dialog.lbl_ollama_status.text())
        finally:
            close_widget(dialog)
            close_widget(window)

    def test_batch_translate_deepl_cost_guard_shows_estimate_and_cancel_stops_jobs(self):
        config.set_value('api', 'deepl_key', 'sample:fx')
        config.set_value('api', 'engine', 'DeepL')
        config.set_value('translation', 'source', 'ENG_US')
        config.set_value('translation', 'destination', 'VI_VN')

        storage = app_state.packages_storage
        item = record(FLAG_UNVALIDATED)
        storage.model.items = [item]

        dialog = TranslateDialog()
        try:
            dialog.refresh_api_list()
            dialog.rb_all.setChecked(True)

            with patch.object(dialog, '_TranslateDialog__confirm_deepl_cost', return_value=False) as confirm, \
                    patch.object(dialog._TranslateDialog__runner, 'start') as start:
                dialog.translate()

            confirm.assert_called_once()
            start.assert_not_called()
            self.assertFalse(dialog._TranslateDialog__translating)

            with patch('windows.translate_dialog.deepl_usage',
                       return_value=DeepLUsage(200, 10, 1000, '')), \
                    patch('PySide6.QtWidgets.QMessageBox.exec',
                          return_value=QMessageBox.StandardButton.Yes) as exec_mock:
                accepted = dialog._TranslateDialog__confirm_deepl_cost([item])

            exec_mock.assert_called_once()
            self.assertTrue(accepted)
        finally:
            close_widget(dialog)

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

    def test_vietnamese_interface_language_is_available_with_english_fallback(self):
        languages = {lang.code: lang.name for lang in interface.languages}
        self.assertEqual(languages.get('vi_VN'), 'Vietnamese')
        window = MainWindow()
        dialog = OptionsDialog(window)

        config.set_value('interface', 'language', 'vi_VN')
        interface.reload()
        try:
            window.retranslate()
            self.assertGreaterEqual(dialog.cb_language.findData('vi_VN'), 0)
            self.assertEqual(interface.text('MainWindow', 'File'), 'Tệp')
            self.assertEqual(interface.text('MainWindow', 'Status Overview Bar'), 'Thanh tổng quan trạng thái')
            self.assertEqual(window.command_open.text(), 'Mở')
            self.assertEqual(window.command_dictionary.text(), 'Từ điển')
            self.assertFalse(hasattr(window, 'filter_title'))
            self.assertEqual(window.filter_advanced_toggle.text(), 'Nâng cao')
            self.assertEqual(window.inspector_apply.text(), 'Phê duyệt')
            self.assertEqual(interface.text('TokenValidation', 'Token check:'), 'Kiểm tra token:')
            self.assertEqual(interface.text('MainWindow', 'Untranslated source fallback'), 'Untranslated source fallback')
        finally:
            config.set_value('interface', 'language', 'en_US')
            interface.reload()
            close_widget(dialog)
            close_widget(window)

    def test_status_overview_bar_replaces_color_visualization_label_and_tooltip(self):
        window = MainWindow()
        item = record(FLAG_UNVALIDATED)
        before = list(item)
        try:
            self.assertFalse(ConfigManager.DEFAULTS['view']['colorbar'])
            self.assertEqual(window.action_colorbar.text(), 'Status Overview Bar')
            self.assertIn('status distribution', window.action_colorbar.toolTip())
            self.assertNotIn('Color visualization', window.action_colorbar.text())

            window.colorbar.update_colors(1, 2, 3, 4)
            self.assertIn('Approved 2', window.colorbar.toolTip())
            self.assertIn('Needs review 3', window.colorbar.toolTip())
            self.assertIn('Untranslated 4', window.colorbar.toolTip())
            self.assertEqual(list(item), before)
        finally:
            close_widget(window)


if __name__ == '__main__':
    unittest.main()
