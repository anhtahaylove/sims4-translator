# -*- coding: utf-8 -*-

import json
import os
import tempfile
import unittest
import xml.etree.ElementTree as ElementTree

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from packer.resource import ResourceID
from packer.stbl import Stbl
from scripts.synthetic_package import create_synthetic_package, read_resource_content, read_stbl_by_locale
from singletons.config import config
from singletons.signals import window_signals
from singletons.state import app_state
from storages.package_tasks import (
    ExportRecordDTO,
    StructuredExportRequest,
    export_structured_task,
)
from storages.packages import PackagesStorage
from utils.constants import (
    EXPORT_BINARY_S4S,
    EXPORT_JSON_S4S,
    EXPORT_STBL,
    EXPORT_XML,
    FLAG_VALIDATED,
)
from utils.task_runner import CancellationToken, TaskReporter


def app():
    return QCoreApplication.instance() or QCoreApplication([])


def wait_for(handle, timeout=1000):
    loop = QEventLoop()
    handle.finished.connect(lambda _cancelled: loop.quit())
    QTimer.singleShot(timeout, loop.quit)
    loop.exec()


class NoopReporter(TaskReporter):

    def __init__(self):
        pass

    def progress(self, current: int = 0, total: int = 0, message: str = '') -> None:
        pass


class FakeDictionariesStorage:

    loaded = True

    @staticmethod
    def search(sid=None, source=None):
        return []

    @staticmethod
    def snapshot():
        return (), ()


def export_records(storage):
    return tuple(ExportRecordDTO(
        resource=item.resource,
        string_id=item.id,
        source_text=item.source,
        translated_text=item.translate,
        flag=item.flag,
        package_key=item.package,
        comment=item.comment,
    ) for item in storage.model.items)


def export_request(export_type, path, records):
    return StructuredExportRequest(
        export_type=export_type,
        filename=path,
        records=records,
        include_untranslated=True,
        destination_locale='FRE_FR',
        message='Exporting translate...',
    )


class SyntheticPackageIntegrationTests(unittest.TestCase):

    def setUp(self):
        app()
        config.set_value('translation', 'source', 'ENG_US')
        config.set_value('translation', 'destination', 'FRE_FR')
        config.set_value('group', 'original', True)
        config.set_value('group', 'highbit', False)
        config.set_value('save', 'experemental', False)
        config.set_value('save', 'backup', False)
        config.set_value('dictionaries', 'strong', False)
        app_state.set_dictionaries_storage(FakeDictionariesStorage())
        app_state.set_current_package(None)
        app_state.set_current_instance(0)

    def test_load_synthetic_package_dedupes_and_exports_all_formats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            package_path = os.path.join(tmpdir, 'synthetic.package')
            create_synthetic_package(package_path)

            storage = PackagesStorage()
            app_state.set_packages_storage(storage)
            storage.load(package_path)

            self.assertEqual(len(storage.model.items), 2)
            self.assertEqual(storage.workspace_cache.stats(), (2, 2))
            self.assertEqual(
                {(item.id, item.source, item.translate) for item in storage.model.items},
                {(42, 'Hello', 'Bonjour'), (7, 'World', 'Monde')}
            )

            records = export_records(storage)
            stbl_path = os.path.join(tmpdir, 'out.stbl')
            xml_path = os.path.join(tmpdir, 'out.xml')
            json_path = os.path.join(tmpdir, 'out.json')
            binary_path = os.path.join(tmpdir, 'out.binary')

            export_structured_task(CancellationToken(), NoopReporter(), export_request(EXPORT_STBL, stbl_path, records))
            export_structured_task(CancellationToken(), NoopReporter(), export_request(EXPORT_XML, xml_path, records))
            export_structured_task(CancellationToken(), NoopReporter(), export_request(EXPORT_JSON_S4S, json_path, records))
            export_structured_task(CancellationToken(), NoopReporter(), export_request(EXPORT_BINARY_S4S, binary_path, records))

            with open(stbl_path, 'rb') as fp:
                stbl_strings = Stbl(ResourceID(group=0, instance=1, type=0x220557DA), fp.read()).strings
            xml_root = ElementTree.parse(xml_path).getroot()
            with open(json_path, 'r', encoding='utf-8') as fp:
                json_data = json.load(fp)
            with open(binary_path, 'rb') as fp:
                binary_strings = Stbl(ResourceID(group=0, instance=1, type=0x220557DA), fp.read()).strings

        self.assertEqual(stbl_strings, {42: 'Bonjour', 7: 'Monde'})
        self.assertEqual(len(xml_root.findall('.//String')), 2)
        self.assertEqual(json_data['Entries'], [
            {'Key': '0x0000002A', 'Value': 'Bonjour'},
            {'Key': '0x00000007', 'Value': 'Monde'},
        ])
        self.assertEqual(binary_strings, {42: 'Bonjour', 7: 'Monde'})

    def test_save_synthetic_package_writes_unique_destination_stbl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            package_path = os.path.join(tmpdir, 'synthetic.package')
            saved_path = os.path.join(tmpdir, 'saved.package')
            create_synthetic_package(package_path)

            storage = PackagesStorage()
            app_state.set_packages_storage(storage)
            storage.load(package_path)
            for item in storage.model.items:
                if item.id == 42:
                    item.translate = 'Salut'
                item.flag = FLAG_VALIDATED

            result = storage.save(saved_path, asynchronous=False)
            dest_tables = read_stbl_by_locale(saved_path, 'FRE_FR')

            self.assertEqual(result.resource_count, 1)
            self.assertFalse(os.path.exists(saved_path + '.tmp'))
            self.assertEqual(len(dest_tables), 1)
            self.assertEqual(next(iter(dest_tables.values())), {42: 'Salut', 7: 'Monde'})

    def test_async_save_logs_non_modal_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            package_path = os.path.join(tmpdir, 'synthetic.package')
            saved_path = os.path.join(tmpdir, 'saved.package')
            create_synthetic_package(package_path)

            storage = PackagesStorage()
            app_state.set_packages_storage(storage)
            storage.load(package_path)
            for item in storage.model.items:
                item.flag = FLAG_VALIDATED

            messages = []
            window_signals.log.connect(messages.append)
            try:
                handle = storage.save(saved_path, asynchronous=True)
                wait_for(handle)
            finally:
                window_signals.log.disconnect(messages.append)

            self.assertTrue(os.path.exists(saved_path))
            self.assertTrue(any('saved.package' in message and '1 resource' in message for message in messages))

    def test_finalize_synthetic_package_replaces_destination_and_preserves_other_resources(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            package_path = os.path.join(tmpdir, 'unique.package')
            target_path = os.path.join(tmpdir, 'finalized.package')
            info = create_synthetic_package(package_path, include_duplicate=False)

            storage = PackagesStorage()
            app_state.set_packages_storage(storage)
            storage.load(package_path)
            translations = {42: 'Salut', 7: 'Terre'}
            for item in storage.model.items:
                item.translate = translations[item.id]
                item.flag = FLAG_VALIDATED

            result = storage.finalize(package_path, target_path, asynchronous=False)
            dest_tables = read_stbl_by_locale(target_path, 'FRE_FR')

            self.assertEqual(result.resource_count, 1)
            self.assertFalse(os.path.exists(target_path + '.tmp'))
            self.assertEqual(dest_tables[info.destination], translations)
            self.assertEqual(read_resource_content(target_path, info.extra), b'non-stbl-payload')

    def test_finalize_synthetic_package_appends_missing_destination_stbl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            package_path = os.path.join(tmpdir, 'source_only.package')
            target_path = os.path.join(tmpdir, 'finalized.package')
            info = create_synthetic_package(package_path, include_destination=False, include_duplicate=False)

            storage = PackagesStorage()
            app_state.set_packages_storage(storage)
            storage.load(package_path)
            translations = {42: 'Salut', 7: 'Terre'}
            for item in storage.model.items:
                item.translate = translations[item.id]
                item.flag = FLAG_VALIDATED

            result = storage.finalize(package_path, target_path, asynchronous=False)
            source_tables = read_stbl_by_locale(target_path, 'ENG_US')
            dest_tables = read_stbl_by_locale(target_path, 'FRE_FR')

            self.assertEqual(result.resource_count, 1)
            self.assertEqual(source_tables[info.source], {42: 'Hello', 7: 'World'})
            self.assertEqual(dest_tables[info.destination], translations)
            self.assertEqual(read_resource_content(target_path, info.extra), b'non-stbl-payload')


if __name__ == '__main__':
    unittest.main()
