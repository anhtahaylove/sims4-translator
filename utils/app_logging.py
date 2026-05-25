# -*- coding: utf-8 -*-

import logging
import os
import re
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from singletons.config import ConfigManager
from singletons.signals import window_signals
from utils.constants import APP_NAME
from utils.task_runner import task_runner_signals


LOGGER_NAME = 'sims4_translator'
LOG_DIR_ENV = 'SIMS4_TRANSLATOR_LOG_DIR'
API_KEY_PATTERNS = (
    re.compile(r'(?i)(deepl[_\-\s]*(?:api[_\-\s]*)?key\s*[:=]\s*)(\S+)'),
    re.compile(r'(?i)(gemini[_\-\s]*(?:api[_\-\s]*)?key\s*[:=]\s*)(\S+)'),
    re.compile(r'(?i)(openai[_\-\s]*(?:api[_\-\s]*)?key\s*[:=]\s*)(\S+)'),
    re.compile(r'(?i)(auth[_\-\s]*key\s*[:=]\s*)(\S+)'),
    re.compile(r'(?i)(bearer\s+)([A-Za-z0-9._\-]{20,})'),
    re.compile(r'\b[A-Za-z0-9_-]{20,}:fx\b'),
    re.compile(r'\bAIza[0-9A-Za-z_\-]{20,}\b'),
)


_signals_attached = False
_handling_excepthook = False
HEADLESS_QT_PLATFORMS = {'minimal', 'offscreen'}


class RedactingFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        return redact_sensitive(rendered)


def default_log_dir() -> Path:
    override = os.environ.get(LOG_DIR_ENV)
    if override:
        return Path(override)
    return ConfigManager.default_config_dir() / 'logs'


def log_file_path() -> Path:
    return default_log_dir() / 'app.log'


def redact_sensitive(message: object) -> str:
    text = str(message)
    home = str(Path.home())
    if home and home in text:
        text = text.replace(home, '%USERPROFILE%')

    appdata = os.environ.get('APPDATA')
    if appdata and appdata in text:
        text = text.replace(appdata, '%APPDATA%')

    for pattern in API_KEY_PATTERNS:
        if pattern.groups >= 2:
            text = pattern.sub(lambda match: f'{match.group(1)}[REDACTED]', text)
        else:
            text = pattern.sub('[REDACTED]', text)
    return text


def setup_app_logging(log_dir: Path | str | None = None, reset: bool = False) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if reset:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

    target_dir = Path(log_dir) if log_dir is not None else default_log_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / 'app.log'

    if not any(isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename) == target_file
               for handler in logger.handlers):
        handler = RotatingFileHandler(
            target_file,
            maxBytes=1_000_000,
            backupCount=3,
            encoding='utf-8',
        )
        handler.setFormatter(RedactingFormatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)

    _attach_signals(logger)
    previous = getattr(sys.excepthook, '_sims4_previous_excepthook', sys.excepthook)
    sys.excepthook = _build_excepthook(logger, previous)
    logger.info('%s logging started', APP_NAME)
    return logger


def _attach_signals(logger: logging.Logger) -> None:
    global _signals_attached
    if _signals_attached:
        return
    window_signals.log.connect(lambda message: logger.info('Activity: %s', redact_sensitive(message)))
    task_runner_signals.error.connect(lambda handle, error: _log_task_error(logger, handle, error))
    _signals_attached = True


def _log_task_error(logger: logging.Logger, handle, error) -> None:
    name = getattr(handle, 'name', 'Task')
    exception_type = getattr(error, 'exception_type', 'Error')
    message = getattr(error, 'message', '')
    details = getattr(error, 'details', '')

    if details:
        logger.error(
            'Background task failed: %s: %s: %s\n%s',
            name,
            exception_type,
            message,
            details,
        )
        return

    logger.error(
        'Background task failed: %s: %s: %s',
        name,
        exception_type,
        message,
    )


def _build_excepthook(logger: logging.Logger, previous):
    def excepthook(exc_type, exc_value, exc_traceback):
        global _handling_excepthook

        details = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        if _handling_excepthook:
            _call_previous_excepthook(previous, excepthook, exc_type, exc_value, exc_traceback)
            return

        _handling_excepthook = True
        try:
            logger.error('Unhandled exception\n%s', details)
            _show_crash_dialog(details)
        except Exception:
            logger.exception('Unhandled exception handler failed')
        finally:
            _handling_excepthook = False

        _call_previous_excepthook(previous, excepthook, exc_type, exc_value, exc_traceback)

    excepthook._sims4_previous_excepthook = previous
    return excepthook


def _call_previous_excepthook(previous, current, exc_type, exc_value, exc_traceback) -> None:
    if previous and previous is not current:
        previous(exc_type, exc_value, exc_traceback)


def _show_crash_dialog(details: str) -> None:
    if not _crash_dialog_available():
        return

    from PySide6.QtWidgets import QApplication

    redacted_details = redact_sensitive(details)
    dialog, copy_button = _build_crash_dialog(redacted_details)
    dialog.exec()

    if dialog.clickedButton() is copy_button:
        QApplication.clipboard().setText(redacted_details)


def _crash_dialog_available() -> bool:
    if os.environ.get('QT_QPA_PLATFORM', '').lower() in HEADLESS_QT_PLATFORMS:
        return False

    try:
        from PySide6.QtWidgets import QApplication
    except Exception:
        return False

    app = QApplication.instance()
    return isinstance(app, QApplication)


def _build_crash_dialog(details: str):
    from PySide6.QtWidgets import QMessageBox

    dialog = QMessageBox()
    dialog.setIcon(QMessageBox.Icon.Critical)
    dialog.setWindowTitle(f'{APP_NAME} Error')
    dialog.setText('The app hit an unexpected error.')
    dialog.setInformativeText(
        'The details were written to the app log. Copy the error details when reporting this issue.'
    )
    dialog.setDetailedText(details)
    copy_button = dialog.addButton('Copy Error', QMessageBox.ButtonRole.ActionRole)
    dialog.addButton(QMessageBox.StandardButton.Close)
    dialog.setDefaultButton(QMessageBox.StandardButton.Close)
    dialog.setEscapeButton(QMessageBox.StandardButton.Close)
    return dialog, copy_button
