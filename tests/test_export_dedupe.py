# -*- coding: utf-8 -*-

import unittest

from packer.resource import ResourceID
from packer.stbl import Stbl
from storages.package_tasks import SaveStringDTO, _build_stbl
from utils.constants import FLAG_TRANSLATED
from utils.task_runner import CancellationToken, TaskReporter


class NoopReporter(TaskReporter):

    def __init__(self):
        pass

    def progress(self, current: int = 0, total: int = 0, message: str = '') -> None:
        pass


class ExportDedupeTests(unittest.TestCase):

    def test_save_stbl_build_collapses_duplicate_string_keys(self):
        rid = ResourceID(group=0, instance=1, type=0x220557DA)
        rows = (
            SaveStringDTO(rid, 42, 'Bonjour', FLAG_TRANSLATED),
            SaveStringDTO(rid, 42, 'Bonjour', FLAG_TRANSLATED),
            SaveStringDTO(rid, 7, 'Salut', FLAG_TRANSLATED),
        )

        stbl = _build_stbl(
            CancellationToken(),
            NoopReporter(),
            rows,
            convert=True,
            experimental=False,
            destination_locale='ENG_US',
            message='Saving...'
        )

        self.assertEqual(len(stbl), 1)
        exported = next(iter(stbl.values()))
        parsed = Stbl(exported.rid, exported.binary).strings
        self.assertEqual(parsed, {42: 'Bonjour', 7: 'Salut'})


if __name__ == '__main__':
    unittest.main()
