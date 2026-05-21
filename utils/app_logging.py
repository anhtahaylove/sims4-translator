# -*- coding: utf-8 -*-

import logging
import os
import re
import sys
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
    re.compile(r'(?i)(auth[_\-\s]*key\s*[:=]\s*)(\S+)'),
    re.compile(r'\b[A-Za-z0-9_-]{20,}:fx\b'),
)


_signals_attached = False


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
    sys.excepthook = _build_excepthook(logger, sys.excepthook)
    logger.info('%s logging started', APP_NAME)
    return logger


def _attach_signals(logger: logging.Logger) -> None:
    global _signals_attached
    if _signals_attached:
        return
    window_signals.log.connect(lambda message: logger.info('Activity: %s', redact_sensitive(message)))
    task_runner_signals.error.connect(
        lambda handle, error: logger.error(
            'Background task failed: %s: %s: %s',
            getattr(handle, 'name', 'Task'),
            getattr(error, 'exception_type', 'Error'),
            redact_sensitive(getattr(error, 'message', '')),
        )
    )
    _signals_attached = True


def _build_excepthook(logger: logging.Logger, previous):
    def excepthook(exc_type, exc_value, exc_traceback):
        logger.exception(
            'Unhandled exception',
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        if previous and previous is not excepthook:
            previous(exc_type, exc_value, exc_traceback)
    return excepthook
