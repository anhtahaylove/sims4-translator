# -*- coding: utf-8 -*-

import json
import os
import tempfile
import unittest

from packer.dbpf import DbpfPackage
from scripts.synthetic_package import build_stbl, create_synthetic_package
from scripts.verify_synthetic_smoke import SmokeVerificationError, verify_directory


def write_smoke_exports(tmpdir, info):
    with open(os.path.join(tmpdir, 'synthetic_smoke.json'), 'w', encoding='utf-8') as fp:
        json.dump({
            'Locale': 'RUS_RU',
            'Entries': [
                {'Key': '0x0000002A', 'Value': 'Hello'},
                {'Key': '0x00000007', 'Value': 'World'},
            ],
        }, fp)

    with open(os.path.join(tmpdir, 'synthetic_smoke.xml'), 'w', encoding='utf-8') as fp:
        fp.write(
            '<StblData><TextStringDefinitions>'
            '<TextStringDefinition InstanceID="0x0000002A" TextString="Hello"/>'
            '<TextStringDefinition InstanceID="0x00000007" TextString="World"/>'
            '</TextStringDefinitions></StblData>'
        )

    with open(os.path.join(tmpdir, 'translation_hub.csv'), 'w', encoding='utf-8-sig', newline='') as fp:
        fp.write('Key,Translated Text\r\n0x0000002A,Hello\r\n0x00000007,World\r\n')

    export_rid = info.source.convert_instance('RUS_RU')
    with DbpfPackage.write(os.path.join(tmpdir, '1_synthetic_smoke_RUS_RU.package')) as package:
        package.put(export_rid, build_stbl(export_rid, {42: 'Hello', 7: 'World'}).binary)


class SyntheticSmokeVerifierTests(unittest.TestCase):

    def test_verifies_generated_package_and_gui_exports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            info = create_synthetic_package(os.path.join(tmpdir, 'synthetic_smoke.package'))
            write_smoke_exports(tmpdir, info)

            summary = verify_directory(tmpdir, require_gui_outputs=True)

        self.assertFalse(summary.warnings)
        self.assertTrue(any('loaded as FRE_FR' in check for check in summary.checks))
        self.assertTrue(any('JSON export has 2 unique entries' in check for check in summary.checks))
        self.assertTrue(any('CSV export has 2 unique rows' in check for check in summary.checks))

    def test_package_only_passes_with_warning_but_strict_mode_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_synthetic_package(os.path.join(tmpdir, 'synthetic_smoke.package'))

            summary = verify_directory(tmpdir)
            with self.assertRaises(SmokeVerificationError):
                verify_directory(tmpdir, require_gui_outputs=True)

        self.assertTrue(summary.warnings)

    def test_duplicate_export_rows_fail_verification(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_synthetic_package(os.path.join(tmpdir, 'synthetic_smoke.package'))
            with open(os.path.join(tmpdir, 'synthetic_smoke.json'), 'w', encoding='utf-8') as fp:
                json.dump({
                    'Entries': [
                        {'Key': '0x0000002A', 'Value': 'Hello'},
                        {'Key': '0x0000002A', 'Value': 'Hello'},
                    ],
                }, fp)

            with self.assertRaises(SmokeVerificationError):
                verify_directory(tmpdir)


if __name__ == '__main__':
    unittest.main()
