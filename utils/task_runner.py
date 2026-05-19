# -*- coding: utf-8 -*-

from dataclasses import dataclass
from itertools import count
from threading import Event
from typing import Any, Callable

from PySide6.QtCore import QCoreApplication, QObject, QRunnable, QThreadPool, QTimer, Signal


@dataclass(frozen=True)
class TaskProgress:
    current: int = 0
    total: int = 0
    message: str = ''


@dataclass(frozen=True)
class TaskError:
    message: str
    exception_type: str


class TaskRunnerSignals(QObject):
    started = Signal(object)
    progress = Signal(object, object)
    error = Signal(object, object)
    finished = Signal(object, bool)


task_runner_signals = TaskRunnerSignals()
_job_ids = count(1)


class CancellationToken:

    def __init__(self) -> None:
        self.__event = Event()

    def cancel(self) -> None:
        self.__event.set()

    @property
    def cancelled(self) -> bool:
        return self.__event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise CancelledTask()


class CancelledTask(Exception):
    pass


class TaskReporter:

    def __init__(self, handle: 'TaskHandle') -> None:
        self.__handle = handle

    def progress(self, current: int = 0, total: int = 0, message: str = '') -> None:
        self.__handle.progress.emit(TaskProgress(current=current, total=total, message=message))


class TaskHandle(QObject):
    progress = Signal(object)
    result = Signal(object)
    error = Signal(object)
    finished = Signal(bool)

    def __init__(self, token: CancellationToken, name: str = '', parent=None) -> None:
        super().__init__(parent)
        self.__token = token
        self.job_id = next(_job_ids)
        self.name = name or f'Task {self.job_id}'

    def cancel(self) -> None:
        self.__token.cancel()

    @property
    def cancelled(self) -> bool:
        return self.__token.cancelled


class TaskRunnable(QRunnable):

    def __init__(
            self,
            handle: TaskHandle,
            token: CancellationToken,
            fn: Callable[..., Any],
            *args,
            **kwargs
    ) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self.__handle = handle
        self.__token = token
        self.__fn = fn
        self.__args = args
        self.__kwargs = kwargs

    def run(self) -> None:
        if self.__token.cancelled:
            self.__handle.finished.emit(True)
            return

        reporter = TaskReporter(self.__handle)

        try:
            result = self.__fn(self.__token, reporter, *self.__args, **self.__kwargs)
            if self.__token.cancelled:
                self.__handle.finished.emit(True)
                return
            self.__handle.result.emit(result)
            self.__handle.finished.emit(False)
        except CancelledTask:
            self.__handle.finished.emit(True)
        except Exception as exc:
            self.__handle.error.emit(TaskError(str(exc), type(exc).__name__))
            self.__handle.finished.emit(False)


class TaskRunner(QObject):

    def __init__(self, max_threads: int = 4, parent=None) -> None:
        super().__init__(parent)
        self.__pool = QThreadPool(self)
        self.__pool.setMaxThreadCount(max(1, max_threads))
        self.__handles = set()

    def start(self, fn: Callable[..., Any], *args, job_name: str = '', **kwargs) -> TaskHandle:
        token = CancellationToken()
        handle = TaskHandle(token, job_name or getattr(fn, '__name__', 'Background task'))
        runnable = TaskRunnable(handle, token, fn, *args, **kwargs)
        self.__handles.add(handle)
        handle.finished.connect(lambda _cancelled, h=handle: self.__handles.discard(h))
        handle.progress.connect(lambda progress, h=handle: task_runner_signals.progress.emit(h, progress))
        handle.error.connect(lambda error, h=handle: task_runner_signals.error.emit(h, error))
        handle.finished.connect(lambda cancelled, h=handle: task_runner_signals.finished.emit(h, cancelled))
        task_runner_signals.started.emit(handle)
        if QCoreApplication.instance():
            QTimer.singleShot(0, lambda runnable=runnable: self.__pool.start(runnable))
        else:
            self.__pool.start(runnable)
        return handle

    def cancel_all(self) -> None:
        for handle in list(self.__handles):
            handle.cancel()

    def wait_for_done(self, msecs: int = -1) -> bool:
        return self.__pool.waitForDone(msecs)
