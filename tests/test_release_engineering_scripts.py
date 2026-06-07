# -*- coding: utf-8 -*-

import unittest

from scripts.verify_interface_i18n import verify as verify_interface_i18n
from scripts.verify_interface_i18n import verify_all as verify_all_interface_i18n
from scripts.verify_version_sync import verify as verify_version_sync


class ReleaseEngineeringScriptTests(unittest.TestCase):

    def test_version_sync_accepts_current_release_version(self):
        self.assertEqual(verify_version_sync('2.3.3'), [])

    def test_vietnamese_interface_health_checker_accepts_current_catalog(self):
        self.assertEqual(verify_interface_i18n('vi_VN', '2.3.3'), [])

    def test_vietnamese_interface_catalog_has_full_release_coverage(self):
        self.assertEqual(
            verify_interface_i18n('vi_VN', '2.3.3', strict_empty=True, strict_missing=True),
            [],
        )

    def test_all_interface_catalogs_have_full_release_coverage(self):
        self.assertEqual(
            verify_all_interface_i18n('2.3.3', strict_empty=True, strict_missing=True),
            [],
        )


if __name__ == '__main__':
    unittest.main()
