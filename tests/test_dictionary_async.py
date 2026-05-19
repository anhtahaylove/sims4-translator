# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from packer import Packer
from singletons.state import app_state
from storages.dictionaries import DictionariesStorage
from utils.constants import DICTIONARY_VERSION


def app():
    return QCoreApplication.instance() or QCoreApplication([])


def wait_for(handle, timeout=1000):
    loop = QEventLoop()
    handle.finished.connect(lambda _cancelled: loop.quit())
    QTimer.singleShot(timeout, loop.quit)
    loop.exec()


def write_dictionary(path, rows):
    packer = Packer(b'', mode='w')
    packer.put_raw_bytes(b'DCT')
    packer.put_byte(DICTIONARY_VERSION)
    packer.put_json(rows)
    with open(path, 'w+b') as fp:
        fp.write(packer.get_content())


class AsyncDictionaryLoadTests(unittest.TestCase):

    def setUp(self):
        app()

    def test_async_load_builds_same_lookup_state_as_sync_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rows = [
                [0x2A, 'Hello', 'Bonjour', ''],
                [0x2B, 'World', 'Monde', 'note'],
            ]
            write_dictionary(os.path.join(tmpdir, 'base.dct'), rows)

            sync_storage = DictionariesStorage()
            sync_storage.directory = tmpdir
            sync_storage.load()

            async_storage = DictionariesStorage()
            async_storage.directory = tmpdir
            app_state.set_dictionaries_storage(async_storage)

            handle = async_storage.load(asynchronous=True)
            self.assertIsNotNone(handle)
            wait_for(handle)

            self.assertTrue(async_storage.loaded)
            self.assertEqual(async_storage.search(sid=0x2A), sync_storage.search(sid=0x2A))
            self.assertEqual(async_storage.search(source='World'), sync_storage.search(source='World'))
            self.assertEqual(async_storage.model.items, sync_storage.model.items)


if __name__ == '__main__':
    unittest.main()
