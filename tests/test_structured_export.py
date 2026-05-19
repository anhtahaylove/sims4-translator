# -*- coding: utf-8 -*-

import json
import os
import tempfile
import unittest
import xml.etree.ElementTree as ElementTree

from packer.resource import ResourceID
from packer.stbl import Stbl
from storages.package_tasks import (
    ExportRecordDTO,
    StructuredExportRequest,
    export_structured_task,
)
from utils.constants import (
    EXPORT_BINARY_S4S,
    EXPORT_JSON_S4S,
    EXPORT_STBL,
    EXPORT_XML,
    EXPORT_XML_DP,
    FLAG_TRANSLATED,
    FLAG_UNVALIDATED,
)
from utils.task_runner import CancellationToken, CancelledTask, TaskReporter


class NoopReporter(TaskReporter):

    def __init__(self):
        pass

    def progress(self, current: int = 0, total: int = 0, message: str = '') -> None:
        pass


class CancellingReporter(TaskReporter):

    def __init__(self, token):
        self.token = token

    def progress(self, current: int = 0, total: int = 0, message: str = '') -> None:
        if current:
            self.token.cancel()


def record(string_id, source, translated, package='pkg.package', flag=FLAG_TRANSLATED):
    return ExportRecordDTO(
        resource=ResourceID(group=0, instance=1, type=0x220557DA),
        string_id=string_id,
        source_text=source,
        translated_text=translated,
        flag=flag,
        package_key=package,
        comment='note' if string_id == 42 else '',
    )


def request(export_type, path=None, directory=None, records=(), include_untranslated=False, separate_packages=False):
    return StructuredExportRequest(
        export_type=export_type,
        filename=path,
        directory=directory,
        records=tuple(records),
        include_untranslated=include_untranslated,
        separate_packages=separate_packages,
        package_names=(('pkg.package', 'pkg'), ('other.package', 'other')),
        destination_locale='ENG_US',
        message='Exporting translate...',
    )


class StructuredExportTests(unittest.TestCase):

    def test_exports_stbl_atomically_and_skips_untranslated(self):
        rows = (
            record(42, 'Hello', 'Bonjour'),
            record(42, 'Hello', 'Bonjour'),
            record(7, 'Skip', 'Skip', flag=FLAG_UNVALIDATED),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'out.stbl')
            result = export_structured_task(CancellationToken(), NoopReporter(), request(EXPORT_STBL, path, records=rows))
            with open(path, 'rb') as fp:
                parsed = Stbl(ResourceID(group=0, instance=1, type=0x220557DA), fp.read()).strings

        self.assertEqual(result.string_count, 1)
        self.assertEqual(len(result.files), 1)
        self.assertEqual(parsed, {42: 'Bonjour'})

    def test_exports_xml_and_xml_dp_with_existing_shapes(self):
        rows = (
            record(42, 'Hello', 'Bonjour'),
            record(7, 'Skip', 'Skip', flag=FLAG_UNVALIDATED),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            xml_path = os.path.join(tmpdir, 'out.xml')
            dp_path = os.path.join(tmpdir, 'out_dp.xml')
            export_structured_task(CancellationToken(), NoopReporter(), request(EXPORT_XML, xml_path, records=rows))
            export_structured_task(CancellationToken(), NoopReporter(), request(EXPORT_XML_DP, dp_path, records=rows))

            xml_root = ElementTree.parse(xml_path).getroot()
            dp_root = ElementTree.parse(dp_path).getroot()

        self.assertEqual(xml_root.tag, 'STBLXMLResources')
        self.assertEqual(len(xml_root.findall('.//String')), 1)
        self.assertEqual(xml_root.find('.//String').get('id'), '0000002a')
        self.assertEqual(dp_root.tag, 'StblData')
        self.assertEqual(len(dp_root.findall('.//TextStringDefinition')), 1)
        self.assertEqual(dp_root.find('.//TextStringDefinition').get('InstanceID'), '0x0000002A')

    def test_exports_json_and_binary_outputs(self):
        rows = (
            record(42, 'Hello', 'Bonjour'),
            record(7, 'World', 'Monde'),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, 'out.json')
            binary_path = os.path.join(tmpdir, 'out.binary')
            export_structured_task(CancellationToken(), NoopReporter(), request(EXPORT_JSON_S4S, json_path, records=rows))
            export_structured_task(CancellationToken(), NoopReporter(), request(EXPORT_BINARY_S4S, binary_path, records=rows))

            with open(json_path, 'r', encoding='utf-8') as fp:
                json_data = json.loads(fp.read())
            with open(binary_path, 'rb') as fp:
                binary_data = Stbl(ResourceID(group=0, instance=1, type=0x220557DA), fp.read()).strings

        self.assertEqual(json_data['Locale'], 'ENG_US')
        self.assertEqual(json_data['Entries'], [
            {'Key': '0x0000002A', 'Value': 'Bonjour'},
            {'Key': '0x00000007', 'Value': 'Monde'},
        ])
        self.assertEqual(binary_data, {42: 'Bonjour', 7: 'Monde'})

    def test_separate_package_directory_export_uses_package_names(self):
        rows = (
            record(42, 'Hello', 'Bonjour', package='pkg.package'),
            record(7, 'World', 'Monde', package='other.package'),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_structured_task(
                CancellationToken(),
                NoopReporter(),
                request(EXPORT_JSON_S4S, directory=tmpdir, records=rows, separate_packages=True),
            )
            names = sorted(os.path.basename(path) for path in result.files)

        self.assertEqual(names, ['other.json', 'pkg.json'])
        self.assertEqual(result.string_count, 2)

    def test_cancelled_export_removes_temp_file(self):
        rows = tuple(record(index, f'Source {index}', f'Dest {index}') for index in range(5))

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'out.json')
            token = CancellationToken()
            with self.assertRaises(CancelledTask):
                export_structured_task(token, CancellingReporter(token), request(EXPORT_JSON_S4S, path, records=rows))

            self.assertFalse(os.path.exists(path))
            self.assertFalse(os.path.exists(path + '.tmp'))

    def test_export_error_removes_temp_file(self):
        rows = (record(42, 'Hello', 'Bonjour'),)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'missing', 'out.json')
            with self.assertRaises(FileNotFoundError):
                export_structured_task(CancellationToken(), NoopReporter(), request(EXPORT_JSON_S4S, path, records=rows))

            self.assertFalse(os.path.exists(path))
            self.assertFalse(os.path.exists(path + '.tmp'))


if __name__ == '__main__':
    unittest.main()
