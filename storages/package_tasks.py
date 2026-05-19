# -*- coding: utf-8 -*-

import csv
import json
import os
import pathlib
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from typing import Tuple

from packer.dbpf import DbpfPackage
from packer.resource import ResourceID
from packer.stbl import Stbl
from storages.container import Container
from utils.constants import (
    EXPORT_BINARY_S4S,
    EXPORT_JSON_S4S,
    EXPORT_STBL,
    EXPORT_XML,
    EXPORT_XML_DP,
    FLAG_PROGRESS,
    FLAG_TRANSLATED,
    FLAG_UNVALIDATED,
)
from utils.functions import compare, create_temporary_copy, fnv64, prettify, text_to_edit, text_to_stbl
from utils.task_runner import CancellationToken, TaskReporter


@dataclass(frozen=True)
class DictionarySnapshot:
    sid_entries: tuple = ()
    source_entries: tuple = ()


@dataclass(frozen=True)
class PackageLoadRequest:
    files: Tuple[str, ...]
    existing_package_keys: Tuple[str, ...]
    existing_record_keys: Tuple[tuple, ...]
    dictionaries: DictionarySnapshot
    strong_dictionary: bool
    group_original: bool
    group_highbit: bool
    file_message_template: str


@dataclass(frozen=True)
class LoadedPackageDTO:
    path: str
    instances: Tuple[str, ...]
    row_count: int


@dataclass(frozen=True)
class LoadedRecordDTO:
    key: tuple
    string_id: int
    instance: int
    group: int
    source_text: str
    translated_text: str
    flag: int
    resource: ResourceID
    resource_original: ResourceID
    package_key: str
    source_old: str
    translated_old: str
    index_alt: tuple
    comment: str


@dataclass(frozen=True)
class LoadedOccurrenceDTO:
    key: tuple
    resource_original: ResourceID
    package_key: str
    index_alt: tuple
    comment: str


@dataclass(frozen=True)
class PackageLoadResult:
    packages: Tuple[LoadedPackageDTO, ...]
    records: Tuple[LoadedRecordDTO, ...]
    occurrences: Tuple[LoadedOccurrenceDTO, ...]
    loaded: Tuple[str, ...]
    empty: Tuple[str, ...]
    skipped_duplicates: int = 0


@dataclass(frozen=True)
class SaveStringDTO:
    resource: ResourceID
    string_id: int
    translated_text: str
    flag: int


@dataclass(frozen=True)
class SavePackageRequest:
    path: str
    items: Tuple[SaveStringDTO, ...]
    convert: bool
    experimental: bool
    destination_locale: str
    message: str


@dataclass(frozen=True)
class SavePackageResult:
    path: str
    resource_count: int


@dataclass(frozen=True)
class FinalizePackageRequest:
    source_path: str
    target_path: str
    items: Tuple[SaveStringDTO, ...]
    backup: bool
    destination_locale: str
    message: str


@dataclass(frozen=True)
class FinalizePackageResult:
    source_path: str
    target_path: str
    resource_count: int


@dataclass(frozen=True)
class TranslationHubCsvRow:
    string_id: int
    source_text: str
    translated_text: str
    flag: int


@dataclass(frozen=True)
class TranslationHubCsvRequest:
    path: str
    rows: Tuple[TranslationHubCsvRow, ...]
    include_untranslated: bool
    message: str


@dataclass(frozen=True)
class TranslationHubCsvResult:
    path: str
    row_count: int


@dataclass(frozen=True)
class ExportRecordDTO:
    resource: ResourceID
    string_id: int
    source_text: str
    translated_text: str
    flag: int
    package_key: str
    comment: str = ''


@dataclass(frozen=True)
class StructuredExportRequest:
    export_type: int
    filename: str = ''
    directory: str = ''
    records: Tuple[ExportRecordDTO, ...] = ()
    include_untranslated: bool = False
    separate_packages: bool = False
    package_names: Tuple[Tuple[str, str], ...] = ()
    destination_locale: str = ''
    message: str = ''


@dataclass(frozen=True)
class StructuredExportResult:
    export_type: int
    files: Tuple[str, ...]
    string_count: int


def load_packages_task(
        token: CancellationToken,
        reporter: TaskReporter,
        request: PackageLoadRequest
) -> PackageLoadResult:
    existing_packages = set(request.existing_package_keys)
    dedupe_keys = set(request.existing_record_keys)
    sid_map = {sid: entries for sid, entries in request.dictionaries.sid_entries}
    source_map = {source: translations for source, translations in request.dictionaries.source_entries}

    packages = []
    records = []
    occurrences = []
    loaded = []
    empty = []
    skipped_duplicates = 0

    for file in request.files:
        token.raise_if_cancelled()

        package = Container(file)
        if package.key in existing_packages:
            continue

        reporter.progress(0, 0, request.file_message_template.format(package.fullname))
        strings = package.open()
        token.raise_if_cancelled()

        if not strings:
            empty.append(package.name)
            continue

        reporter.progress(0, max(1, int(len(strings) / 100)), request.file_message_template.format(package.fullname))

        packages.append(LoadedPackageDTO(
            path=package.path,
            instances=tuple(package.instances),
            row_count=len(strings)
        ))
        loaded.append(package.key)

        for i, string in enumerate(strings):
            token.raise_if_cancelled()
            if i % 100 == 0:
                reporter.progress(1, 0, '')

            rid = string[0]
            sid = string[1]
            source = text_to_stbl(string[2])
            dest = text_to_stbl(string[3])
            comment = string[4]
            line_source = string[5]
            line_instance = string[6]
            flag = FLAG_UNVALIDATED
            old = None

            if not package.is_package:
                flag = FLAG_TRANSLATED
            else:
                translated = _find_sid_translation(
                    sid_map.get(sid, ()),
                    package.name,
                    source,
                    request.strong_dictionary
                )
                if translated:
                    dest = translated[0][2]
                    comment = translated[0][3]
                    flag = FLAG_PROGRESS if len(translated) > 1 else FLAG_TRANSLATED
                    if not compare(translated[0][1], source):
                        old = translated[0][1]
                elif not request.strong_dictionary:
                    source_translations = source_map.get(source, ())
                    if source_translations:
                        dest = source_translations[0]
                        flag = FLAG_PROGRESS if len(source_translations) > 1 else FLAG_TRANSLATED

            display_rid = rid if request.group_original else rid.convert_group(highbit=request.group_highbit)
            index_alt = (i + 1, line_source, i + 4, line_instance + 3)
            key = (sid, source, dest)

            if key in dedupe_keys:
                skipped_duplicates += 1
                continue

            occurrences.append(LoadedOccurrenceDTO(
                key=key,
                resource_original=rid,
                package_key=package.key,
                index_alt=index_alt,
                comment=comment
            ))

            records.append(LoadedRecordDTO(
                key=key,
                string_id=sid,
                instance=display_rid.instance,
                group=display_rid.group,
                source_text=source,
                translated_text=dest,
                flag=flag,
                resource=display_rid,
                resource_original=rid,
                package_key=package.key,
                source_old=old,
                translated_old=None,
                index_alt=index_alt,
                comment=comment
            ))
            dedupe_keys.add(key)

    return PackageLoadResult(
        packages=tuple(packages),
        records=tuple(records),
        occurrences=tuple(occurrences),
        loaded=tuple(loaded),
        empty=tuple(empty),
        skipped_duplicates=skipped_duplicates
    )


def save_package_task(
        token: CancellationToken,
        reporter: TaskReporter,
        request: SavePackageRequest
) -> SavePackageResult:
    stbl = _build_stbl(token, reporter, request.items, request.convert, request.experimental, request.destination_locale,
                       request.message)

    reporter.progress(0, max(1, len(stbl)), request.message)
    temp_path = request.path + '.tmp'
    outpkg = None
    committed = False

    try:
        outpkg = DbpfPackage(temp_path, mode='w')
        for rid, inst in stbl.items():
            token.raise_if_cancelled()
            outpkg.put(rid, inst.binary)
            reporter.progress(1, 0, '')

        outpkg.commit()
        os.replace(temp_path, request.path)
        committed = True
    finally:
        if outpkg is not None and not committed:
            outpkg.close()
        if not committed:
            pathlib.Path(temp_path).unlink(missing_ok=True)

    return SavePackageResult(path=request.path, resource_count=len(stbl))


def finalize_package_task(
        token: CancellationToken,
        reporter: TaskReporter,
        request: FinalizePackageRequest
) -> FinalizePackageResult:
    source_path = os.path.abspath(request.source_path)
    target_path = os.path.abspath(request.target_path)

    if not os.path.exists(source_path):
        return FinalizePackageResult(source_path=source_path, target_path=target_path, resource_count=0)

    stbl = _build_stbl(token, reporter, request.items, False, False, request.destination_locale, request.message)

    with open(source_path, 'rb') as f:
        magic = f.read(4)

    if magic != b'DBPF':
        return FinalizePackageResult(source_path=source_path, target_path=target_path, resource_count=0)

    is_temp = False
    if request.backup and source_path.lower() == target_path.lower():
        source_path = source_path + '.backup'
        os.rename(request.source_path, source_path)
    else:
        source_path = create_temporary_copy(source_path)
        is_temp = True

    resource_count = len(stbl)
    target_temp_path = target_path + '.tmp'
    dbfile = None
    outpkg = None
    committed = False

    try:
        dbfile = DbpfPackage(source_path, mode='r')
        outpkg = DbpfPackage(target_temp_path, mode='w')
        instances = tuple(dbfile.search())
        reporter.progress(0, max(1, len(instances)), request.message)

        for rid in instances:
            token.raise_if_cancelled()
            if rid.language == request.destination_locale:
                replacement = _pop_matching_stbl(stbl, rid)
                if replacement:
                    outpkg.put(replacement[0], replacement[1].binary)
                else:
                    content = dbfile[rid].content
                    if content:
                        outpkg.put(rid, content)
            else:
                content = dbfile[rid].content
                if content:
                    outpkg.put(rid, content)

            reporter.progress(1, 0, '')

        for rid, stbl_resource in stbl.items():
            token.raise_if_cancelled()
            outpkg.put(rid, stbl_resource.binary)

        outpkg.commit()
        os.replace(target_temp_path, target_path)
        committed = True
    finally:
        if dbfile is not None:
            dbfile.close()
        if outpkg is not None and not committed:
            outpkg.close()
        if is_temp:
            pathlib.Path(source_path).unlink(missing_ok=True)
        if not committed:
            pathlib.Path(target_temp_path).unlink(missing_ok=True)

    return FinalizePackageResult(source_path=request.source_path, target_path=target_path, resource_count=resource_count)


def export_translation_hub_csv_task(
        token: CancellationToken,
        reporter: TaskReporter,
        request: TranslationHubCsvRequest
) -> TranslationHubCsvResult:
    reporter.progress(0, max(1, len(request.rows)), request.message)

    row_count = 0
    seen_keys = set()
    temp_path = request.path + '.tmp'
    committed = False

    try:
        with open(temp_path, 'w', encoding='utf-8-sig', newline='') as fp:
            writer = csv.writer(fp)
            writer.writerow(('Key', 'Translated Text'))

            for row in request.rows:
                token.raise_if_cancelled()
                reporter.progress(1, 0, '')

                if not request.include_untranslated and row.flag == FLAG_UNVALIDATED:
                    continue

                dedupe_key = (row.string_id, row.source_text, row.translated_text)
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)

                writer.writerow((f'0x{row.string_id:08X}', row.translated_text))
                row_count += 1

        token.raise_if_cancelled()
        os.replace(temp_path, request.path)
        committed = True
    finally:
        if not committed:
            pathlib.Path(temp_path).unlink(missing_ok=True)

    return TranslationHubCsvResult(path=request.path, row_count=row_count)


def export_structured_task(
        token: CancellationToken,
        reporter: TaskReporter,
        request: StructuredExportRequest
) -> StructuredExportResult:
    records = _export_records(token, reporter, request)

    if request.export_type == EXPORT_XML:
        files = _export_xml(token, request, records)
    elif request.export_type == EXPORT_XML_DP:
        files = _export_xml_dp(token, request, records)
    elif request.export_type == EXPORT_JSON_S4S:
        files = _export_json_s4s(token, request, records)
    elif request.export_type == EXPORT_BINARY_S4S:
        files = _export_binary_s4s(token, request, records)
    else:
        files = _export_stbl(token, request, records, '.stbl')

    return StructuredExportResult(
        export_type=request.export_type,
        files=tuple(files),
        string_count=len(records)
    )


def _find_sid_translation(entries: tuple, package_name: str, source: str, strong_dictionary: bool) -> tuple:
    if not entries:
        return ()

    translated = tuple(t for t in entries if t[0].lower() == package_name.lower())
    if not translated and not strong_dictionary:
        translated = entries
    if translated and not compare(translated[0][1], source):
        return translated
    return translated


def _build_stbl(
        token: CancellationToken,
        reporter: TaskReporter,
        items: Tuple[SaveStringDTO, ...],
        convert: bool,
        experimental: bool,
        destination_locale: str,
        message: str
) -> dict:
    stbl = {}
    reporter.progress(0, max(1, int(len(items) / 100)), message)

    for index, item in enumerate(items):
        token.raise_if_cancelled()
        if index % 100 == 0:
            reporter.progress(1, 0, '')

        rid = item.resource
        if convert and experimental:
            if item.flag == FLAG_UNVALIDATED:
                continue
            rid = ResourceID(
                group=rid.group,
                type=rid.type,
                instance=fnv64('translator:' + os.path.abspath('.') + rid.str_instance)
            )

        rid = rid.convert_instance(destination_locale)
        if rid not in stbl:
            stbl[rid] = Stbl(rid)

        stbl[rid].add(item.string_id, item.translated_text)

    return stbl


def _export_records(
        token: CancellationToken,
        reporter: TaskReporter,
        request: StructuredExportRequest
) -> tuple:
    reporter.progress(0, max(1, len(request.records)), request.message)
    records = []
    seen_keys = set()

    for record in request.records:
        token.raise_if_cancelled()
        reporter.progress(1, 0, '')

        if not request.include_untranslated and record.flag == FLAG_UNVALIDATED:
            continue

        dedupe_key = (record.string_id, record.source_text, record.translated_text)
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        records.append(record)

    token.raise_if_cancelled()
    return tuple(records)


def _converted_resource(record: ExportRecordDTO, request: StructuredExportRequest) -> ResourceID:
    return record.resource.convert_instance(request.destination_locale or None)


def _build_export_stbl(records: tuple, request: StructuredExportRequest) -> dict:
    stbl = {}
    for record in records:
        rid = _converted_resource(record, request)
        if rid not in stbl:
            stbl[rid] = Stbl(rid)
        stbl[rid].add(record.string_id, record.translated_text)
    return stbl


def _write_bytes_atomic(token: CancellationToken, path: str, content: bytes) -> str:
    temp_path = path + '.tmp'
    committed = False
    try:
        with open(temp_path, 'wb') as fp:
            token.raise_if_cancelled()
            fp.write(content)
            fp.flush()
            token.raise_if_cancelled()
        os.replace(temp_path, path)
        committed = True
        return path
    finally:
        if not committed:
            pathlib.Path(temp_path).unlink(missing_ok=True)


def _write_text_atomic(token: CancellationToken, path: str, content: str) -> str:
    return _write_bytes_atomic(token, path, content.encode('utf-8'))


def _package_name(request: StructuredExportRequest, package_key: str) -> str:
    package_names = dict(request.package_names)
    name = package_names.get(package_key)
    if name:
        return name
    base = os.path.basename(package_key)
    return os.path.splitext(base)[0] or 'package'


def _group_records_by_resource(records: tuple, request: StructuredExportRequest) -> dict:
    grouped = {}
    for record in records:
        rid = _converted_resource(record, request)
        grouped.setdefault(rid, []).append(record)
    return grouped


def _group_records_by_package(records: tuple) -> dict:
    grouped = {}
    for record in records:
        grouped.setdefault(record.package_key, []).append(record)
    return grouped


def _first_locale(request: StructuredExportRequest, records: tuple) -> str:
    source = records[0] if records else (request.records[0] if request.records else None)
    if not source:
        return None
    return _converted_resource(source, request).language


def _export_stbl(
        token: CancellationToken,
        request: StructuredExportRequest,
        records: tuple,
        extension: str
) -> list:
    files = []
    stbl = _build_export_stbl(records, request)

    if request.filename:
        for _rid, table in stbl.items():
            files.append(_write_bytes_atomic(token, request.filename, table.binary))
            break
    elif request.directory:
        for rid, table in stbl.items():
            token.raise_if_cancelled()
            filename = os.path.join(request.directory, rid.filename + extension)
            files.append(_write_bytes_atomic(token, filename, table.binary))

    return files


def _export_binary_s4s(token: CancellationToken, request: StructuredExportRequest, records: tuple) -> list:
    if not (request.directory and request.separate_packages):
        return _export_stbl(token, request, records, '.binary')

    files = []
    for package_key, package_records in _group_records_by_package(records).items():
        token.raise_if_cancelled()
        tables = _build_export_stbl(tuple(package_records), request)
        merged_stbl = None
        for _rid, table in tables.items():
            if merged_stbl is None:
                merged_stbl = table
            else:
                for str_id, str_value in table._strings.items():
                    merged_stbl.add(str_id, str_value)
        if merged_stbl:
            filename = os.path.join(request.directory, _package_name(request, package_key) + '.binary')
            files.append(_write_bytes_atomic(token, filename, merged_stbl.binary))
    return files


def _xml_table(parent, rid: ResourceID):
    table = ElementTree.SubElement(parent, 'Table')
    table.set('instance', rid.str_instance)
    table.set('group', rid.str_group)
    return table


def _xml_root_for(records: tuple, request: StructuredExportRequest):
    root = ElementTree.Element('STBLXMLResources')
    content = ElementTree.SubElement(root, 'Content')
    tables = {}
    for record in records:
        rid = _converted_resource(record, request)
        if rid not in tables:
            tables[rid] = _xml_table(content, rid)
        string = ElementTree.SubElement(tables[rid], 'String')
        string.set('id', '{id:08x}'.format(id=record.string_id))
        source = ElementTree.SubElement(string, 'Source')
        source.text = text_to_edit(record.source_text)
        dest = ElementTree.SubElement(string, 'Dest')
        dest.text = text_to_edit(record.translated_text)
        if record.comment:
            comment = ElementTree.SubElement(string, 'Comment')
            comment.text = record.comment
    return root


def _export_xml(token: CancellationToken, request: StructuredExportRequest, records: tuple) -> list:
    files = []
    if request.filename:
        root = _xml_root_for(records, request)
        files.append(_write_bytes_atomic(token, request.filename, prettify(root)))
    elif request.directory:
        if request.separate_packages:
            groups = _group_records_by_package(records)
            for package_key, package_records in groups.items():
                token.raise_if_cancelled()
                filename = os.path.join(request.directory, _package_name(request, package_key) + '.xml')
                root = _xml_root_for(tuple(package_records), request)
                files.append(_write_bytes_atomic(token, filename, prettify(root)))
        else:
            groups = _group_records_by_resource(records, request)
            for rid, resource_records in groups.items():
                token.raise_if_cancelled()
                filename = os.path.join(request.directory, rid.filename + '.xml')
                root = _xml_root_for(tuple(resource_records), request)
                files.append(_write_bytes_atomic(token, filename, prettify(root)))
    return files


def _xml_dp_root_for(records: tuple, request: StructuredExportRequest):
    root = ElementTree.Element('StblData')
    content = ElementTree.SubElement(root, 'TextStringDefinitions')
    for record in records:
        string = ElementTree.SubElement(content, 'TextStringDefinition')
        string.set('InstanceID', '0x{id:08X}'.format(id=record.string_id))
        string.set('TextString', text_to_stbl(record.translated_text))
    return root


def _export_xml_dp(token: CancellationToken, request: StructuredExportRequest, records: tuple) -> list:
    files = []
    if request.filename:
        root = _xml_dp_root_for(records, request)
        files.append(_write_bytes_atomic(token, request.filename, prettify(root)))
    elif request.directory:
        if request.separate_packages:
            groups = _group_records_by_package(records)
            for package_key, package_records in groups.items():
                token.raise_if_cancelled()
                filename = os.path.join(request.directory, _package_name(request, package_key) + '.xml')
                root = _xml_dp_root_for(tuple(package_records), request)
                files.append(_write_bytes_atomic(token, filename, prettify(root)))
        else:
            groups = _group_records_by_resource(records, request)
            for rid, resource_records in groups.items():
                token.raise_if_cancelled()
                filename = os.path.join(request.directory, rid.filename + '.xml')
                root = _xml_dp_root_for(tuple(resource_records), request)
                files.append(_write_bytes_atomic(token, filename, prettify(root)))
    return files


def _json_entries(records: tuple) -> list:
    return [{
        'Key': '0x{id:08X}'.format(id=record.string_id),
        'Value': text_to_stbl(record.translated_text)
    } for record in records]


def _json_content(records: tuple, request: StructuredExportRequest) -> str:
    return json.dumps({
        'Locale': _first_locale(request, records),
        'Entries': _json_entries(records),
    }, indent=2, ensure_ascii=False)


def _export_json_s4s(token: CancellationToken, request: StructuredExportRequest, records: tuple) -> list:
    files = []
    if request.filename:
        files.append(_write_text_atomic(token, request.filename, _json_content(records, request)))
    elif request.directory:
        if request.separate_packages:
            groups = _group_records_by_package(records)
            for package_key, package_records in groups.items():
                token.raise_if_cancelled()
                filename = os.path.join(request.directory, _package_name(request, package_key) + '.json')
                files.append(_write_text_atomic(token, filename, _json_content(tuple(package_records), request)))
        else:
            groups = _group_records_by_resource(records, request)
            for rid, resource_records in groups.items():
                token.raise_if_cancelled()
                filename = os.path.join(request.directory, rid.filename + '.json')
                files.append(_write_text_atomic(token, filename, _json_content(tuple(resource_records), request)))
    return files


def _pop_matching_stbl(stbl: dict, rid: ResourceID):
    for resource_id, stbl_resource in tuple(stbl.items()):
        if resource_id.group == rid.group and resource_id.instance == rid.instance:
            del stbl[resource_id]
            return resource_id, stbl_resource
    return None
