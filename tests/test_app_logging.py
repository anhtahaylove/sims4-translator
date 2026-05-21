# -*- coding: utf-8 -*-

import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from singletons.signals import window_signals
from utils.app_logging import LOG_DIR_ENV, LOGGER_NAME, redact_sensitive, setup_app_logging


class AppLoggingTests(unittest.TestCase):

    def tearDown(self):
        self.__close_logger()

    @staticmethod
    def __close_logger():
        logger = logging.getLogger(LOGGER_NAME)
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

    def test_redacts_deepl_keys_and_user_paths(self):
        home_path = str(Path.home() / 'secret-package.package')
        message = f'deepl_key=abcdef1234567890abcdef1234567890:fx path={home_path}'

        redacted = redact_sensitive(message)

        self.assertIn('[REDACTED]', redacted)
        self.assertNotIn('abcdef1234567890abcdef1234567890:fx', redacted)
        self.assertIn('%USERPROFILE%', redacted)
        self.assertNotIn(str(Path.home()), redacted)

    def test_setup_writes_redacted_log_file_under_user_data_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {LOG_DIR_ENV: tmpdir}):
                logger = setup_app_logging(reset=True)
                logger.info('auth_key: abcdef1234567890abcdef1234567890:fx')
                for handler in logger.handlers:
                    handler.flush()

            log_path = Path(tmpdir) / 'app.log'
            text = log_path.read_text(encoding='utf-8')
            self.__close_logger()

        self.assertIn('[REDACTED]', text)
        self.assertNotIn('abcdef1234567890abcdef1234567890:fx', text)

    def test_activity_log_signal_is_written_with_redaction(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {LOG_DIR_ENV: tmpdir}):
                logger = setup_app_logging(reset=True)
                window_signals.log.emit('DeepL key abcdef1234567890abcdef1234567890:fx')
                for handler in logger.handlers:
                    handler.flush()

            text = (Path(tmpdir) / 'app.log').read_text(encoding='utf-8')
            self.__close_logger()

        self.assertIn('Activity:', text)
        self.assertIn('[REDACTED]', text)
        self.assertNotIn('abcdef1234567890abcdef1234567890:fx', text)


if __name__ == '__main__':
    unittest.main()
