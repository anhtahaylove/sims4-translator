# -*- coding: utf-8 -*-

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from singletons.config import ConfigManager


class ConfigStorageTests(unittest.TestCase):

    def test_fresh_config_is_saved_to_user_config_directory(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            user_config_dir = root / 'userdata'
            try:
                os.chdir(root)
                with patch.dict(os.environ, {'SIMS4_TRANSLATOR_CONFIG_DIR': str(user_config_dir)}):
                    manager = ConfigManager()
            finally:
                os.chdir(cwd)

            self.assertEqual(Path(manager.config_file), user_config_dir / 'config.xml')
            self.assertTrue((user_config_dir / 'config.xml').exists())
            self.assertEqual(manager.value('translation', 'source'), 'ENG_US')
            self.assertEqual(manager.value('translation', 'destination'), 'VI_VN')

    def test_legacy_prefs_config_migrates_to_user_config_without_overwriting_legacy(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prefs = root / 'prefs'
            prefs.mkdir()
            legacy = prefs / 'config.xml'
            legacy.write_text(
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<config>\n'
                '  <translation><source>ENG_US</source><destination>RUS_RU</destination></translation>\n'
                '  <api><deepl_key>sample:fx</deepl_key></api>\n'
                '</config>\n',
                encoding='utf-8'
            )

            user_config_dir = root / 'userdata'
            try:
                os.chdir(root)
                with patch.dict(os.environ, {'SIMS4_TRANSLATOR_CONFIG_DIR': str(user_config_dir)}):
                    manager = ConfigManager()
                    manager.save()
            finally:
                os.chdir(cwd)

            self.assertEqual(manager.value('translation', 'destination'), 'RUS_RU')
            self.assertEqual(manager.value('api', 'deepl_key'), 'sample:fx')
            self.assertTrue((user_config_dir / 'config.xml').exists())
            self.assertIn('<destination>RUS_RU</destination>', legacy.read_text(encoding='utf-8'))

    def test_save_does_not_create_repo_prefs_config_when_user_config_is_available(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            user_config_dir = root / 'userdata'
            try:
                os.chdir(root)
                with patch.dict(os.environ, {'SIMS4_TRANSLATOR_CONFIG_DIR': str(user_config_dir)}):
                    manager = ConfigManager()
                    manager.set_value('api', 'deepl_key', 'sample:fx')
                    manager.save()
            finally:
                os.chdir(cwd)

            self.assertFalse((root / 'prefs' / 'config.xml').exists())
            self.assertIn('sample:fx', (user_config_dir / 'config.xml').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
