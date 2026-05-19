# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from utils.task_runner import TaskProgress, task_runner_signals


class JobRow(QFrame):

    def __init__(self, title: str, handle=None, parent=None, active: bool = None) -> None:
        super().__init__(parent)
        self.setObjectName('jobRow')
        self.setProperty('state', 'running')

        self.handle = handle
        self.active = handle is not None if active is None else active
        self.current = 0
        self.total = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName('jobTitle')

        self.detail_label = QLabel('', self)
        self.detail_label.setObjectName('jobDetail')

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.detail_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setObjectName('jobProgress')
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(0)
        self.progress_bar.setValue(-1)

        self.percent_label = QLabel('Queued', self)
        self.percent_label.setObjectName('jobPercent')
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.percent_label.setMinimumWidth(56)

        self.cancel_button = QPushButton('Cancel', self)
        self.cancel_button.setObjectName('jobCancelButton')
        self.cancel_button.setEnabled(handle is not None)
        self.cancel_button.setVisible(handle is not None)
        self.cancel_button.clicked.connect(self.cancel)

        layout.addLayout(text_layout, 2)
        layout.addWidget(self.progress_bar, 3)
        layout.addWidget(self.percent_label)
        layout.addWidget(self.cancel_button)

    def cancel(self) -> None:
        if self.handle:
            self.handle.cancel()
            self.detail_label.setText('Cancelling...')
            self.cancel_button.setEnabled(False)
            self.set_state('cancelling')

    def apply_progress(self, progress: TaskProgress) -> None:
        if progress.message:
            self.detail_label.setText(progress.message)

        if progress.total:
            self.total = progress.total
            self.current = progress.current
            self.progress_bar.setMaximum(self.total)
            self.progress_bar.setValue(min(self.current, self.total))
        elif progress.current and self.total:
            self.current += progress.current
            self.progress_bar.setValue(min(self.current, self.total))
        elif progress.current:
            self.progress_bar.setMaximum(0)
            self.progress_bar.setValue(-1)

        self.percent_label.setText(self.percent_text())

    def finish(self, cancelled: bool = False, error: str = '') -> None:
        self.active = False
        self.cancel_button.setEnabled(False)
        self.cancel_button.setVisible(False)
        self.progress_bar.setVisible(False)
        if error:
            self.set_state('error')
            self.detail_label.setText(error)
            self.percent_label.setText('Error')
            return

        if cancelled:
            self.set_state('cancelled')
            self.detail_label.setText('Cancelled')
            self.percent_label.setText('Cancelled')
            return

        self.set_state('done')
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(1)
        self.percent_label.setText('Done')

    def set_state(self, state: str) -> None:
        self.setProperty('state', state)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def percent_text(self) -> str:
        if self.total > 0:
            percent = int(min(self.current, self.total) / self.total * 100)
            return f'{percent}%'
        return 'Running'


class QJobStatusDrawer(QWidget):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName('jobDrawer')

        self.__rows = {}
        self.__legacy_row = None
        self.__legacy_done = 0
        self.__legacy_total = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QFrame(self)
        self.header.setObjectName('jobDrawerHeader')
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(8)

        self.toggle_button = QToolButton(self.header)
        self.toggle_button.setObjectName('jobDrawerToggle')
        self.toggle_button.setText('Jobs')
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.clicked.connect(self.set_expanded)

        self.status_label = QLabel('Idle', self.header)
        self.status_label.setObjectName('jobStatusLabel')

        self.clear_button = QPushButton('Clear', self.header)
        self.clear_button.setObjectName('jobClearButton')
        self.clear_button.clicked.connect(self.clear_finished)

        header_layout.addWidget(self.toggle_button)
        header_layout.addWidget(self.status_label, 1)
        header_layout.addWidget(self.clear_button)

        self.body = QFrame(self)
        self.body.setObjectName('jobDrawerBody')
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(10, 8, 10, 10)
        body_layout.setSpacing(8)

        self.jobs_widget = QWidget(self.body)
        self.jobs_layout = QVBoxLayout(self.jobs_widget)
        self.jobs_layout.setContentsMargins(0, 0, 0, 0)
        self.jobs_layout.setSpacing(6)

        self.empty_label = QLabel('No active background jobs.', self.body)
        self.empty_label.setObjectName('jobEmptyLabel')
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.log = QPlainTextEdit(self.body)
        self.log.setObjectName('jobLog')
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(80)
        self.log.setFixedHeight(74)

        body_layout.addWidget(self.jobs_widget)
        body_layout.addWidget(self.empty_label)
        body_layout.addWidget(self.log)

        layout.addWidget(self.header)
        layout.addWidget(self.body)
        self.set_expanded(False)

        task_runner_signals.started.connect(self.task_started)
        task_runner_signals.progress.connect(self.task_progress)
        task_runner_signals.error.connect(self.task_error)
        task_runner_signals.finished.connect(self.task_finished)

        self.refresh_state()

    @property
    def has_task_jobs(self) -> bool:
        return any(row.active for row in self.__rows.values())

    def set_expanded(self, expanded: bool) -> None:
        self.body.setVisible(expanded)
        self.toggle_button.blockSignals(True)
        self.toggle_button.setChecked(expanded)
        self.toggle_button.blockSignals(False)
        self.toggle_button.setText('Jobs' if expanded else 'Jobs hidden')

    def task_started(self, handle) -> None:
        self.finish_legacy(cancelled=True, silent=True)

        row = JobRow(handle.name, handle, self.jobs_widget)
        self.__rows[handle.job_id] = row
        self.jobs_layout.addWidget(row)
        self.set_expanded(True)
        self.log_message(f'Started: {handle.name}')
        self.refresh_state()

    def task_progress(self, handle, progress: TaskProgress) -> None:
        row = self.__rows.get(handle.job_id)
        if row:
            row.apply_progress(progress)
            self.refresh_state()

    def task_error(self, handle, error) -> None:
        row = self.__rows.get(handle.job_id)
        if row:
            row.finish(error=error.message)
        self.log_message(f'Error: {handle.name}: {error.message}')
        self.refresh_state()

    def task_finished(self, handle, cancelled: bool) -> None:
        row = self.__rows.get(handle.job_id)
        if row:
            row.finish(cancelled=cancelled)
        self.log_message(f'{"Cancelled" if cancelled else "Finished"}: {handle.name}')
        self.refresh_state()

    def start_legacy(self, message: str, total: int) -> None:
        if self.has_task_jobs:
            return

        if self.__legacy_row is None:
            self.__legacy_row = JobRow(message or 'Working', None, self.jobs_widget, active=True)
            self.jobs_layout.addWidget(self.__legacy_row)
            self.log_message(f'Started: {message or "Working"}')
        else:
            self.__legacy_row.title_label.setText(message or 'Working')

        self.set_expanded(True)
        self.__legacy_done = 0
        self.__legacy_total = total
        self.__legacy_row.apply_progress(TaskProgress(0, total, message))
        self.refresh_state()

    def increment_legacy(self) -> None:
        if self.__legacy_row is None or self.has_task_jobs:
            return
        self.__legacy_row.apply_progress(TaskProgress(1, 0, ''))
        self.refresh_state()

    def finish_legacy(self, cancelled: bool = False, silent: bool = False) -> None:
        if self.__legacy_row is None:
            return
        if silent:
            self.__legacy_row.setParent(None)
            self.__legacy_row.deleteLater()
            self.__legacy_row = None
            self.refresh_state()
            return
        self.__legacy_row.finish(cancelled=cancelled)
        if not silent:
            self.log_message('Finished: foreground job')
        self.refresh_state()

    def log_message(self, message: str) -> None:
        if message:
            self.log.appendPlainText(message)

    def clear_finished(self) -> None:
        for job_id, row in tuple(self.__rows.items()):
            if not row.active:
                row.setParent(None)
                row.deleteLater()
                del self.__rows[job_id]

        if self.__legacy_row and not self.__legacy_row.active:
            self.__legacy_row.setParent(None)
            self.__legacy_row.deleteLater()
            self.__legacy_row = None

        self.refresh_state()

    def refresh_state(self) -> None:
        visible_rows = len(self.__rows) + (1 if self.__legacy_row else 0)
        running = sum(1 for row in self.__rows.values() if row.active)
        if self.__legacy_row and self.__legacy_row.active:
            running += 1

        self.empty_label.setVisible(visible_rows == 0)
        self.clear_button.setEnabled(visible_rows > running)

        if running:
            self.status_label.setText(f'{running} active background job(s)')
        elif visible_rows:
            self.status_label.setText('Recent jobs')
        else:
            self.status_label.setText('Idle')
