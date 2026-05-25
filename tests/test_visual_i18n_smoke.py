# -*- coding: utf-8 -*-

import os
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from scripts.visual_i18n_smoke import (
    build_pseudo_catalog,
    pseudo_localize_text,
    qa_output_dir,
    scan_widget_layout,
)
from utils.constants import APP_VERSION


def app():
    return QApplication.instance() or QApplication([])


class VisualI18nSmokeTests(unittest.TestCase):

    def test_pseudo_localization_preserves_protected_tokens_and_terms(self):
        source = (
            'Use Ctrl+Enter to Save as package with {0.SimFirstName}, DeepL, Gemini, '
            'OpenAI-compatible, Ollama, token, package, https://example.com, and \\n.'
        )

        pseudo = pseudo_localize_text(source)

        self.assertIn('Ctrl+Enter', pseudo)
        self.assertIn('Save as package', pseudo)
        self.assertIn('{0.SimFirstName}', pseudo)
        self.assertIn('DeepL', pseudo)
        self.assertIn('Gemini', pseudo)
        self.assertIn('OpenAI-compatible', pseudo)
        self.assertIn('Ollama', pseudo)
        self.assertIn('token', pseudo)
        self.assertIn('package', pseudo)
        self.assertIn('https://example.com', pseudo)
        self.assertIn('\\n', pseudo)
        self.assertGreater(len(pseudo), len(source))

    def test_pseudo_catalog_uses_current_english_sources(self):
        catalog = build_pseudo_catalog()

        self.assertIn('MainWindow', catalog)
        self.assertIn('OptionsDialog', catalog)
        self.assertIn('ReleaseValidationDialog', catalog)
        self.assertIn('File', catalog['MainWindow'])
        self.assertTrue(catalog['MainWindow']['File'])

    def test_visual_qa_output_path_stays_under_build_directory(self):
        path = qa_output_dir(APP_VERSION, 'german').resolve()
        build = (Path.cwd() / 'build').resolve()

        self.assertTrue(str(path).startswith(str(build)))
        self.assertIn('i18n-visual-qa', path.parts)

    def test_layout_scanner_detects_obvious_button_clipping(self):
        app()
        button = QPushButton('This button label is intentionally far too long for the rendered width')
        button.resize(40, 24)
        button.show()
        try:
            issues = scan_widget_layout('unit', button)
        finally:
            button.close()
            button.deleteLater()

        self.assertTrue(issues)
        self.assertEqual(issues[0].window, 'unit')

    def test_layout_scanner_ignores_wrapping_labels(self):
        app()
        label = QLabel('This label is intentionally long but configured to wrap instead of clipping.')
        label.setWordWrap(True)
        label.resize(80, 80)
        label.show()
        try:
            issues = scan_widget_layout('unit', label)
        finally:
            label.close()
            label.deleteLater()

        self.assertEqual(issues, [])


if __name__ == '__main__':
    unittest.main()
