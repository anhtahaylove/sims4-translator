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

    def test_build_script_uses_conservative_pyinstaller_excludes_without_upx(self):
        self.assertIn('--noupx', self.script)
        self.assertNotIn('--upx-dir', self.script)
        self.assertNotIn('--upx ', self.script)
        for module in ('tkinter', 'unittest', 'pytest', 'IPython', 'notebook', 'matplotlib'):
            self.assertIn(f'--exclude-module {module}', self.script)

    def test_build_script_excludes_local_user_config_from_release(self):
        self.assertIn("Prepare distributable prefs without local config", self.script)
        self.assertIn("Build prefs bundle must not include local prefs\\config.xml", self.script)
        self.assertIn("Bundled prefs\\config.xml must not be shipped", self.script)
        self.assertIn("Built app must not write prefs\\config.xml beside the executable", self.script)
        self.assertIn('SIMS4_TRANSLATOR_CONFIG_DIR', self.script)
        self.assertIn('sims4-translator-build-smoke-cwd', self.script)
        self.assertIn('-WorkingDirectory $BuildSmokeCwd', self.script)

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
        self.assertIn('python scripts\\verify_version_sync.py --version 2.3.3', script)
        self.assertIn(
            'python scripts\\verify_interface_i18n.py --all --version 2.3.3 --strict-empty --strict-missing',
            script,
        )
        self.assertIn('git diff --check', script)

    def test_release_check_keeps_gui_output_requirement_outside_clean_build(self):
        script = Path('scripts/check_release.ps1').read_text(encoding='utf-8')
        self.assertIn('check_fast.ps1', script)
        self.assertIn('python scripts\\verify_synthetic_smoke.py --directory build\\synthetic --require-gui-outputs', script)
        self.assertIn(
            'python scripts\\visual_i18n_smoke.py --languages english german russian ukrainian brasil chinese vietnamese',
            script,
        )
        self.assertIn('--strict-layout --no-screenshots', script)
        self.assertIn('python scripts\\collect_release_notes.py --version $Version --check', script)
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
        self.assertIn('scripts\\collect_release_notes.py --version $env:RELEASE_VERSION', workflow)
        self.assertIn('build\\release-notes\\v$env:RELEASE_VERSION.md', workflow)
        self.assertIn('actions/attest@v4', workflow)
        self.assertIn('sigstore/cosign-installer@v4.1.2', workflow)
        self.assertIn('cosign sign-blob --yes --bundle', workflow)
        self.assertIn('cosign verify-blob', workflow)
        self.assertIn('Resolve-Path "build\\release-notes\\$Tag.md"', workflow)
        self.assertIn('gh release create', workflow)
        self.assertIn('--verify-tag', workflow)
        self.assertIn('--draft', workflow)
        self.assertIn('gh release edit $Tag --repo $env:GITHUB_REPOSITORY --draft=false --latest', workflow)
        self.assertIn("Invoke-ReleaseVerifyWithRetry", workflow)
        self.assertIn("'release', 'verify'", workflow)
        self.assertIn("'verify-asset'", workflow)
        self.assertIn('Immutable releases cannot be edited or clobbered', workflow)
        self.assertNotIn('gh release upload', workflow)
        self.assertNotIn('--clobber', workflow)
        self.assertIn('runs-on: windows-2025-vs2026', workflow)
        self.assertIn('actions/checkout@v6', workflow)
        self.assertIn('actions/setup-python@v6', workflow)
        self.assertIn('actions/upload-artifact@v7', workflow)
        self.assertIn('The-Sims-4-Translator-Plus-v${{ steps.version.outputs.version }}-windows.zip', workflow)
        self.assertIn('The-Sims-4-Translator-Plus-v${{ steps.version.outputs.version }}-windows.zip.sha256', workflow)
        self.assertIn('The-Sims-4-Translator-Plus-v${{ steps.version.outputs.version }}-windows.zip.sigstore.json', workflow)
        self.assertIn('Generate visual i18n QA screenshots', workflow)
        self.assertIn('Upload visual i18n QA screenshots', workflow)
        self.assertIn('i18n-visual-qa-v${{ steps.version.outputs.version }}', workflow)
        self.assertIn('build/i18n-visual-qa/v${{ steps.version.outputs.version }}/', workflow)
        self.assertIn('--strict-layout --screenshots', workflow)
        self.assertIn('python scripts\\visual_i18n_smoke.py --pseudo', workflow)

    def test_release_notes_script_keeps_verification_guidance(self):
        script = Path('scripts/collect_release_notes.py').read_text(encoding='utf-8')
        self.assertIn('Why this release exists:', script)
        self.assertIn('Why two JSON-looking files?', script)
        self.assertIn('not duplicates', script)
        self.assertIn('gh release verify', script)
        self.assertIn('gh attestation verify', script)
        self.assertIn('cosign verify-blob', script)

    def test_ci_workflow_uses_node24_actions_and_explicit_windows_runner(self):
        workflow = Path('.github/workflows/ci.yml').read_text(encoding='utf-8')
        self.assertIn('runs-on: windows-2025-vs2026', workflow)
        self.assertIn('actions/checkout@v6', workflow)
        self.assertIn('actions/setup-python@v6', workflow)
        self.assertNotIn('windows-latest', workflow)
        self.assertNotIn('actions/checkout@v4', workflow)
        self.assertNotIn('actions/setup-python@v5', workflow)

    def test_release_download_verifier_checks_public_zip_layout_and_checksum(self):
        script = Path('scripts/verify_release_download.ps1').read_text(encoding='utf-8')
        self.assertIn('Invoke-RestMethod', script)
        self.assertIn('Invoke-WebRequest', script)
        self.assertIn('Get-FileHash', script)
        self.assertIn('Expand-Archive', script)
        self.assertIn('[switch]$VerifyProvenance', script)
        self.assertIn('[switch]$VerifyReleaseAttestation', script)
        self.assertIn('The-Sims-4-Translator-Plus-v$ReleaseVersion-windows.zip', script)
        self.assertIn('$ZipName.sigstore.json', script)
        self.assertIn('gh release verify $Tag --repo $Repo', script)
        self.assertIn('gh release verify-asset $Tag $DownloadZip --repo $Repo', script)
        self.assertIn('gh attestation verify', script)
        self.assertIn('cosign verify-blob', script)
        self.assertIn('--certificate-oidc-issuer', script)
        self.assertIn('prefs\\languages.xml', script)
        self.assertIn('fonts\\RobotoRegular.ttf', script)
        self.assertIn('Release ZIP must not include prefs\\config.xml', script)
        self.assertIn('SIMS4_TRANSLATOR_CONFIG_DIR', script)
        self.assertIn('$SmokeCwd', script)
        self.assertIn('-WorkingDirectory $SmokeCwd', script)

    def test_false_positive_evidence_script_collects_verifiable_release_data(self):
        script = Path('scripts/collect_false_positive_evidence.ps1').read_text(encoding='utf-8')
        self.assertIn('verify_release_download.ps1', script)
        self.assertIn('-VerifyProvenance', script)
        self.assertIn('Get-FileHash', script)
        self.assertIn('vendor-submission-template.txt', script)
        self.assertIn('GitHub Artifact Attestation', script)
        self.assertIn('Sigstore/cosign', script)
        self.assertIn('This pack does not upload files', script)
        self.assertIn('false-positive-evidence', script)
        self.assertNotIn('VT_API_KEY', script)
        self.assertNotIn('/api/v3/files', script)

    def test_virustotal_release_checker_reads_api_key_from_environment(self):
        script = Path('scripts/check_virustotal_release.ps1').read_text(encoding='utf-8')
        self.assertIn("[string]$ApiKeyEnvName = 'VT_API_KEY'", script)
        self.assertIn('GetEnvironmentVariable($ApiKeyEnvName', script)
        self.assertIn('[string]$EnvFile', script)
        self.assertIn('[switch]$NoEnvFile', script)
        self.assertIn('[switch]$UpdateEvidencePack', script)
        self.assertIn('Get-ApiKeyFromEnvFile', script)
        self.assertIn('Normalize-SecretValue', script)
        self.assertIn('vendor-submission-template.txt', script)
        self.assertIn('Update-EvidencePackVirusTotalUrls', script)
        self.assertIn('https://www.virustotal.com/api/v3/files/$Sha256/analyse', script)
        self.assertIn('https://www.virustotal.com/api/v3/analyses/', script)
        self.assertIn('https://www.virustotal.com/api/v3/files/$($Target.sha256)', script)
        self.assertIn('New-Object System.Collections.ArrayList', script)
        self.assertIn('Continuing with the latest available report', script)
        self.assertIn('Trim([char]0xFEFF)', script)
        self.assertIn('virustotal-report.json', script)
        self.assertIn('virustotal-report.txt', script)
        self.assertNotIn('PASTE_KEY_HERE', script)
        self.assertNotIn('https://www.virustotal.com/api/v3/files"', script)

    def test_ai_provider_smoke_script_keeps_provider_keys_local(self):
        script = Path('scripts/check_ai_providers.ps1').read_text(encoding='utf-8')
        self.assertIn('Import-DotEnv', script)
        self.assertIn('GEMINI_API_KEY', script)
        self.assertIn('GOOGLE_API_KEY', script)
        self.assertIn('OPENAI_API_KEY', script)
        self.assertIn('OPENAI_BASE_URL', script)
        self.assertIn('OPENAI_MODEL', script)
        self.assertIn('OLLAMA_BASE_URL', script)
        self.assertIn('OLLAMA_MODEL', script)
        self.assertIn('[switch]$Ollama', script)
        self.assertIn('redact_sensitive', script)
        self.assertIn('It does not save keys', script)
        self.assertNotIn('config.save()', script)
        self.assertNotIn('PASTE_KEY_HERE', script)

    def test_false_positive_docs_are_linked_from_public_trust_surfaces(self):
        doc = Path('docs/false-positive-submissions.md').read_text(encoding='utf-8')
        trust = Path('docs/trust-and-safety.md').read_text(encoding='utf-8')
        readme = Path('README.md').read_text(encoding='utf-8')
        readme_vi = Path('README.vi.md').read_text(encoding='utf-8')
        release_checklist = Path('docs/release-checklist.md').read_text(encoding='utf-8')

        self.assertIn('VirusTotal false-positive guidance', doc)
        self.assertIn('SecureAge false-positive form', doc)
        self.assertIn('-UpdateEvidencePack', doc)
        self.assertIn('does not upload files', doc)
        self.assertIn('ignored local `.env`', doc)
        self.assertIn('false-positive-submissions.md', trust)
        self.assertIn('Release attestation (json)', trust)
        self.assertIn('.zip.sigstore.json', trust)
        self.assertIn('should not be described as duplicate files', release_checklist)
        self.assertIn('false-positive review notes', readme)
        self.assertIn('ghi chú false-positive', readme_vi)

    def test_optional_pre_commit_config_runs_focused_checks(self):
        config = Path('.pre-commit-config.yaml').read_text(encoding='utf-8')
        self.assertIn('trailing-whitespace', config)
        self.assertIn('end-of-file-fixer', config)
        self.assertIn('python -m ruff check . --select E9,F63,F7,F82', config)


if __name__ == '__main__':
    unittest.main()
