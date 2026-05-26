# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal


class ProgressSignals(QObject):
    initiate = Signal(str, int)
    increment = Signal()
    finished = Signal()


class WindowSignals(QObject):
    message = Signal(str)
    log = Signal(str)


class StorageSignals(QObject):
    updated = Signal()


progress_signals = ProgressSignals()
window_signals = WindowSignals()
storage_signals = StorageSignals()
