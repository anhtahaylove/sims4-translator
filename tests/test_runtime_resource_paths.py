# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import unittest
from pathlib import Path

from singletons.config import config
from singletons.expansions import Expansions
from singletons.interface import Interface
from singletons.languages import Languages
from utils.runtime_paths import resource_path


class RuntimeResourcePathTests(unittest.TestCase):

    def setUp(self):
        self.__previous_cwd = os.getcwd()
        self.__sentinel = object()
        self.__previous_meipass = getattr(sys, '_MEIPASS', self.__sentinel)

    def tearDown(self):
        os.chdir(self.__previous_cwd)
        if self.__previous_meipass is self.__sentinel:
            if hasattr(sys, '_MEIPASS'):
                delattr(sys, '_MEIPASS')
        else:
            setattr(sys, '_MEIPASS', self.__previous_meipass)

    @staticmethod
    def __write_interface_catalog(path: Path, code: str, translated_file: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            f'<ts language="{code}" name="{code}" version="test" authors="">\n'
            '  <context name="MainWindow">\n'
            '    <string><source>File</source>'
            f'<translation>{translated_file}</translation></string>\n'
            '  </context>\n'
            '</ts>\n',
            encoding='utf-8',
        )

    def test_resource_path_prefers_pyinstaller_bundle_over_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bundle = root / 'bundle'
            cwd = root / 'cwd'
            bundle.mkdir()
            cwd.mkdir()
            try:
                setattr(sys, '_MEIPASS', str(bundle))
                os.chdir(cwd)

                self.assertEqual(resource_path('prefs', 'languages.xml'), bundle / 'prefs' / 'languages.xml')
            finally:
                os.chdir(self.__previous_cwd)

    def test_interface_catalogs_load_from_bundle_independent_of_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bundle = root / 'bundle'
            cwd = root / 'cwd'
            self.__write_interface_catalog(bundle / 'prefs' / 'interface' / 'bundle.xml', 'zz_ZZ', 'Bundled')
            self.__write_interface_catalog(cwd / 'prefs' / 'interface' / 'cwd.xml', 'yy_YY', 'CWD')
            cwd.mkdir(exist_ok=True)

            old_language = config.value('interface', 'language')
            try:
                setattr(sys, '_MEIPASS', str(bundle))
                os.chdir(cwd)
                config.set_value('interface', 'language', 'zz_ZZ')
                loaded = Interface()
            finally:
                os.chdir(self.__previous_cwd)
                config.set_value('interface', 'language', old_language)

            languages = {lang.code: lang for lang in loaded.languages}
            self.assertIn('zz_ZZ', languages)
            self.assertNotIn('yy_YY', languages)
            self.assertEqual(loaded.text('MainWindow', 'File'), 'Bundled')

    def test_languages_metadata_loads_from_bundle_independent_of_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bundle = root / 'bundle'
            cwd = root / 'cwd'
            (bundle / 'prefs').mkdir(parents=True)
            (cwd / 'prefs').mkdir(parents=True)
            (bundle / 'prefs' / 'languages.xml').write_text(
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<lng><language locale="SPA_ES" code="0x13" google-code="es" deepl-code="ES"/></lng>\n',
                encoding='utf-8',
            )
            (cwd / 'prefs' / 'languages.xml').write_text(
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<lng><language locale="UKR_UA" code="0x17" google-code="uk" deepl-code="UA"/></lng>\n',
                encoding='utf-8',
            )

            try:
                setattr(sys, '_MEIPASS', str(bundle))
                os.chdir(cwd)
                loaded = Languages()
            finally:
                os.chdir(self.__previous_cwd)

            self.assertIsNotNone(loaded.by_locale('SPA_ES'))
            self.assertIsNone(loaded.by_locale('UKR_UA'))

    def test_dlc_metadata_loads_from_bundle_independent_of_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bundle = root / 'bundle'
            cwd = root / 'cwd'
            (bundle / 'prefs').mkdir(parents=True)
            (cwd / 'prefs').mkdir(parents=True)
            (bundle / 'prefs' / 'dlc.ini').write_text(
                '[EP99]\nname_en_us=Bundled Pack\ntype=Expansion Pack\n',
                encoding='utf-8',
            )
            (cwd / 'prefs' / 'dlc.ini').write_text(
                '[EP98]\nname_en_us=CWD Pack\ntype=Game Pack\n',
                encoding='utf-8',
            )

            try:
                setattr(sys, '_MEIPASS', str(bundle))
                os.chdir(cwd)
                loaded = Expansions()._parse_expansion_packs()
            finally:
                os.chdir(self.__previous_cwd)

            self.assertIn('EP99', loaded)
            self.assertNotIn('EP98', loaded)
            self.assertEqual(loaded['EP99']['names']['name_en_us'], 'Bundled Pack')


if __name__ == '__main__':
    unittest.main()
