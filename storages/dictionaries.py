# -*- coding: utf-8 -*-

import os
import zlib
import json
import glob
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal, QThreadPool, QRunnable

from packer import Packer

from models.dictionary import Model, ProxyModel

from singletons.config import config
from singletons.interface import interface
from singletons.signals import progress_signals, storage_signals, window_signals
from singletons.state import app_state
from utils.functions import text_to_stbl
from utils.task_runner import CancellationToken, TaskReporter, TaskRunner
from utils.constants import *


class StorageSignals(QObject):
    updated = Signal()


@dataclass(frozen=True)
class DictionaryLoadRequest:
    directory: str
    message: str


@dataclass(frozen=True)
class DictionaryLoadResult:
    sid_entries: tuple = ()
    source_entries: tuple = ()
    model_items: tuple = ()
    file_count: int = 0


class _NullReporter(TaskReporter):

    def __init__(self):
        pass

    def progress(self, current: int = 0, total: int = 0, message: str = '') -> None:
        pass


def load_dictionaries_task(
        token: CancellationToken,
        reporter: TaskReporter,
        request: DictionaryLoadRequest
) -> DictionaryLoadResult:
    dictionary_files = glob.glob(os.path.join(request.directory, '*.dct'))
    sid_entries = {}
    source_entries = {}
    hash_entries = {}

    if dictionary_files:
        reporter.progress(0, len(dictionary_files), request.message)

    for filename in dictionary_files:
        token.raise_if_cancelled()
        dictionary_name = os.path.splitext(os.path.basename(filename))[0]

        with open(filename, 'rb') as fp:
            packer = Packer(fp.read(), mode='r')

        if packer.get_raw_bytes(3) == b'DCT':
            version = packer.get_byte()
            items = packer.get_json()
        else:
            content = zlib.decompress(packer.get_content()).decode('utf-8')
            version = 1
            items = json.loads(content)

        _read_dictionary(dictionary_name, version, items, sid_entries, source_entries, hash_entries)
        reporter.progress(1, 0, '')

    return DictionaryLoadResult(
        sid_entries=tuple((sid, tuple(entries)) for sid, entries in sid_entries.items()),
        source_entries=tuple((source, tuple(translations)) for source, translations in source_entries.items()),
        model_items=tuple(tuple(item) for item in hash_entries.values()),
        file_count=len(dictionary_files)
    )


def _read_dictionary(
        dictionary_name: str,
        version: int,
        items: list,
        sid_entries: dict,
        source_entries: dict,
        hash_entries: dict
) -> None:
    name = dictionary_name.lower()

    for item in items:
        item = list(item)
        if version == 1:
            item[0] = int(item[0], 16)
            item.append(0)

        if version < 3:
            item.append('')

        if version < 4:
            item.pop(3)

        if item[1] and item[1] != item[2]:
            _update_hash(name, item, sid_entries, source_entries, hash_entries)


def _update_hash(name: str, item: list, sid_entries: dict, source_entries: dict, hash_entries: dict):
    sid_entries.setdefault(item[0], []).append((name, item[1], item[2], item[3]))

    if item[1] not in source_entries:
        source_entries[item[1]] = []
    if item[2] not in source_entries[item[1]]:
        source_entries[item[1]].append(item[2])

    key = f'{item[1]}__{item[2]}'
    if key not in hash_entries:
        hash_entries[key] = [name, item[1], item[2], len(item[1])]


class UpdaterWorker(QRunnable):

    def __init__(self, item):
        super().__init__()

        self.item = item

        self.signals = StorageSignals()

    def run(self):
        source = text_to_stbl(self.item.source)
        translate = text_to_stbl(self.item.translate)
        found = self._update_or_append(source, translate)
        if not found:
            app_state.dictionaries_storage.model.append(['-', source, translate, len(source)])
        storage_signals.updated.emit()

    @staticmethod
    def _update_or_append(source, translate):
        for model_item in app_state.dictionaries_storage.model.items:
            if model_item[RECORD_DICTIONARY_SOURCE] == source and model_item[RECORD_DICTIONARY_PACKAGE] == '-':
                model_item[RECORD_DICTIONARY_TRANSLATE] = translate
                return True
        return False


class DictionariesStorage:

    def __init__(self) -> None:
        self.model = Model()
        self.proxy = ProxyModel()
        self.proxy.setSourceModel(self.model)

        self.directory = config.value('dictionaries', 'dictpath')
        if not self.directory:
            self.directory = os.path.abspath('./dictionary')

        self.loaded = False

        self.signals = StorageSignals()

        self.__sid = {}
        self.__sources = {}
        self.__hash = {}

        self.__pool = QThreadPool()
        self.__runner = TaskRunner(max_threads=1)
        self.__load_handle = None

    def search(self, sid: int = None, source: str = None) -> list:
        if sid:
            return self.__sid.get(sid, [])
        elif source:
            return self.__sources.get(source, [])
        return []

    def snapshot(self) -> tuple:
        return (
            tuple((sid, tuple(entries)) for sid, entries in self.__sid.items()),
            tuple((source, tuple(entries)) for source, entries in self.__sources.items())
        )

    def load(self, asynchronous: bool = False):
        request = DictionaryLoadRequest(
            directory=self.directory,
            message=interface.text('System', 'Loading dictionaries...')
        )

        if asynchronous:
            if self.__load_handle:
                self.__load_handle.cancel()

            self.__load_handle = self.__runner.start(
                load_dictionaries_task,
                request,
                job_name=request.message
            )
            self.__load_handle.progress.connect(self.__task_progress)
            self.__load_handle.result.connect(self.__loaded_async)
            self.__load_handle.error.connect(self.__load_error)
            self.__load_handle.finished.connect(
                lambda cancelled, handle=self.__load_handle: self.__load_finished(cancelled, handle)
            )
            return self.__load_handle

        result = load_dictionaries_task(CancellationToken(), _NullReporter(), request)
        self.__apply_load_result(result)
        return None

    def __loaded_async(self, result: DictionaryLoadResult) -> None:
        self.__apply_load_result(result)
        progress_signals.finished.emit()

    def __apply_load_result(self, result: DictionaryLoadResult) -> None:
        self.__sid = {sid: list(entries) for sid, entries in result.sid_entries}
        self.__sources = {source: list(translations) for source, translations in result.source_entries}
        self.__hash = {}

        self.model.replace([list(item) for item in result.model_items])
        self.signals.updated.emit()
        self.loaded = True

    @staticmethod
    def __task_progress(progress) -> None:
        if progress.message:
            progress_signals.initiate.emit(progress.message, int(progress.total))
        elif progress.current:
            progress_signals.increment.emit()

    @staticmethod
    def __load_error(error) -> None:
        progress_signals.finished.emit()
        window_signals.message.emit(error.message)

    def __load_finished(self, cancelled: bool, handle) -> None:
        if cancelled:
            progress_signals.finished.emit()
        if self.__load_handle is handle:
            self.__load_handle = None

    def read_dictionary(self, dictionary_name: str, version: int, items: list) -> None:
        name = dictionary_name.lower()

        for i, item in enumerate(items):
            if version == 1:
                item[0] = int(item[0], 16)
                item.append(0)

            if version < 3:
                item.append('')

            if version < 4:
                item.pop(3)

            if item[1] and item[1] != item[2]:
                self.update_hash(name, item)

    def update_hash(self, name: str, item: list):
        self.__sid.setdefault(item[0], []).append((name, item[1], item[2], item[3]))

        if item[1] not in self.__sources:
            self.__sources[item[1]] = []
        if item[2] not in self.__sources[item[1]]:
            self.__sources[item[1]].append(item[2])

        k = f'{item[1]}__{item[2]}'
        if k not in self.__hash:
            self.__hash[k] = [name, item[1], item[2], len(item[1])]

    def update(self, item):
        if not item.compare():
            worker = UpdaterWorker(item)
            worker.setAutoDelete(True)
            self.__pool.start(worker)

    def save(self, force: bool = False, multi: bool = False):
        storage = app_state.packages_storage
        package = storage.current_package
        if multi or package is None:
            for p in storage.packages:
                if p.modified or force:
                    self.save_standalone(p.name, storage.items(key=p.key))
                    p.modify(False)
        elif package is not None and (package.modified or force):
            self.save_standalone(package.name, storage.items(key=package.key))
            package.modify(False)

    def save_standalone(self, name, items):
        if not os.path.isdir(self.directory):
            os.mkdir(self.directory)

        path = os.path.join(self.directory, name + '.dct')

        f = Packer(b'', mode='w')

        f.put_raw_bytes(b'DCT')
        f.put_byte(DICTIONARY_VERSION)

        _items = []

        for item in items:
            if item.flag != FLAG_UNVALIDATED and item.source:
                _items.append([
                    item.id,
                    text_to_stbl(item.source),
                    text_to_stbl(item.translate),
                    item.comment
                ])

        f.put_json(_items)

        with open(path, 'w+b') as fp:
            fp.write(f.get_content())
