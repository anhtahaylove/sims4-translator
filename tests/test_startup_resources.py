# -*- coding: utf-8 -*-

import os
import tempfile
import unittest
from pathlib import Path

import main as app_main


class StartupResourceTests(unittest.TestCase):

    def test_font_paths_use_pyinstaller_base_independent_of_cwd(self):
        sentinel = object()
        previous_meipass = getattr(app_main.sys, '_MEIPASS', sentinel)
        previous_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as bundle_dir, tempfile.TemporaryDirectory() as other_cwd:
            fonts_dir = Path(bundle_dir) / 'fonts'
            fonts_dir.mkdir()
            expected_font = fonts_dir / 'RobotoRegular.ttf'
            expected_font.write_bytes(b'fake-font-for-path-test')

            try:
                setattr(app_main.sys, '_MEIPASS', bundle_dir)
                os.chdir(other_cwd)

                self.assertEqual(app_main.font_paths(), [expected_font])
            finally:
                os.chdir(previous_cwd)
                if previous_meipass is sentinel:
                    delattr(app_main.sys, '_MEIPASS')
                else:
                    setattr(app_main.sys, '_MEIPASS', previous_meipass)

    def test_platform_style_is_only_added_on_windows(self):
        linux_args = ['app.py']
        app_main.apply_platform_style(linux_args, platform='linux')
        self.assertEqual(linux_args, ['app.py'])

        windows_args = ['app.py']
        app_main.apply_platform_style(windows_args, platform='win32')
        self.assertEqual(windows_args, ['app.py', '-style', 'windows'])


if __name__ == '__main__':
    unittest.main()
