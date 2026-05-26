# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from singletons.config import ConfigManager


class ConfigStorageTests(unittest.TestCase):

    @staticmethod
    def __set_meipass(path):
        sentinel = object()
        previous = getattr(sys, '_MEIPASS', sentinel)
        setattr(sys, '_MEIPASS', str(path))
        return sentinel, previous

    @staticmethod
    def __restore_meipass(sentinel, previous):
        if previous is sentinel:
            delattr(sys, '_MEIPASS')
        else:
            setattr(sys, '_MEIPASS', previous)

    def test_fresh_config_is_saved_to_user_config_directory(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            app_root = root / 'app'
            app_root.mkdir()
            user_config_dir = root / 'userdata'
            sentinel, previous = self.__set_meipass(app_root)
            try:
                os.chdir(root)
                with patch.dict(os.environ, {'SIMS4_TRANSLATOR_CONFIG_DIR': str(user_config_dir)}):
                    manager = ConfigManager()
            finally:
                os.chdir(cwd)
                self.__restore_meipass(sentinel, previous)

            self.assertEqual(Path(manager.config_file), user_config_dir / 'config.xml')
            self.assertTrue((user_config_dir / 'config.xml').exists())
            self.assertEqual(manager.value('translation', 'source'), 'ENG_US')
            self.assertEqual(manager.value('translation', 'destination'), 'VI_VN')

    def test_legacy_prefs_config_migrates_to_user_config_without_overwriting_legacy(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            app_root = root / 'app'
            other_cwd = root / 'cwd'
            prefs = app_root / 'prefs'
            prefs.mkdir(parents=True)
            other_cwd.mkdir()
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
            sentinel, previous = self.__set_meipass(app_root)
            try:
                os.chdir(other_cwd)
                with patch.dict(os.environ, {'SIMS4_TRANSLATOR_CONFIG_DIR': str(user_config_dir)}):
                    manager = ConfigManager()
                    manager.save()
            finally:
                os.chdir(cwd)
                self.__restore_meipass(sentinel, previous)

            self.assertEqual(manager.value('translation', 'destination'), 'RUS_RU')
            self.assertEqual(manager.value('api', 'deepl_key'), 'sample:fx')
            self.assertTrue((user_config_dir / 'config.xml').exists())
            self.assertIn('<destination>RUS_RU</destination>', legacy.read_text(encoding='utf-8'))

    def test_legacy_prefs_config_uses_app_bundle_not_current_working_directory(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            app_root = root / 'app'
            cwd_root = root / 'cwd'
            (app_root / 'prefs').mkdir(parents=True)
            (cwd_root / 'prefs').mkdir(parents=True)
            (app_root / 'prefs' / 'config.xml').write_text(
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<config>\n'
                '  <translation><source>ENG_US</source><destination>SPA_ES</destination></translation>\n'
                '</config>\n',
                encoding='utf-8',
            )
            (cwd_root / 'prefs' / 'config.xml').write_text(
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<config>\n'
                '  <translation><source>ENG_US</source><destination>UKR_UA</destination></translation>\n'
                '</config>\n',
                encoding='utf-8',
            )

            sentinel, previous = self.__set_meipass(app_root)
            try:
                os.chdir(cwd_root)
                with patch.dict(os.environ, {'SIMS4_TRANSLATOR_CONFIG_DIR': str(root / 'userdata')}):
                    manager = ConfigManager()
            finally:
                os.chdir(cwd)
                self.__restore_meipass(sentinel, previous)

            self.assertEqual(manager.value('translation', 'destination'), 'SPA_ES')

    def test_save_does_not_create_repo_prefs_config_when_user_config_is_available(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            app_root = root / 'app'
            app_root.mkdir()
            user_config_dir = root / 'userdata'
            sentinel, previous = self.__set_meipass(app_root)
            try:
                os.chdir(root)
                with patch.dict(os.environ, {'SIMS4_TRANSLATOR_CONFIG_DIR': str(user_config_dir)}):
                    manager = ConfigManager()
                    manager.set_value('api', 'deepl_key', 'sample:fx')
                    manager.save()
            finally:
                os.chdir(cwd)
                self.__restore_meipass(sentinel, previous)

            self.assertFalse((root / 'prefs' / 'config.xml').exists())
            self.assertIn('sample:fx', (user_config_dir / 'config.xml').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
