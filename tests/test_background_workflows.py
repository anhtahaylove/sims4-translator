# -*- coding: utf-8 -*-

import re
import unittest
from pathlib import Path


class BackgroundWorkflowTests(unittest.TestCase):

    def test_heavy_ui_workflows_continue_to_use_task_runner(self):
        packages = Path('storages/packages.py').read_text(encoding='utf-8')
        dictionaries = Path('storages/dictionaries.py').read_text(encoding='utf-8')
        export_dialog = Path('windows/export_dialog.py').read_text(encoding='utf-8')
        translate_dialog = Path('windows/translate_dialog.py').read_text(encoding='utf-8')
        edit_dialog = Path('windows/edit_dialog.py').read_text(encoding='utf-8')

        self.assertRegex(packages, re.compile(r'self\.__runner\.start\(\s*load_packages_task', re.DOTALL))
        self.assertIn('return self.__start_save(save_package_task, request)', packages)
        self.assertIn('return self.__start_save(finalize_package_task, request)', packages)
        self.assertRegex(dictionaries, re.compile(r'self\.__runner\.start\(\s*load_dictionaries_task', re.DOTALL))
        self.assertRegex(export_dialog, re.compile(r'self\.__runner\.start\(\s*export_structured_task', re.DOTALL))
        self.assertRegex(translate_dialog, re.compile(r'self\.__runner\.start\(\s*translate_chunk_task', re.DOTALL))
        self.assertRegex(edit_dialog, re.compile(r'self\.__runner\.start\(\s*edit_translation_task', re.DOTALL))


if __name__ == '__main__':
    unittest.main()
