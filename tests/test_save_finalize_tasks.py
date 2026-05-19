# -*- coding: utf-8 -*-

import os
import pathlib
import tempfile
import unittest

from packer.resource import ResourceID
from scripts.synthetic_package import create_synthetic_package
from storages.package_tasks import (
    FinalizePackageRequest,
    SavePackageRequest,
    SaveStringDTO,
    finalize_package_task,
    save_package_task,
)
from utils.constants import FLAG_VALIDATED
from utils.task_runner import CancellationToken, CancelledTask, TaskReporter


class CancellingReporter(TaskReporter):

    def __init__(self, token: CancellationToken, cancel_on_message: int = 2):
        self.token = token
        self.cancel_on_message = cancel_on_message
        self.message_count = 0

    def progress(self, current: int = 0, total: int = 0, message: str = '') -> None:
        if message:
            self.message_count += 1
            if self.message_count >= self.cancel_on_message:
                self.token.cancel()


class NoopReporter(TaskReporter):

    def __init__(self):
        pass

    def progress(self, current: int = 0, total: int = 0, message: str = '') -> None:
        pass


def write_package(path):
    info = create_synthetic_package(
        path,
        source_strings={42: 'Hello'},
        destination_strings={42: 'Bonjour'},
        include_duplicate=False,
        include_extra=False,
    )
    return info.source


def save_request(path, source):
    return SavePackageRequest(
        path=path,
        items=(SaveStringDTO(source, 42, 'Salut', FLAG_VALIDATED),),
        convert=True,
        experimental=False,
        destination_locale='FRE_FR',
        message='Saving package...'
    )


def finalize_request(source_path, target_path, source):
    return FinalizePackageRequest(
        source_path=source_path,
        target_path=target_path,
        items=(SaveStringDTO(source, 42, 'Salut', FLAG_VALIDATED),),
        backup=False,
        destination_locale='FRE_FR',
        message='Saving package...'
    )


class SaveFinalizeTaskTests(unittest.TestCase):

    def test_cancelled_save_removes_temp_package(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = ResourceID(group=0, instance=0x0000000000000001, type=0x220557DA)
            target_path = os.path.join(tmpdir, 'saved.package')
            token = CancellationToken()

            with self.assertRaises(CancelledTask):
                save_package_task(token, CancellingReporter(token), save_request(target_path, source))

            self.assertFalse(os.path.exists(target_path))
            self.assertFalse(os.path.exists(target_path + '.tmp'))

    def test_cancelled_finalize_removes_target_temp_and_source_copy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, 'source.package')
            target_path = os.path.join(tmpdir, 'finalized.package')
            source = write_package(source_path)
            temp_source_copy = pathlib.Path(tempfile.gettempdir()) / os.path.basename(source_path)
            temp_source_copy.unlink(missing_ok=True)
            token = CancellationToken()

            with self.assertRaises(CancelledTask):
                finalize_package_task(token, CancellingReporter(token), finalize_request(source_path, target_path, source))

            self.assertFalse(os.path.exists(target_path))
            self.assertFalse(os.path.exists(target_path + '.tmp'))
            self.assertFalse(temp_source_copy.exists())

    def test_finalize_error_before_writer_commit_removes_source_copy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, 'source.package')
            target_path = os.path.join(tmpdir, 'missing', 'finalized.package')
            source = write_package(source_path)
            temp_source_copy = pathlib.Path(tempfile.gettempdir()) / os.path.basename(source_path)
            temp_source_copy.unlink(missing_ok=True)

            with self.assertRaises(OSError):
                finalize_package_task(CancellationToken(), NoopReporter(), finalize_request(source_path, target_path, source))

            self.assertFalse(os.path.exists(target_path))
            self.assertFalse(os.path.exists(target_path + '.tmp'))
            self.assertFalse(temp_source_copy.exists())


if __name__ == '__main__':
    unittest.main()
