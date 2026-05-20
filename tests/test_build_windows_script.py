# -*- coding: utf-8 -*-

import re
import unittest
from pathlib import Path


class BuildWindowsScriptTests(unittest.TestCase):

    def setUp(self):
        self.script = Path('scripts/build_windows.ps1').read_text(encoding='utf-8')

    def test_build_script_uses_verified_pyinstaller_layout(self):
        self.assertIn('--contents-directory .', self.script)
        self.assertIn('sims4-translator-build-prefs', self.script)
        self.assertIn('--add-data "$BuildPrefs;prefs"', self.script)
        self.assertIn("--add-data 'fonts;fonts'", self.script)
        self.assertIn('resources\\logo.ico', self.script)
        self.assertIn('The Sims 4 Translator Plus', self.script)

    def test_build_script_excludes_local_user_config_from_release(self):
        self.assertIn("Prepare distributable prefs without local config", self.script)
        self.assertIn("Build prefs bundle must not include local prefs\\config.xml", self.script)
        self.assertIn("Bundled prefs\\config.xml must not be shipped", self.script)
        self.assertIn("Remove-Item -LiteralPath $GeneratedConfig -Force", self.script)

    def test_build_script_keeps_pyinstaller_build_only(self):
        self.assertIn('-r requirements.txt pyinstaller', self.script)
        forbidden_writes = (
            r'Add-Content\s+.*requirements\.txt',
            r'Set-Content\s+.*requirements\.txt',
            r'Out-File\s+.*requirements\.txt',
            r'>>\s*requirements\.txt',
        )
        for pattern in forbidden_writes:
            self.assertIsNone(re.search(pattern, self.script, re.IGNORECASE), pattern)

    def test_build_script_runs_release_verification_steps(self):
        self.assertIn('python -m unittest discover -s tests -v', self.script)
        self.assertIn('python -m compileall -q models packer singletons storages themes utils widgets windows tests scripts main.py', self.script)
        self.assertIn('python scripts\\create_synthetic_package.py', self.script)
        self.assertIn('python scripts\\verify_synthetic_smoke.py --directory build\\synthetic --require-gui-outputs', self.script)
        self.assertIn('git diff --check', self.script)


if __name__ == '__main__':
    unittest.main()
