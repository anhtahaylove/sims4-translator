# -*- coding: utf-8 -*-

import logging
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from singletons.signals import window_signals
from utils.app_logging import (
    LOG_DIR_ENV,
    LOGGER_NAME,
    _build_excepthook,
    _show_crash_dialog,
    redact_sensitive,
    setup_app_logging,
)
from utils.task_runner import TaskError, task_runner_signals


def app():
    return QApplication.instance() or QApplication([])


class AppLoggingTests(unittest.TestCase):

    def setUp(self):
        self.previous_excepthook = sys.excepthook

    def tearDown(self):
        sys.excepthook = self.previous_excepthook
        self.__close_logger()

    @staticmethod
    def __close_logger():
        logger = logging.getLogger(LOGGER_NAME)
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
        logger.addHandler(logging.NullHandler())

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

    def test_excepthook_logs_traceback_without_dialog_in_headless_context(self):
        previous = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {LOG_DIR_ENV: tmpdir}):
                logger = setup_app_logging(reset=True)
                hook = _build_excepthook(logger, previous)
                try:
                    raise RuntimeError('auth_key: abcdef1234567890abcdef1234567890:fx')
                except RuntimeError:
                    exc_info = sys.exc_info()

                with patch('utils.app_logging._crash_dialog_available', return_value=False), \
                        patch('utils.app_logging._build_crash_dialog') as dialog_builder:
                    hook(*exc_info)

                for handler in logger.handlers:
                    handler.flush()

            text = (Path(tmpdir) / 'app.log').read_text(encoding='utf-8')
            self.__close_logger()

        self.assertIn('Unhandled exception', text)
        self.assertIn('RuntimeError', text)
        self.assertIn('[REDACTED]', text)
        self.assertNotIn('abcdef1234567890abcdef1234567890:fx', text)
        dialog_builder.assert_not_called()
        previous.assert_called_once()

    def test_crash_dialog_copies_redacted_error_details(self):
        app()
        copy_button = object()

        class FakeDialog:
            def __init__(self):
                self.executed = False

            def exec(self):
                self.executed = True

            def clickedButton(self):
                return copy_button

        dialog = FakeDialog()
        secret = 'auth_key: abcdef1234567890abcdef1234567890:fx'
        QApplication.clipboard().clear()

        with patch('utils.app_logging._crash_dialog_available', return_value=True), \
                patch('utils.app_logging._build_crash_dialog', return_value=(dialog, copy_button)):
            _show_crash_dialog(f'Traceback\n{secret}\npath={Path.home()}')

        clipboard_text = QApplication.clipboard().text()
        self.assertTrue(dialog.executed)
        self.assertIn('[REDACTED]', clipboard_text)
        self.assertIn('%USERPROFILE%', clipboard_text)
        self.assertNotIn('abcdef1234567890abcdef1234567890:fx', clipboard_text)

    def test_background_task_errors_log_traceback_details(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {LOG_DIR_ENV: tmpdir}):
                logger = setup_app_logging(reset=True)
                task_runner_signals.error.emit(
                    SimpleNamespace(name='Unit task', job_id='unit-task'),
                    TaskError(
                        'auth_key: abcdef1234567890abcdef1234567890:fx',
                        'RuntimeError',
                        'Traceback details auth_key: abcdef1234567890abcdef1234567890:fx',
                    ),
                )
                for handler in logger.handlers:
                    handler.flush()

            text = (Path(tmpdir) / 'app.log').read_text(encoding='utf-8')
            self.__close_logger()

        self.assertIn('Background task failed: Unit task: RuntimeError', text)
        self.assertIn('Traceback details', text)
        self.assertIn('[REDACTED]', text)
        self.assertNotIn('abcdef1234567890abcdef1234567890:fx', text)


if __name__ == '__main__':
    unittest.main()
