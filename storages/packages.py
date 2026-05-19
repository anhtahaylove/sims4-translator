# -*- coding: utf-8 -*-

import os
import operator
import gc
import json
import xml.etree.ElementTree as ElementTree
from json import JSONDecodeError
from PySide6.QtCore import QObject, Signal
from typing import Union, Dict, List
from pathlib import Path

from packer.dbpf import DbpfPackage
from packer.resource import ResourceID
from packer.stbl import Stbl

from .container import Container
from .records import MainRecord, RecordOccurrence
from .package_tasks import (
    DictionarySnapshot,
    FinalizePackageRequest,
    PackageLoadRequest,
    SavePackageRequest,
    SaveStringDTO,
    finalize_package_task,
    load_packages_task,
    save_package_task,
)
from .workspace_cache import WorkspaceCache

from models.main import Model, ProxyModel

from singletons.config import config
from singletons.interface import interface
from singletons.signals import progress_signals, window_signals
from singletons.state import app_state
from singletons.undo import undo
from utils.task_runner import CancellationToken, TaskReporter, TaskRunner
from utils.functions import text_to_stbl, fnv64, prettify
from utils.constants import *


class StorageSignals(QObject):
    loaded = Signal(list)
    closed = Signal(str)
    cleared = Signal()


class _NullReporter(TaskReporter):

    def __init__(self):
        pass

    def progress(self, current: int = 0, total: int = 0, message: str = '') -> None:
        pass


class PackagesStorage(QObject):

    def __init__(self) -> None:
        super().__init__()

        self.packages: List[Container] = []

        self.model = Model()
        self.proxy = ProxyModel()
        self.proxy.setSourceModel(self.model)
        self.workspace_cache = WorkspaceCache()
        self.__runner = TaskRunner(max_threads=1, parent=self)
        self.__load_handle = None
        self.__save_handle = None

        self.signals = StorageSignals()

    def find(self, key: str) -> Union[Container, None]:
        for package in self.packages:
            if package.key == key:
                return package
        return None

    def exists(self, key: str) -> bool:
        package = self.find(key)
        return package is not None

    @property
    def current_package(self) -> Container:
        key = app_state.current_package
        return self.find(key) if key else None

    @property
    def current_instance(self) -> int:
        return app_state.current_instance

    @property
    def modified(self) -> bool:
        for package in self.packages:
            if package.modified:
                return True
        return False

    @property
    def enabled(self) -> bool:
        return len(self.packages) > 0

    @property
    def multiplied(self) -> bool:
        return len(self.packages) > 1

    def modify(self, state: bool = True) -> None:
        for package in self.packages:
            package.modify(state)

    def items(self, key: str = None, instance: int = 0) -> List[MainRecord]:
        items = self.model.items

        if key or instance:
            if instance > 0:
                items = [i for i in items if i.has_occurrence(package=key, instance=instance)]
            elif key:
                items = [i for i in items if i.has_package(key)]

        else:
            package_key = app_state.current_package
            package_instance = app_state.current_instance

            if package_instance > 0:
                items = [i for i in items if i.has_occurrence(package=package_key, instance=package_instance)]
            elif package_key:
                items = [i for i in items if i.has_package(package_key)]

        return items

    def primary_items(self, key: str = None, instance: int = 0) -> List[MainRecord]:
        items = self.model.items

        if key:
            items = [item for item in items if item.package == key]

        if instance:
            items = [item for item in items if item.instance == instance]

        return items

    @staticmethod
    def expand_items(items: List[MainRecord], package: str = None, instance: int = 0) -> List[MainRecord]:
        expanded = []
        for item in items:
            expanded.extend(item.expanded(package=package, instance=instance))
        return expanded

    def load(self, files: Union[list, str], added: bool = False, asynchronous: bool = False):
        if not isinstance(files, list):
            files = [files]

        if not added:
            self.close()

        request = self.__build_load_request(files)

        if asynchronous:
            return self.__start_load(request, len(files))

        result = load_packages_task(CancellationToken(), _NullReporter(), request)
        self.__apply_load_result(result, len(files))
        return None

    def __start_load(self, request: PackageLoadRequest, file_count: int):
        if self.__load_handle:
            self.__load_handle.cancel()

        progress_signals.initiate.emit(
            interface.text('System', 'Opening files...') if file_count > 1 else interface.text('System', 'Opening file...'),
            0
        )

        self.__load_handle = self.__runner.start(
            load_packages_task,
            request,
            job_name=interface.text('System', 'Opening files...') if file_count > 1 else interface.text('System',
                                                                                                        'Opening file...')
        )
        self.__load_handle.progress.connect(self.__task_progress)
        self.__load_handle.result.connect(lambda result, count=file_count: self.__loaded_async(result, count))
        self.__load_handle.error.connect(self.__load_error)
        self.__load_handle.finished.connect(lambda cancelled, handle=self.__load_handle: self.__load_finished(cancelled, handle))
        return self.__load_handle

    def __build_load_request(self, files: list) -> PackageLoadRequest:
        dictionaries = self.__dictionary_snapshot()
        return PackageLoadRequest(
            files=tuple(files),
            existing_package_keys=tuple(package.key for package in self.packages),
            existing_record_keys=tuple(item.dedupe_key for item in self.model.items),
            dictionaries=dictionaries,
            strong_dictionary=config.value('dictionaries', 'strong'),
            group_original=config.value('group', 'original'),
            group_highbit=config.value('group', 'highbit'),
            file_message_template=interface.text('System', 'Opening file {}...')
        )

    @staticmethod
    def __dictionary_snapshot() -> DictionarySnapshot:
        dictionaries_storage = app_state.dictionaries_storage
        if dictionaries_storage and hasattr(dictionaries_storage, 'snapshot'):
            sid_entries, source_entries = dictionaries_storage.snapshot()
            return DictionarySnapshot(sid_entries=sid_entries, source_entries=source_entries)
        return DictionarySnapshot()

    def __loaded_async(self, result, file_count: int) -> None:
        self.__apply_load_result(result, file_count)
        progress_signals.finished.emit()

    def __apply_load_result(self, result, file_count: int) -> None:
        idx_all = len(self.model.items) + 1
        dedupe_index = {item.dedupe_key: item for item in self.model.items}
        record_data = {record.key: record for record in result.records}
        items = []
        cache_entries = []

        for package_data in result.packages:
            package = Container(package_data.path)
            package.set_loaded_metadata(package_data.instances, package_data.row_count)
            self.packages.append(package)

        for occurrence_data in result.occurrences:
            occurrence = RecordOccurrence(
                occurrence_data.resource_original,
                occurrence_data.package_key,
                occurrence_data.index_alt,
                occurrence_data.comment
            )
            cache_entries.append((occurrence_data.key, occurrence))

            existing = dedupe_index.get(occurrence_data.key)
            if existing:
                existing.add_occurrence(occurrence)
                continue

            record = record_data.get(occurrence_data.key)
            if record is None:
                continue

            item = MainRecord(
                idx_all,
                record.string_id,
                record.instance,
                record.group,
                record.source_text,
                record.translated_text,
                record.flag,
                record.resource,
                record.resource_original,
                record.package_key,
                record.source_old,
                record.translated_old,
                record.index_alt,
                record.comment,
                [occurrence]
            )
            items.append(item)
            dedupe_index[occurrence_data.key] = item
            idx_all += 1

        self.workspace_cache.add_many(cache_entries)
        self.workspace_cache.commit()

        if items:
            self.model.append(items)
        elif result.loaded:
            self.model.layoutChanged.emit()

        if result.empty:
            if file_count == 1:
                window_signals.message.emit(interface.text('Messages', 'Not found text records in this file!'))
            elif file_count == len(result.empty):
                window_signals.message.emit(interface.text('Messages', 'Not found text records in this files!'))
            else:
                names = "\n".join(result.empty)
                window_signals.message.emit(
                    interface.text('Messages', 'Not found text records in following files:') + "\n\n{}".format(names))

        if result.loaded or result.skipped_duplicates:
            message = interface.text(
                'System',
                'Loaded {} unique strings, skipped {} duplicates'
            ).format(len(result.records), result.skipped_duplicates)
            window_signals.log.emit(message)

        self.signals.loaded.emit(list(result.loaded))

    def load_bundle(self, filename: str, asynchronous: bool = False) -> None:
        if not os.path.exists(filename):
            return

        with open(filename, 'r', encoding='utf-8') as fp:
            content = fp.read()

        try:
            parser = ElementTree.XMLParser(encoding='utf-8')
            tree = ElementTree.fromstring(content, parser=parser)
        except ElementTree.ParseError:
            return

        files = []

        if tree.findall('Content/File'):
            prefix = tree.find('Content').get('prefix')
            prefix = prefix if prefix else ''
            for s in tree.findall('Content/File'):
                files.append(os.path.abspath(os.path.join(prefix, s.get('path'))))

        if files:
            self.load(files, asynchronous=asynchronous)

    def save_bundle(self, filename: str) -> None:
        root = ElementTree.Element('XMLPackages')
        content = ElementTree.SubElement(root, 'Content')

        packages = [str(Path(p.path).resolve()) for p in self.packages]
        packages.sort()

        try:
            common_prefix = os.path.commonpath(packages)
            content.set('prefix', str(common_prefix))
        except ValueError:
            common_prefix = None

        for f in packages:
            relative_path = Path(f).relative_to(common_prefix) if common_prefix else f
            string = ElementTree.SubElement(content, 'File')
            string.set('path', str(relative_path))

        with open(filename, 'wb') as fp:
            fp.write(prettify(root))

    def get_stbl(self, convert: bool = True, items: List[MainRecord] = None) -> Dict[ResourceID, Stbl]:
        stbl = {}

        items = sorted(items if items is not None else self.model.items,
                       key=operator.itemgetter(RECORD_MAIN_INDEX),
                       reverse=False)

        experemental = config.value('save', 'experemental')

        for item in items:
            rid = item.resource

            if convert and experemental:
                if item.flag == FLAG_UNVALIDATED:
                    continue
                rid = ResourceID(group=rid.group,
                                 type=rid.type,
                                 instance=fnv64('translator:' + os.path.abspath('.') + rid.str_instance))

            rid = rid.convert_instance()
            if rid not in stbl:
                stbl[rid] = Stbl(rid)

            stbl[rid].add(item.id, item.translate)

        return stbl

    def save(self, path, package_key: str = None, asynchronous: bool = True):
        items = self.primary_items(package_key) if package_key else self.model.items
        request = SavePackageRequest(
            path=path,
            items=self.__save_items(items),
            convert=True,
            experimental=config.value('save', 'experemental'),
            destination_locale=config.value('translation', 'destination'),
            message=interface.text('System', 'Saving package {}...').format(os.path.basename(path))
        )

        if asynchronous:
            return self.__start_save(save_package_task, request)

        return save_package_task(CancellationToken(), _NullReporter(), request)

    def finalize(self, fpath, tpath, package_key: str = None, asynchronous: bool = True):
        package_key = package_key or (self.current_package.key if self.current_package else None)
        items = self.primary_items(package_key) if package_key else self.model.items
        request = FinalizePackageRequest(
            source_path=fpath,
            target_path=tpath,
            items=self.__save_items(items),
            backup=config.value('save', 'backup'),
            destination_locale=config.value('translation', 'destination'),
            message=interface.text('System', 'Saving package {}...').format(os.path.basename(tpath))
        )

        if asynchronous:
            return self.__start_save(finalize_package_task, request)

        return finalize_package_task(CancellationToken(), _NullReporter(), request)

    @staticmethod
    def __save_items(items: List[MainRecord]) -> tuple:
        rows = sorted(items, key=operator.itemgetter(RECORD_MAIN_INDEX), reverse=False)
        return tuple(SaveStringDTO(
            resource=item.resource,
            string_id=item.id,
            translated_text=item.translate,
            flag=item.flag
        ) for item in rows)

    def __start_save(self, task, request):
        if self.__save_handle:
            self.__save_handle.cancel()

        progress_signals.initiate.emit(request.message, 0)
        self.__save_handle = self.__runner.start(task, request, job_name=request.message)
        self.__save_handle.progress.connect(self.__task_progress)
        self.__save_handle.result.connect(lambda result, handle=self.__save_handle: self.__save_result(result, handle))
        self.__save_handle.error.connect(lambda error, handle=self.__save_handle: self.__save_error(error, handle))
        self.__save_handle.finished.connect(lambda cancelled, handle=self.__save_handle: self.__save_finished(cancelled, handle))
        return self.__save_handle

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

    def __save_result(self, result, handle) -> None:
        if self.__save_handle is not handle:
            return
        path = getattr(result, 'target_path', None) or getattr(result, 'path', '')
        message = interface.text(
            'System',
            'Saved package {}, {} resource(s)'
        ).format(os.path.basename(path), getattr(result, 'resource_count', 0))
        window_signals.log.emit(message)

    def __save_error(self, error, handle) -> None:
        if self.__save_handle is not handle:
            return
        message = getattr(error, 'message', str(error))
        window_signals.log.emit(message)
        window_signals.message.emit(message)

    def __load_finished(self, cancelled: bool, handle) -> None:
        if cancelled:
            progress_signals.finished.emit()
        if self.__load_handle is handle:
            self.__load_handle = None

    def __save_finished(self, _cancelled: bool, handle) -> None:
        if self.__save_handle is not handle:
            return
        progress_signals.finished.emit()
        self.__save_handle = None

    def close(self) -> None:
        if self.__load_handle:
            self.__load_handle.cancel()

        if not self.packages:
            return

        package_key = app_state.current_package

        if package_key and len(self.packages) > 1:
            undo.clean(package_key)

            items = []

            idx = 1
            for item in self.model.items:
                if item.has_package(package_key):
                    if item.remove_package(package_key):
                        item.idx = idx
                        items.append(item)
                        idx += 1
                    else:
                        item.clear()
                else:
                    item.idx = idx
                    items.append(item)
                    idx += 1

            self.model.replace(items)
            self.workspace_cache.remove_package(package_key)

            self.packages = [p for p in self.packages if p.key != package_key]

            self.signals.closed.emit(package_key)

        else:
            undo.clean()
            self.model.clear()
            self.packages.clear()
            self.workspace_cache.clear()
            self.signals.cleared.emit()

        gc.collect()

    def __len__(self) -> int:
        return sum(len(p) for p in self.packages)

    @staticmethod
    def check_package(path):
        if not os.path.exists(path):
            return False

        with DbpfPackage.read(path) as dbfile:
            stbl = dbfile.search_stbl()
            return len(stbl) > 0

    @staticmethod
    def check_stbl(path):
        if not os.path.exists(path):
            return False

        with open(path, 'rb') as f:
            if f.read(4) == b'STBL':
                return True

        return False

    @staticmethod
    def check_xml(path):
        if not os.path.exists(path):
            return False

        with open(path, 'r', encoding='utf-8') as fp:
            content = fp.read()
            try:
                parser = ElementTree.XMLParser(encoding='utf-8')
                tree = ElementTree.fromstring(content, parser=parser)
                if tree.findall('TextStringDefinitions/TextStringDefinition') or tree.findall('Content/Table/String'):
                    return True
            except ElementTree.ParseError:
                return False

        return False

    @staticmethod
    def check_json(path):
        if not os.path.exists(path):
            return False

        with open(path, 'r', encoding='utf-8') as fp:
            try:
                content = json.load(fp)
            except JSONDecodeError:
                return False

            entries = content.get('Entries', None)

            if entries:
                return True

        return False

    @staticmethod
    def check_binary(path):
        if not os.path.exists(path):
            return False

        try:
            with open(path, 'rb') as fp:
                header = fp.read(4)
                if header == b'STBL':
                    return True
        except (IOError, OSError):
            return False

        return False

    @staticmethod
    def read_package(path):
        if not os.path.exists(path):
            return {}

        table = {}

        language_dest = config.value('translation', 'destination')

        with DbpfPackage.read(path) as dbfile:
            for rid in dbfile.search_stbl():
                if rid.language == language_dest:
                    stbl = Stbl(rid=rid, value=dbfile[rid].content)
                    for sid, value in stbl.strings.items():
                        if value:
                            table[sid] = value

        return table

    @staticmethod
    def read_stbl(path):
        if not os.path.exists(path):
            return {}

        table = {}

        with open(path, 'rb') as fp:
            filename = os.path.basename(path)
            filename = os.path.splitext(filename)[0]
            stbl = Stbl(ResourceID.from_string(filename), value=fp.read())
            for sid, value in stbl.strings.items():
                if value:
                    table[sid] = value

        return table

    @staticmethod
    def read_xml(path):
        if not os.path.exists(path):
            return {}

        with open(path, 'r', encoding='utf-8') as fp:
            content = fp.read()

        try:
            parser = ElementTree.XMLParser(encoding='utf-8')
            tree = ElementTree.fromstring(content, parser=parser)
        except ElementTree.ParseError:
            return {}

        table = {}

        if tree.findall('TextStringDefinitions/TextStringDefinition'):
            for s in tree.findall('TextStringDefinitions/TextStringDefinition'):
                sid = int(s.get('InstanceID'), 16)
                source = text_to_stbl(s.get('TextString'))
                table[sid] = source
        else:
            for s in tree.findall('Content/Table/String'):
                sid = int(s.get('id'), 16)
                table[sid] = text_to_stbl(s.find('Dest').text)

        return table

    @staticmethod
    def read_json(path):
        if not os.path.exists(path):
            return {}

        try:
            with open(path, 'r', encoding='utf-8') as fp:
                content = json.load(fp)
        except JSONDecodeError:
            return {}

        entries = content.get('Entries', None)

        if not entries:
            return {}

        table = {}

        for entry in entries:
            sid = int(entry['Key'], 16)
            source = text_to_stbl(entry['Value'])
            table[sid] = source

        return table

    @staticmethod
    def read_binary(path):
        if not os.path.exists(path):
            return {}

        try:
            with open(path, 'rb') as fp:
                rid = ResourceID(group=0x80000000, instance=0x00000000, type=0x220557DA)
                stbl = Stbl(rid, fp.read())
                return stbl.strings
        except (IOError, OSError, Exception):
            return {}


packages_storage = PackagesStorage()
