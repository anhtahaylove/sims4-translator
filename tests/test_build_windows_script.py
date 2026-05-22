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
        self.assertIn("Built app must not write prefs\\config.xml beside the executable", self.script)
        self.assertIn('SIMS4_TRANSLATOR_CONFIG_DIR', self.script)

    def test_build_script_keeps_pyinstaller_build_only(self):
        self.assertIn('-r requirements-dev.txt -c constraints.txt', self.script)
        forbidden_writes = (
            r'Add-Content\s+.*requirements\.txt',
            r'Set-Content\s+.*requirements\.txt',
            r'Out-File\s+.*requirements\.txt',
            r'>>\s*requirements\.txt',
        )
        for pattern in forbidden_writes:
            self.assertIsNone(re.search(pattern, self.script, re.IGNORECASE), pattern)

    def test_build_script_runs_release_verification_steps(self):
        self.assertIn("Run clean-checkout fast checks", self.script)
        self.assertIn("check_fast.ps1", self.script)
        self.assertIn('python scripts\\verify_synthetic_smoke.py --directory build\\synthetic', self.script)
        self.assertNotIn('--require-gui-outputs', self.script)

    def test_fast_check_script_runs_clean_checkout_checks(self):
        script = Path('scripts/check_fast.ps1').read_text(encoding='utf-8')
        self.assertIn('python -m unittest discover -s tests -v', script)
        self.assertIn('python -m compileall -q models packer singletons storages themes utils widgets windows tests scripts main.py', script)
        self.assertIn('python scripts\\create_synthetic_package.py', script)
        self.assertIn('python scripts\\verify_synthetic_smoke.py --directory build\\synthetic', script)
        self.assertNotIn('--require-gui-outputs', script)
        self.assertIn('python scripts\\verify_version_sync.py --version 2.0.2', script)
        self.assertIn(
            'python scripts\\verify_interface_i18n.py --language vi_VN --version 2.0.2 --strict-empty --strict-missing',
            script,
        )
        self.assertIn('git diff --check', script)

    def test_release_check_keeps_gui_output_requirement_outside_clean_build(self):
        script = Path('scripts/check_release.ps1').read_text(encoding='utf-8')
        self.assertIn('check_fast.ps1', script)
        self.assertIn('python scripts\\verify_synthetic_smoke.py --directory build\\synthetic --require-gui-outputs', script)
        self.assertIn('package_release.ps1', script)

    def test_package_release_script_creates_zip_and_sha256(self):
        script = Path('scripts/package_release.ps1').read_text(encoding='utf-8')
        self.assertIn('The-Sims-4-Translator-Plus-v$Version-windows.zip', script)
        self.assertIn('Get-FileHash', script)
        self.assertIn('.sha256', script)
        self.assertIn("Release bundle must not include prefs\\config.xml", script)

    def test_release_build_workflow_uploads_zip_and_checksum_artifacts(self):
        workflow = Path('.github/workflows/release-build.yml').read_text(encoding='utf-8')
        self.assertIn('workflow_dispatch', workflow)
        self.assertIn("tags:", workflow)
        self.assertIn('contents: write', workflow)
        self.assertIn('id-token: write', workflow)
        self.assertIn('attestations: write', workflow)
        self.assertIn('artifact-metadata: write', workflow)
        self.assertIn('scripts\\build_windows.ps1', workflow)
        self.assertIn('scripts\\package_release.ps1', workflow)
        self.assertIn('actions/attest@v4', workflow)
        self.assertIn('sigstore/cosign-installer@v4.1.2', workflow)
        self.assertIn('cosign sign-blob --yes --bundle', workflow)
        self.assertIn('cosign verify-blob', workflow)
        self.assertIn('gh release create', workflow)
        self.assertIn('actions/upload-artifact@v4', workflow)
        self.assertIn('The-Sims-4-Translator-Plus-v${{ steps.version.outputs.version }}-windows.zip', workflow)
        self.assertIn('The-Sims-4-Translator-Plus-v${{ steps.version.outputs.version }}-windows.zip.sha256', workflow)
        self.assertIn('The-Sims-4-Translator-Plus-v${{ steps.version.outputs.version }}-windows.zip.sigstore.json', workflow)

    def test_release_download_verifier_checks_public_zip_layout_and_checksum(self):
        script = Path('scripts/verify_release_download.ps1').read_text(encoding='utf-8')
        self.assertIn('Invoke-RestMethod', script)
        self.assertIn('Invoke-WebRequest', script)
        self.assertIn('Get-FileHash', script)
        self.assertIn('Expand-Archive', script)
        self.assertIn('[switch]$VerifyProvenance', script)
        self.assertIn('The-Sims-4-Translator-Plus-v$ReleaseVersion-windows.zip', script)
        self.assertIn('$ZipName.sigstore.json', script)
        self.assertIn('gh attestation verify', script)
        self.assertIn('cosign verify-blob', script)
        self.assertIn('--certificate-oidc-issuer', script)
        self.assertIn('prefs\\languages.xml', script)
        self.assertIn('fonts\\RobotoRegular.ttf', script)
        self.assertIn('Release ZIP must not include prefs\\config.xml', script)
        self.assertIn('SIMS4_TRANSLATOR_CONFIG_DIR', script)


if __name__ == '__main__':
    unittest.main()
