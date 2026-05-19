# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from packer.resource import ResourceID
from singletons.config import config
from singletons.signals import window_signals
from singletons.state import app_state
from storages.package_tasks import DictionarySnapshot, PackageLoadRequest, load_packages_task
from storages.packages import PackagesStorage
from storages.records import RecordOccurrence
from storages.workspace_cache import WorkspaceCache
from utils.task_runner import CancellationToken, TaskReporter


def app():
    return QCoreApplication.instance() or QCoreApplication([])


def wait_for(handle, timeout=1000):
    loop = QEventLoop()
    handle.finished.connect(lambda _cancelled: loop.quit())
    QTimer.singleShot(timeout, loop.quit)
    loop.exec()


class FakeDictionariesStorage:

    loaded = True

    @staticmethod
    def search(sid=None, source=None):
        return []


class FakeContainer:

    rows = []

    def __init__(self, path):
        self.path = path
        self.fullname = path
        self.name = path.split('.')[0]
        self.key = path
        self.instances = []
        self.modified = False

    @property
    def is_package(self):
        return True

    def open(self):
        for row in self.rows:
            rid = row[0]
            if rid.hex_instance not in self.instances:
                self.instances.append(rid.hex_instance)
        return self.rows

    def set_loaded_metadata(self, instances, row_count):
        self.instances = list(instances)

    def modify(self, state=True):
        self.modified = state


class NoopReporter(TaskReporter):

    def __init__(self):
        pass

    def progress(self, current: int = 0, total: int = 0, message: str = '') -> None:
        pass


class DeduplicationTests(unittest.TestCase):

    def setUp(self):
        app()
        config.set_value('group', 'original', True)
        config.set_value('group', 'highbit', False)
        app_state.set_dictionaries_storage(FakeDictionariesStorage())
        app_state.set_current_package(None)
        app_state.set_current_instance(0)

    def test_workspace_cache_merges_exact_duplicates_only(self):
        cache = WorkspaceCache()
        rid_a = ResourceID(group=0, instance=1, type=0x220557DA)
        rid_b = ResourceID(group=0, instance=2, type=0x220557DA)

        cache.add((42, 'Hello', 'Bonjour'), RecordOccurrence(rid_a, 'a.package', (1, 1, 4, 4), ''))
        cache.add((42, 'Hello', 'Bonjour'), RecordOccurrence(rid_b, 'b.package', (2, 2, 5, 5), ''))
        cache.add((42, 'Hello', 'Salut'), RecordOccurrence(rid_b, 'b.package', (3, 3, 6, 6), ''))
        cache.commit()

        self.assertEqual(cache.stats(), (2, 2))

    def test_workspace_cache_bulk_insert_skips_exact_duplicate_occurrences(self):
        cache = WorkspaceCache()
        rid_a = ResourceID(group=0, instance=1, type=0x220557DA)
        rid_b = ResourceID(group=0, instance=2, type=0x220557DA)

        cache.add_many((
            ((42, 'Hello', 'Bonjour'), RecordOccurrence(rid_a, 'a.package', (1, 1, 4, 4), '')),
            ((42, 'Hello', 'Bonjour'), RecordOccurrence(rid_b, 'b.package', (2, 2, 5, 5), '')),
            ((42, 'Hello', 'Salut'), RecordOccurrence(rid_b, 'b.package', (3, 3, 6, 6), '')),
        ))
        cache.commit()

        self.assertEqual(cache.stats(), (2, 2))

    def test_package_load_deduplicates_exact_matches_and_preserves_variations(self):
        rid_a = ResourceID(group=0, instance=1, type=0x220557DA)
        rid_b = ResourceID(group=0, instance=2, type=0x220557DA)
        rid_c = ResourceID(group=0, instance=3, type=0x220557DA)
        rid_d = ResourceID(group=0, instance=4, type=0x220557DA)

        FakeContainer.rows = [
            (rid_a, 42, 'Hello', 'Bonjour', '', 1, 1),
            (rid_b, 42, 'Hello', 'Bonjour', '', 2, 2),
            (rid_c, 42, 'Hello', 'Salut', '', 3, 3),
            (rid_d, 42, 'Hi', 'Bonjour', '', 4, 4),
        ]

        storage = PackagesStorage()
        app_state.set_packages_storage(storage)

        with patch('storages.packages.Container', FakeContainer), patch('storages.package_tasks.Container', FakeContainer):
            storage.load('test.package')

        self.assertEqual(len(storage.model.items), 3)
        self.assertEqual(storage.model.items[0].occurrence_count, 1)
        self.assertEqual(storage.model.items[1].occurrence_count, 1)
        self.assertEqual(storage.model.items[2].occurrence_count, 1)
        self.assertEqual(storage.workspace_cache.stats(), (3, 3))

        expanded = storage.expand_items(storage.model.items)
        self.assertEqual(len(expanded), 3)
        filtered = storage.expand_items(storage.model.items, package='test.package', instance=rid_b.instance)
        self.assertEqual(len(filtered), 0)
        self.assertEqual(len(storage.get_stbl(convert=False)), 3)

    def test_package_load_reports_skipped_duplicate_rows_without_importing_them(self):
        rid_a = ResourceID(group=0, instance=1, type=0x220557DA)
        rid_b = ResourceID(group=0, instance=2, type=0x220557DA)
        rid_c = ResourceID(group=0, instance=3, type=0x220557DA)

        FakeContainer.rows = [
            (rid_a, 42, 'Hello', 'Bonjour', '', 1, 1),
            (rid_b, 42, 'Hello', 'Bonjour', '', 2, 2),
            (rid_c, 42, 'Hello', 'Salut', '', 3, 3),
        ]

        request = PackageLoadRequest(
            files=('test.package',),
            existing_package_keys=(),
            existing_record_keys=(),
            dictionaries=DictionarySnapshot(),
            strong_dictionary=False,
            group_original=True,
            group_highbit=False,
            file_message_template='Opening file {}...'
        )

        with patch('storages.package_tasks.Container', FakeContainer):
            result = load_packages_task(CancellationToken(), NoopReporter(), request)

        self.assertEqual(len(result.records), 2)
        self.assertEqual(len(result.occurrences), 2)
        self.assertEqual(result.skipped_duplicates, 1)

    def test_package_load_logs_non_modal_duplicate_summary(self):
        rid_a = ResourceID(group=0, instance=1, type=0x220557DA)
        rid_b = ResourceID(group=0, instance=2, type=0x220557DA)

        FakeContainer.rows = [
            (rid_a, 42, 'Hello', 'Bonjour', '', 1, 1),
            (rid_b, 42, 'Hello', 'Bonjour', '', 2, 2),
        ]

        storage = PackagesStorage()
        app_state.set_packages_storage(storage)
        messages = []
        window_signals.log.connect(messages.append)
        try:
            with patch('storages.packages.Container', FakeContainer), patch('storages.package_tasks.Container', FakeContainer):
                storage.load('test.package')
        finally:
            window_signals.log.disconnect(messages.append)

        self.assertTrue(any('Loaded 1 unique strings, skipped 1 duplicates' in message for message in messages))

    def test_filtering_skips_duplicate_occurrence_instances(self):
        rid_a = ResourceID(group=0, instance=1, type=0x220557DA)
        rid_b = ResourceID(group=0, instance=2, type=0x220557DA)

        FakeContainer.rows = [
            (rid_a, 42, 'Hello', 'Bonjour', '', 1, 1),
            (rid_b, 42, 'Hello', 'Bonjour', '', 2, 2),
        ]

        storage = PackagesStorage()
        app_state.set_packages_storage(storage)

        with patch('storages.packages.Container', FakeContainer), patch('storages.package_tasks.Container', FakeContainer):
            storage.load('test.package')

        self.assertEqual(len(storage.model.items), 1)
        self.assertEqual(storage.model.items[0].occurrence_count, 1)
        self.assertEqual(storage.items(instance=rid_b.instance), [])
        self.assertEqual(storage.primary_items(instance=rid_a.instance), storage.model.items)
        self.assertEqual(storage.primary_items(instance=rid_b.instance), [])
        self.assertEqual(len(storage.get_stbl(convert=False)), 1)

    def test_async_package_load_applies_deduplicated_rows_on_completion(self):
        rid_a = ResourceID(group=0, instance=1, type=0x220557DA)
        rid_b = ResourceID(group=0, instance=2, type=0x220557DA)

        FakeContainer.rows = [
            (rid_a, 42, 'Hello', 'Bonjour', '', 1, 1),
            (rid_b, 42, 'Hello', 'Bonjour', '', 2, 2),
        ]

        storage = PackagesStorage()
        app_state.set_packages_storage(storage)

        with patch('storages.packages.Container', FakeContainer), patch('storages.package_tasks.Container', FakeContainer):
            handle = storage.load('test.package', asynchronous=True)
            wait_for(handle)

        self.assertEqual(len(storage.model.items), 1)
        self.assertEqual(storage.model.items[0].occurrence_count, 1)


if __name__ == '__main__':
    unittest.main()
