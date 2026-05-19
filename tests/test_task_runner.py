# -*- coding: utf-8 -*-

import unittest

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer, QThread

from utils.task_runner import TaskRunner, task_runner_signals


def app():
    return QCoreApplication.instance() or QCoreApplication([])


class TaskRunnerTests(unittest.TestCase):

    def setUp(self):
        app()

    def wait_for(self, handle, timeout=1000):
        loop = QEventLoop()
        handle.finished.connect(lambda _cancelled: loop.quit())
        QTimer.singleShot(timeout, loop.quit)
        loop.exec()

    def test_returns_result_on_main_thread_signal(self):
        runner = TaskRunner(max_threads=1)
        results = []
        finished = []
        job_started = []
        job_progress = []
        job_finished = []

        def work(_token, reporter):
            reporter.progress(1, 1, 'done')
            return ('ok', 42)

        task_runner_signals.started.connect(job_started.append)
        task_runner_signals.progress.connect(lambda handle, progress: job_progress.append((handle.name, progress.message)))
        task_runner_signals.finished.connect(lambda handle, cancelled: job_finished.append((handle.name, cancelled)))

        handle = runner.start(work, job_name='Unit job')
        handle.result.connect(results.append)
        handle.finished.connect(finished.append)

        self.wait_for(handle)

        self.assertEqual(results, [('ok', 42)])
        self.assertEqual(finished, [False])
        self.assertEqual(job_started[-1].name, 'Unit job')
        self.assertIn(('Unit job', 'done'), job_progress)
        self.assertIn(('Unit job', False), job_finished)

    def test_cooperative_cancellation_suppresses_result(self):
        runner = TaskRunner(max_threads=1)
        results = []
        finished = []

        def work(token, _reporter):
            for _ in range(100):
                token.raise_if_cancelled()
                QThread.msleep(1)
            return 'done'

        handle = runner.start(work)
        handle.result.connect(results.append)
        handle.finished.connect(finished.append)
        QTimer.singleShot(5, handle.cancel)

        self.wait_for(handle)

        self.assertEqual(results, [])
        self.assertEqual(finished, [True])

    def test_fast_job_waits_for_post_start_signal_connections(self):
        runner = TaskRunner(max_threads=1)
        results = []
        finished = []

        def work(_token, _reporter):
            return 'fast'

        handle = runner.start(work, job_name='Fast job')

        # Simulate normal caller code doing setup after start() returns.
        # The task must not be able to finish before these connections exist.
        QThread.msleep(20)
        handle.result.connect(results.append)
        handle.finished.connect(finished.append)

        self.wait_for(handle)

        self.assertEqual(results, ['fast'])
        self.assertEqual(finished, [False])


if __name__ == '__main__':
    unittest.main()
