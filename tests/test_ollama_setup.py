# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from singletons.translator import OLLAMA_RECOMMENDED_MODEL, OllamaModels
from utils.ollama_setup import (
    OllamaPullResult,
    OllamaSetupStatus,
    find_ollama_executable,
    ollama_setup_status,
    pull_ollama_model_task,
)
from utils.task_runner import CancellationToken


class FakeReporter:

    def __init__(self):
        self.events = []

    def progress(self, current: int = 0, total: int = 0, message: str = '') -> None:
        self.events.append((current, total, message))


class FakeStdout:

    def __init__(self, text: str):
        self.__text = text
        self.__index = 0

    @property
    def done(self) -> bool:
        return self.__index >= len(self.__text)

    def read(self, size: int = 1) -> str:
        if self.done:
            return ''
        chunk = self.__text[self.__index:self.__index + size]
        self.__index += len(chunk)
        return chunk


class FakeProcess:

    def __init__(self, text: str, returncode: int = 0, force_running: bool = False):
        self.stdout = FakeStdout(text)
        self.returncode = returncode
        self.force_running = force_running
        self.terminated = False
        self.killed = False

    def poll(self):
        if self.terminated:
            return -15
        if self.killed:
            return -9
        if self.force_running:
            return None
        if self.stdout.done:
            return self.returncode
        return None

    def wait(self, timeout=None):
        return self.poll()

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


class OllamaSetupTests(unittest.TestCase):

    def test_find_ollama_executable_uses_path_before_fallbacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path_dir = root / 'bin'
            path_dir.mkdir()
            path_exe = path_dir / 'ollama.exe'
            path_exe.write_text('', encoding='utf-8')
            fallback_dir = root / 'Programs' / 'Ollama'
            fallback_dir.mkdir(parents=True)
            (fallback_dir / 'ollama.exe').write_text('', encoding='utf-8')

            found = find_ollama_executable({
                'PATH': str(path_dir),
                'LOCALAPPDATA': str(root),
                'ProgramFiles': '',
                'ProgramFiles(x86)': '',
            })

            self.assertEqual(found, str(path_exe))

    def test_find_ollama_executable_uses_windows_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fallback = root / 'Programs' / 'Ollama' / 'ollama.exe'
            fallback.parent.mkdir(parents=True)
            fallback.write_text('', encoding='utf-8')

            found = find_ollama_executable({
                'PATH': '',
                'LOCALAPPDATA': str(root),
                'ProgramFiles': '',
                'ProgramFiles(x86)': '',
            })

            self.assertEqual(found, str(fallback))

    def test_setup_status_reports_missing_ollama(self):
        with patch('utils.ollama_setup.find_ollama_executable', return_value=''), \
                patch('utils.ollama_setup.ollama_models',
                      return_value=OllamaModels(503, (), 'offline')):
            status = ollama_setup_status('http://localhost:11434')

        self.assertIsInstance(status, OllamaSetupStatus)
        self.assertFalse(status.installed)
        self.assertFalse(status.server_reachable)
        self.assertFalse(status.can_pull_recommended_model)
        self.assertIn('Ollama was not found', status.message)

    def test_setup_status_reports_recommended_model_missing(self):
        with patch('utils.ollama_setup.find_ollama_executable', return_value='C:/Ollama/ollama.exe'), \
                patch('utils.ollama_setup.ollama_models',
                      return_value=OllamaModels(200, ('gemma4:e4b',), '')):
            status = ollama_setup_status('http://localhost:11434')

        self.assertTrue(status.installed)
        self.assertTrue(status.server_reachable)
        self.assertEqual(status.models, ('gemma4:e4b',))
        self.assertFalse(status.recommended_model_installed)
        self.assertTrue(status.can_pull_recommended_model)

    def test_setup_status_reports_ready_when_recommended_model_exists(self):
        with patch('utils.ollama_setup.find_ollama_executable', return_value='C:/Ollama/ollama.exe'), \
                patch('utils.ollama_setup.ollama_models',
                      return_value=OllamaModels(200, (OLLAMA_RECOMMENDED_MODEL,), '')):
            status = ollama_setup_status('http://localhost:11434')

        self.assertTrue(status.recommended_model_installed)
        self.assertFalse(status.can_pull_recommended_model)
        self.assertIn('ready', status.message.lower())

    def test_pull_task_uses_argument_list_and_parses_progress(self):
        reporter = FakeReporter()
        process = FakeProcess('pulling manifest\n50%\n100%\n', returncode=0)
        captured = {}

        def fake_popen(args, **kwargs):
            captured['args'] = args
            captured['kwargs'] = kwargs
            return process

        with patch('utils.ollama_setup.subprocess.Popen', side_effect=fake_popen):
            result = pull_ollama_model_task(
                CancellationToken(),
                reporter,
                'C:/Ollama/ollama.exe',
                OLLAMA_RECOMMENDED_MODEL,
            )

        self.assertIsInstance(result, OllamaPullResult)
        self.assertTrue(result.success)
        self.assertEqual(captured['args'], ['C:/Ollama/ollama.exe', 'pull', OLLAMA_RECOMMENDED_MODEL])
        self.assertFalse(captured['kwargs']['shell'])
        self.assertIn((50, 100, f'Downloading {OLLAMA_RECOMMENDED_MODEL}: 50%'), reporter.events)
        self.assertEqual(reporter.events[-1], (100, 100, f'Downloaded {OLLAMA_RECOMMENDED_MODEL}.'))

    def test_pull_task_handles_nonzero_exit(self):
        reporter = FakeReporter()
        process = FakeProcess('network failed', returncode=1)

        with patch('utils.ollama_setup.subprocess.Popen', return_value=process):
            result = pull_ollama_model_task(
                CancellationToken(),
                reporter,
                'C:/Ollama/ollama.exe',
                OLLAMA_RECOMMENDED_MODEL,
            )

        self.assertFalse(result.success)
        self.assertIn('exit code 1', result.message)
        self.assertIn('network failed', result.message)

    def test_pull_task_terminates_process_on_cancellation(self):
        reporter = FakeReporter()
        process = FakeProcess('', returncode=0, force_running=True)
        token = CancellationToken()
        token.cancel()

        with patch('utils.ollama_setup.subprocess.Popen', return_value=process):
            result = pull_ollama_model_task(
                token,
                reporter,
                'C:/Ollama/ollama.exe',
                OLLAMA_RECOMMENDED_MODEL,
            )

        self.assertFalse(result.success)
        self.assertTrue(process.terminated)
        self.assertIn('cancelled', result.message.lower())


if __name__ == '__main__':
    unittest.main()
