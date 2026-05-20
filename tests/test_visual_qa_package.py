# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from scripts.create_visual_qa_package import DEFAULT_OUTPUT, create_visual_qa_package
from scripts.synthetic_package import read_stbl_by_locale


class VisualQaPackageTests(unittest.TestCase):

    def test_default_visual_qa_output_is_ignored_build_artifact(self):
        path = Path(DEFAULT_OUTPUT)
        self.assertEqual(path.parts[-3:-1], ('build', 'visual-qa'))
        self.assertEqual(path.name, 'large_visual_qa.package')

    def test_visual_qa_package_generates_token_heavy_source_and_destination(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            package_path = Path(tmpdir) / 'visual_qa.package'
            info = create_visual_qa_package(str(package_path), total_records=12, resource_count=3)

            self.assertEqual(info['records'], 12)
            self.assertEqual(info['resources'], 3)
            self.assertEqual(info['destination_locale'], 'VI_VN')

            source_tables = read_stbl_by_locale(str(package_path), 'ENG_US')
            dest_tables = read_stbl_by_locale(str(package_path), 'VI_VN')
            self.assertEqual(sum(len(strings) for strings in source_tables.values()), 12)
            self.assertEqual(sum(len(strings) for strings in dest_tables.values()), 12)

            source_text = '\n'.join(value for strings in source_tables.values() for value in strings.values())
            dest_text = '\n'.join(value for strings in dest_tables.values() for value in strings.values())
            self.assertIn('{0.SimFirstName}', source_text)
            self.assertIn('<b>', source_text)
            self.assertIn('\\n', source_text)
            self.assertIn('tiếng Việt', dest_text)


if __name__ == '__main__':
    unittest.main()
