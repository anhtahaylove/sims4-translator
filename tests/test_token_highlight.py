# -*- coding: utf-8 -*-

import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from singletons.state import app_state
from storages.packages import PackagesStorage
from utils.functions import text_to_table
from widgets.delegate import MainDelegatePaint
from widgets.editor import QTextEditor
from widgets.token_highlight import (
    TOKEN_LINEBREAK,
    TOKEN_NUMBER,
    TOKEN_SIM,
    TOKEN_TAG,
    classify_token,
    iter_highlight_tokens,
    validate_translation_tokens,
)


def app():
    return QApplication.instance() or QApplication([])


class TokenHighlightTests(unittest.TestCase):

    def setUp(self):
        app()
        app_state.set_packages_storage(PackagesStorage())

    def test_token_classifier_distinguishes_tags_linebreaks_numbers_and_sims_tokens(self):
        text = '<i></i> A\\n\\n {0.Number} <b></b> {0.SimFirstName}'

        tokens = [(token.text, token.kind) for token in iter_highlight_tokens(text)]

        self.assertEqual(tokens, [
            ('<i>', TOKEN_TAG),
            ('</i>', TOKEN_TAG),
            ('\\n\\n', TOKEN_LINEBREAK),
            ('{0.Number}', TOKEN_NUMBER),
            ('<b>', TOKEN_TAG),
            ('</b>', TOKEN_TAG),
            ('{0.SimFirstName}', TOKEN_SIM),
        ])
        self.assertEqual(classify_token('{1.Money}'), TOKEN_NUMBER)

    def test_table_text_keeps_linebreak_tokens_visible_for_highlighting(self):
        self.assertEqual(text_to_table('Hello\\n\\nWorld\nAgain'), 'Hello\\n\\nWorld\\nAgain')

    def test_translation_token_validator_reports_missing_extra_order_and_linebreaks(self):
        missing = validate_translation_tokens(
            'Hello\\n{0.SimFirstName}<b></b>',
            'Bonjour{0.SimFirstName}<i></i>',
        )

        self.assertFalse(missing.ok)
        self.assertIn('\\n', missing.missing)
        self.assertIn('<b>', missing.missing)
        self.assertIn('</b>', missing.missing)
        self.assertIn('<i>', missing.extra)
        self.assertIn('</i>', missing.extra)
        self.assertTrue(missing.linebreak_mismatch)
        self.assertIn('Missing', missing.summary())

        reordered = validate_translation_tokens('{0.SimFirstName} {1.Money}', '{1.Money} {0.SimFirstName}')
        self.assertFalse(reordered.ok)
        self.assertTrue(reordered.order_mismatch)

        ok = validate_translation_tokens('{0.SimFirstName}\\n{1.Money}', '{0.SimFirstName}\\n{1.Money}')
        self.assertTrue(ok.ok)

    def test_table_delegate_renders_different_highlight_spans_for_token_groups(self):
        delegate = MainDelegatePaint()

        rendered = delegate._MainDelegatePaint__highlight_html(
            '<font color="#1E81E6">{0.Number}</font>\\n{0.SimFirstName}<b></b>',
            selected=False,
        )

        self.assertIn('&lt;font color=&quot;#1E81E6&quot;&gt;', rendered)
        self.assertIn('{0.Number}', rendered)
        self.assertIn('\\n', rendered)
        self.assertIn('{0.SimFirstName}', rendered)
        self.assertGreaterEqual(rendered.count('background-color'), 6)

    def test_editor_highlighter_uses_preview_token_groups(self):
        editor = QTextEditor()
        try:
            editor.setPlainText('<b></b>\\n{0.SimFirstName} {1.Money}')
            editor.highlighter.rehighlight()
            app().processEvents()

            formats = editor.document().firstBlock().layout().formats()
            highlighted = [
                (
                    editor.document().firstBlock().text()[fmt.start:fmt.start + fmt.length],
                    fmt.format.foreground().color().name(),
                    fmt.format.background().color().name(),
                )
                for fmt in formats
            ]

            self.assertEqual([item[0] for item in highlighted], [
                '<b></b>',
                '\\n',
                '{0.SimFirstName}',
                '{1.Money}',
            ])
            self.assertGreaterEqual(len({item[2] for item in highlighted}), 3)
        finally:
            editor.close()


if __name__ == '__main__':
    unittest.main()
