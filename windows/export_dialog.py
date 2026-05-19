# -*- coding: utf-8 -*-

import operator
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog
from typing import List

from storages.package_tasks import (
    ExportRecordDTO,
    StructuredExportRequest,
    TranslationHubCsvRequest,
    TranslationHubCsvRow,
    export_structured_task,
    export_translation_hub_csv_task,
)
from storages.records import MainRecord

from .ui.export_dialog import Ui_ExportDialog

from singletons.config import config
from singletons.interface import interface
from singletons.signals import window_signals
from singletons.state import app_state
from utils.functions import opendir, save_xml, save_stbl, save_json, save_binary, savefile
from utils.constants import *
from utils.task_runner import TaskRunner


class ExportDialog(QDialog, Ui_ExportDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.__export = -1
        self.__runner = TaskRunner(max_threads=1, parent=self)
        self.__export_handle = None
        self.__export_failed = False

        self.cb_current_instance.clicked.connect(self.current_instance_click)
        self.cb_separate_instances.clicked.connect(self.separate_instances_click)
        self.cb_separate_packages.clicked.connect(self.separate_packages_click)

        self.btn_export.clicked.connect(self.export_click)
        self.btn_cancel.clicked.connect(self.cancel_click)

        self.retranslate()

    def retranslate(self):
        self.setWindowTitle(interface.text('ExportDialog', 'Export translate'))
        self.gb_rec.setTitle(interface.text('ExportDialog', 'Exported records'))
        self.rb_all.setText(interface.text('ExportDialog', 'Everything'))
        self.rb_translated.setText(interface.text('ExportDialog', 'Everything but untranslated strings'))
        self.rb_selection.setText(interface.text('ExportDialog', 'Selection only'))
        self.cb_current_instance.setText(interface.text('ExportDialog', 'Only selected instance'))
        self.cb_separate_instances.setText(interface.text('ExportDialog', 'Each instance as a separate file'))
        self.cb_separate_packages.setText(interface.text('ExportDialog', 'Each package as a separate file'))
        self.btn_export.setText(interface.text('ExportDialog', 'Export'))
        self.btn_cancel.setText(interface.text('ExportDialog', 'Cancel'))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.__export_handle:
            self.__export_handle.cancel()
        self.__export = -1

    def current_instance_click(self):
        if self.cb_current_instance.isChecked():
            self.cb_separate_instances.setChecked(False)
            self.cb_separate_instances.setEnabled(False)
            self.cb_separate_packages.setChecked(False)
            self.cb_separate_packages.setEnabled(False)
        else:
            self.cb_separate_instances.setEnabled(True)
            self.cb_separate_packages.setEnabled(True)

    def separate_instances_click(self):
        if self.cb_separate_instances.isChecked():
            self.cb_current_instance.setChecked(False)
            self.cb_current_instance.setEnabled(False)
            self.cb_separate_packages.setChecked(False)
            self.cb_separate_packages.setEnabled(False)
        else:
            self.cb_current_instance.setEnabled(True)
            self.cb_separate_packages.setEnabled(True)

    def separate_packages_click(self):
        if self.cb_separate_packages.isChecked():
            self.cb_current_instance.setChecked(False)
            self.cb_current_instance.setEnabled(False)
            self.cb_separate_instances.setChecked(False)
            self.cb_separate_instances.setEnabled(False)
        else:
            self.cb_current_instance.setEnabled(True)
            self.cb_separate_instances.setEnabled(True)

    def stbl(self):
        self.__exec(EXPORT_STBL)

    def xml(self):
        self.__exec(EXPORT_XML)

    def xml_dp(self):
        self.__exec(EXPORT_XML_DP)

    def json_s4s(self):
        self.__exec(EXPORT_JSON_S4S)

    def binary_s4s(self):
        self.__exec(EXPORT_BINARY_S4S)

    def translation_hub_csv(self):
        self.__exec(EXPORT_HUB_CSV)

    def __exec(self, export: int):
        self.__export = export

        self.cb_current_instance.setVisible(False)
        self.cb_separate_instances.setVisible(False)
        self.cb_separate_packages.setVisible(False)

        package = app_state.packages_storage.current_package
        instance = app_state.packages_storage.current_instance

        if self.__export != EXPORT_HUB_CSV:
            if package is not None and instance > 0 and len(package.instances) > 1:
                self.cb_current_instance.setVisible(True)

            if self.__export != EXPORT_STBL:
                if not package or len(package.instances) > 1:
                    self.cb_separate_instances.setVisible(True)

                if not package:
                    self.cb_separate_packages.setVisible(True)

        self.setMinimumHeight(0)
        self.adjustSize()
        self.setMinimumSize(self.size())

        self.exec()

    def export(self):
        filename = None
        directory = None

        current_instance = self.cb_current_instance.isVisible() and self.cb_current_instance.isChecked()
        separate_instances = self.cb_separate_instances.isVisible() and self.cb_separate_instances.isChecked()
        separate_packages = self.cb_separate_packages.isVisible() and self.cb_separate_packages.isChecked()

        storage = app_state.packages_storage

        if self.rb_selection.isChecked():
            items = app_state.tableview.selected_items()
        else:
            items = storage.primary_items()

        if self.__export == EXPORT_HUB_CSV:
            if not self.rb_selection.isChecked():
                items = storage.items()
            return self.export_translation_hub_csv(items)

        package = storage.current_package
        instance = storage.current_instance

        if self.rb_selection.isChecked():
            instances = {i.instance for i in items}
            packages = {i.package for i in items}

            one_instance = len(instances) == 1
            one_package = len(packages) == 1

            item = items[0] if items else None

            if self.__export == EXPORT_STBL:
                if one_instance:
                    if item:
                        filename = save_stbl(item.resource.filename)
                else:
                    directory = opendir()
            else:
                if separate_instances or separate_packages:
                    directory = opendir()
                else:
                    if one_instance:
                        if item:
                            if self.__export == EXPORT_JSON_S4S:
                                filename = save_json(item.resource.filename)
                            elif self.__export == EXPORT_BINARY_S4S:
                                filename = save_binary(item.resource.filename)
                            else:
                                filename = save_xml(item.resource.filename)
                    elif one_package and package:
                        if item:
                            if self.__export == EXPORT_JSON_S4S:
                                filename = save_json(package.name)
                            elif self.__export == EXPORT_BINARY_S4S:
                                filename = save_binary(package.name)
                            else:
                                filename = save_xml(package.name)
                    else:
                        directory = opendir()

        else:
            one_instance = package is not None and instance > 0 and len(package.instances) == 1

            if self.__export == EXPORT_STBL:
                if one_instance or current_instance and package:
                    items = storage.primary_items(package.key if package else None, instance)
                    item = items[0] if items else None
                    if item:
                        filename = save_stbl(item.resource.filename)
                else:
                    directory = opendir()
            else:
                if separate_instances or separate_packages:
                    directory = opendir()
                else:
                    if one_instance or current_instance and package:
                        items = storage.primary_items(package.key if package else None, instance)
                        item = items[0] if items else None
                        if item:
                            if self.__export == EXPORT_JSON_S4S:
                                filename = save_json(item.resource.filename)
                            elif self.__export == EXPORT_BINARY_S4S:
                                filename = save_binary(item.resource.filename)
                            else:
                                filename = save_xml(item.resource.filename)
                    elif package:
                        items = storage.primary_items(package.key)
                        if self.__export == EXPORT_JSON_S4S:
                            filename = save_json(package.name)
                        elif self.__export == EXPORT_BINARY_S4S:
                            filename = save_binary(package.name)
                        else:
                            filename = save_xml(package.name)
                    else:
                        if self.__export == EXPORT_JSON_S4S:
                            filename = save_json('translate_merged')
                        elif self.__export == EXPORT_BINARY_S4S:
                            filename = save_binary('translate_merged')
                        else:
                            filename = save_xml('translate_merged')

        items = sorted(items, key=operator.itemgetter(RECORD_MAIN_INDEX), reverse=False)

        if filename or directory:
            return self.export_structured(items, filename=filename, directory=directory)

        return None

    def export_click(self):
        self.__set_busy(True)
        handle = self.export()
        if handle is None:
            self.__set_busy(False)
            self.close()

    def cancel_click(self):
        if self.__export_handle:
            self.__export_handle.cancel()
            self.__set_busy(True, interface.text('System', 'Cancelling...'), cancelling=True)
        else:
            self.close()

    def export_structured(self, items: List[MainRecord], directory: str = None, filename: str = None):
        if self.__export_handle:
            self.__export_handle.cancel()

        message = interface.text('System', 'Exporting translate...')
        self.__export_failed = False
        request = StructuredExportRequest(
            export_type=self.__export,
            filename=filename or '',
            directory=directory or '',
            records=self.__export_records(items),
            include_untranslated=self.rb_all.isChecked(),
            separate_packages=self.cb_separate_packages.isVisible() and self.cb_separate_packages.isChecked(),
            package_names=tuple((package.key, package.name) for package in app_state.packages_storage.packages),
            destination_locale=config.value('translation', 'destination'),
            message=message,
        )

        self.__export_handle = self.__runner.start(
            export_structured_task,
            request,
            job_name=message
        )
        self.__set_busy(True, message)
        self.__export_handle.result.connect(self.__export_result)
        self.__export_handle.error.connect(
            lambda error, handle=self.__export_handle: self.__export_error(error, handle)
        )
        self.__export_handle.finished.connect(
            lambda cancelled, handle=self.__export_handle: self.__export_finished(cancelled, handle)
        )
        return self.__export_handle

    def export_translation_hub_csv(self, items: List[MainRecord]) -> None:
        filename = savefile('Sims 4 Translation Hub CSV (*.csv)', 'csv', 'translation_hub')
        if not filename:
            return

        if self.__export_handle:
            self.__export_handle.cancel()

        rows = tuple(
            TranslationHubCsvRow(
                string_id=item.id,
                source_text=item.source,
                translated_text=item.translate,
                flag=item.flag
            )
            for item in sorted(items, key=operator.itemgetter(RECORD_MAIN_INDEX), reverse=False)
        )
        message = interface.text('System', 'Exporting Translation Hub CSV...')
        self.__export_failed = False
        request = TranslationHubCsvRequest(
            path=filename,
            rows=rows,
            include_untranslated=self.rb_all.isChecked(),
            message=message
        )

        self.__export_handle = self.__runner.start(
            export_translation_hub_csv_task,
            request,
            job_name=message
        )
        self.__set_busy(True, message)
        self.__export_handle.result.connect(self.__export_result)
        self.__export_handle.error.connect(
            lambda error, handle=self.__export_handle: self.__export_error(error, handle)
        )
        self.__export_handle.finished.connect(
            lambda cancelled, handle=self.__export_handle: self.__export_finished(cancelled, handle)
        )
        return self.__export_handle

    @staticmethod
    def __export_records(items: List[MainRecord]) -> tuple:
        return tuple(ExportRecordDTO(
            resource=item.resource,
            string_id=item.id,
            source_text=item.source,
            translated_text=item.translate,
            flag=item.flag,
            package_key=item.package,
            comment=item.comment
        ) for item in items)

    @staticmethod
    def __export_result(result) -> None:
        if hasattr(result, 'files'):
            window_signals.log.emit(interface.text(
                'System',
                'Exported {} file(s), {} string(s)'
            ).format(len(result.files), result.string_count))
        elif hasattr(result, 'row_count'):
            window_signals.log.emit(interface.text(
                'System',
                'Exported {} file(s), {} string(s)'
            ).format(1, result.row_count))

    def __export_error(self, error, handle) -> None:
        if self.__export_handle is not handle:
            return
        self.__export_failed = True
        message = getattr(error, 'message', str(error))
        window_signals.log.emit(message)
        window_signals.message.emit(message)

    def __export_finished(self, cancelled: bool, handle) -> None:
        if self.__export_handle is handle:
            failed = self.__export_failed
            self.__export_handle = None
            self.__export_failed = False
            self.__set_busy(False)
            if not cancelled and not failed:
                self.close()

    def __set_busy(self, busy: bool, message: str = '', cancelling: bool = False) -> None:
        controls = (
            self.rb_all,
            self.rb_translated,
            self.rb_selection,
            self.cb_current_instance,
            self.cb_separate_instances,
            self.cb_separate_packages,
        )
        for control in controls:
            control.setEnabled(not busy)

        self.btn_export.setEnabled(not busy)
        self.btn_export.setText(message if busy and message else interface.text('ExportDialog', 'Export'))
        self.btn_cancel.setEnabled(not cancelling)
