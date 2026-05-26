# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from singletons.config import config
from singletons.state import app_state
from storages.packages import PackagesStorage
from utils.constants import APP_VERSION
from utils.diagnostics import build_diagnostics_text, provider_health_snapshot


class DiagnosticsTests(unittest.TestCase):

    def setUp(self):
        config.set_value('interface', 'language', 'en_US')
        config.set_value('translation', 'source', 'ENG_US')
        config.set_value('translation', 'destination', 'VI_VN')
        config.set_value('api', 'deepl_key', '')
        config.set_value('api', 'deepl_glossary_id', '')
        config.set_value('api', 'gemini_key', '')
        config.set_value('api', 'gemini_model', 'gemini-2.5-flash')
        config.set_value('api', 'openai_key', '')
        config.set_value('api', 'openai_base_url', 'https://api.openai.com')
        config.set_value('api', 'openai_model', 'gpt-4o-mini')
        config.set_value('api', 'ollama_enabled', False)
        config.set_value('api', 'ollama_base_url', 'http://localhost:11434')
        config.set_value('api', 'ollama_model', 'translategemma:12b')
        app_state.set_packages_storage(PackagesStorage())

    def test_provider_health_snapshot_is_config_only(self):
        config.set_value('api', 'gemini_key', 'gemini-secret')
        config.set_value('api', 'openai_key', 'openai-secret')
        config.set_value('api', 'ollama_enabled', True)

        snapshot = {provider.name: provider for provider in provider_health_snapshot()}

        self.assertTrue(snapshot['Gemini'].configured)
        self.assertTrue(snapshot['OpenAI-compatible'].configured)
        self.assertTrue(snapshot['Ollama'].enabled)
        self.assertEqual(snapshot['DeepL'].status, 'missing-key')

    def test_diagnostics_include_useful_context_and_redact_private_data(self):
        secret = 'auth_key: abcdef1234567890abcdef1234567890:fx'
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / 'app.log'
            log_path.write_text(
                f'Started\n{secret}\npath={Path.home() / "private.package"}\n',
                encoding='utf-8',
            )

            with patch('utils.diagnostics.log_file_path', return_value=log_path):
                text = build_diagnostics_text(log_tail_lines=10)

        self.assertIn(f'App version: {APP_VERSION}', text)
        self.assertIn('Providers:', text)
        self.assertIn('Translation cache:', text)
        self.assertIn('Workspace:', text)
        self.assertIn('[REDACTED]', text)
        self.assertIn('%USERPROFILE%', text)
        self.assertNotIn('abcdef1234567890abcdef1234567890:fx', text)
        self.assertNotIn('private.package', text)
        self.assertIn('[REDACTED_FILE].package', text)
        self.assertNotIn(str(Path.home()), text)


if __name__ == '__main__':
    unittest.main()
