# -*- coding: utf-8 -*-

from dataclasses import dataclass
import os
from pathlib import Path
from queue import Empty, Queue
import re
import subprocess
from threading import Thread
from typing import Mapping

from singletons.interface import interface
from singletons.translator import (
    OLLAMA_DEFAULT_BASE_URL,
    OLLAMA_RECOMMENDED_MODEL,
    ollama_base_url,
    ollama_models,
)
from utils.task_runner import CancellationToken, TaskReporter


OLLAMA_DOWNLOAD_URL = 'https://ollama.com/download/windows'
OLLAMA_RECOMMENDED_MODEL_SIZE = '8.1 GB'
_PROGRESS_PATTERN = re.compile(r'(\d{1,3})%')


@dataclass(frozen=True)
class OllamaSetupStatus:
    installed: bool
    executable: str
    server_reachable: bool
    models: tuple[str, ...]
    recommended_model_installed: bool
    message: str

    @property
    def can_pull_recommended_model(self) -> bool:
        return self.installed and self.server_reachable and not self.recommended_model_installed


@dataclass(frozen=True)
class OllamaPullResult:
    success: bool
    model: str
    message: str


def find_ollama_executable(env: Mapping[str, str] | None = None) -> str:
    env = env or os.environ
    candidates = []

    for folder in (env.get('PATH') or '').split(os.pathsep):
        if not folder:
            continue
        candidates.append(Path(folder) / 'ollama.exe')
        candidates.append(Path(folder) / 'ollama')

    local_app_data = env.get('LOCALAPPDATA')
    if local_app_data:
        candidates.append(Path(local_app_data) / 'Programs' / 'Ollama' / 'ollama.exe')

    program_files = env.get('ProgramFiles')
    if program_files:
        candidates.append(Path(program_files) / 'Ollama' / 'ollama.exe')

    program_files_x86 = env.get('ProgramFiles(x86)')
    if program_files_x86:
        candidates.append(Path(program_files_x86) / 'Ollama' / 'ollama.exe')

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)

    return ''


def ollama_setup_status(base_url: str = None, env: Mapping[str, str] | None = None) -> OllamaSetupStatus:
    executable = find_ollama_executable(env)
    normalized_base_url = ollama_base_url(base_url)
    timeout = 1 if normalized_base_url == OLLAMA_DEFAULT_BASE_URL else 3
    models_result = ollama_models(normalized_base_url, timeout=timeout)
    server_reachable = models_result.status_code == 200
    models = models_result.models if server_reachable else ()
    recommended_ready = OLLAMA_RECOMMENDED_MODEL in models

    if not executable and not server_reachable:
        message = interface.text(
            'OptionsDialog',
            'Ollama was not found on this computer. Download Ollama to use local models.'
        )
    elif not executable:
        message = interface.text(
            'OptionsDialog',
            'Ollama server is reachable, but the local executable was not found. You can use the server, but this app cannot download models automatically.'
        )
    elif not server_reachable:
        message = interface.text(
            'OptionsDialog',
            'Ollama is installed but the server is not reachable. Start Ollama, then refresh models.'
        )
    elif not recommended_ready:
        message = interface.text(
            'OptionsDialog',
            'Ollama is installed, but the recommended model is missing. Download translategemma:12b here or choose another local model.'
        )
    else:
        message = interface.text(
            'OptionsDialog',
            'Ollama is ready. Recommended model is installed.'
        )

    if not server_reachable and models_result.message and executable:
        message = f'{message} {models_result.message}'

    return OllamaSetupStatus(
        installed=bool(executable),
        executable=executable,
        server_reachable=server_reachable,
        models=tuple(models),
        recommended_model_installed=recommended_ready,
        message=message,
    )


def refresh_ollama_status_task(
        token: CancellationToken,
        reporter: TaskReporter,
        base_url: str = ''
) -> OllamaSetupStatus:
    reporter.progress(0, 0, interface.text('OptionsDialog', 'Checking Ollama setup...'))
    token.raise_if_cancelled()
    status = ollama_setup_status(base_url)
    token.raise_if_cancelled()
    reporter.progress(1, 1, status.message)
    return status


def pull_ollama_model_task(
        token: CancellationToken,
        reporter: TaskReporter,
        executable: str = '',
        model: str = OLLAMA_RECOMMENDED_MODEL
) -> OllamaPullResult:
    executable = executable or find_ollama_executable()
    if not executable:
        return OllamaPullResult(
            False,
            model,
            interface.text('OptionsDialog', 'Ollama executable was not found. Download and start Ollama first.'),
        )

    reporter.progress(0, 100, interface.text('OptionsDialog', 'Starting Ollama model download...'))
    output = []
    last_percent = -1
    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

    process = subprocess.Popen(
        [executable, 'pull', model],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding='utf-8',
        errors='replace',
        shell=False,
        creationflags=creationflags,
    )

    assert process.stdout is not None
    output_queue: Queue[str | None] = Queue()
    reader = Thread(target=_read_process_output, args=(process.stdout, output_queue), daemon=True)
    reader.start()
    while True:
        if token.cancelled:
            _terminate_process(process)
            return OllamaPullResult(
                False,
                model,
                interface.text('OptionsDialog', 'Ollama model download was cancelled.'),
            )

        try:
            chunk = output_queue.get(timeout=0.05)
        except Empty:
            if process.poll() is not None and output_queue.empty():
                break
            continue

        if chunk is None:
            if process.poll() is not None:
                break
            continue

        if chunk:
            output.append(chunk)
            percent = _progress_percent(''.join(output[-300:]))
            if percent is not None and percent != last_percent:
                last_percent = percent
                reporter.progress(
                    percent,
                    100,
                    interface.text('OptionsDialog', 'Downloading {model}: {percent}%').format(
                        model=model,
                        percent=percent,
                    ),
                )
            continue

    return_code = process.wait()
    if return_code == 0:
        reporter.progress(100, 100, interface.text('OptionsDialog', 'Downloaded {model}.').format(model=model))
        return OllamaPullResult(
            True,
            model,
            interface.text('OptionsDialog', 'Downloaded {model}.').format(model=model),
        )

    detail = ''.join(output).strip()
    if len(detail) > 500:
        detail = detail[-500:]
    message = interface.text('OptionsDialog', 'Ollama model download failed with exit code {code}.').format(
        code=return_code,
    )
    if detail:
        message = f'{message} {detail}'
    return OllamaPullResult(False, model, message)


def _progress_percent(text: str) -> int | None:
    matches = _PROGRESS_PATTERN.findall(text or '')
    if not matches:
        return None
    return max(0, min(100, int(matches[-1])))


def _read_process_output(stream, output_queue: Queue[str | None]) -> None:
    try:
        while True:
            chunk = stream.read(1)
            if not chunk:
                break
            output_queue.put(chunk)
    finally:
        output_queue.put(None)


def _terminate_process(process) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass
