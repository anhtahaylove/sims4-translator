# -*- coding: utf-8 -*-

import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from singletons.config import config
from singletons.expansions import Expansion, expansions
from windows.options_dialog import Model
from widgets.job_drawer import JobRow, QJobStatusDrawer


def app():
    return QApplication.instance() or QApplication([])


def close_widget(widget):
    widget.close()
    widget.deleteLater()
    app().processEvents()


class PackCatalogTests(unittest.TestCase):

    def setUp(self):
        app()
        expansions.reset_cache()
        config.set_value('interface', 'language', 'en_US')
        config.set_value('translation', 'source', 'ENG_US')
        config.set_value('translation', 'destination', 'FRE_FR')
        config.set_value('dictionaries', 'gamepath', '')

    def test_recent_pack_catalog_entries_are_present_without_sp80(self):
        packs = expansions._parse_expansion_packs()

        expected = {
            'EP20', 'EP21',
            'SP68', 'SP69', 'SP70', 'SP71', 'SP72', 'SP73', 'SP74',
            'SP75', 'SP76', 'SP77', 'SP78', 'SP79', 'SP81', 'SP82',
        }

        self.assertTrue(expected.issubset(set(packs)))
        self.assertNotIn('SP80', packs)
        self.assertEqual(packs['EP21']['metadata']['type'], 'Expansion Pack')
        self.assertEqual(packs['SP82']['metadata']['type'], 'Kit')

    def test_pack_catalog_categorizes_stuff_packs_kits_and_free_pack(self):
        items = expansions.items
        sections = [item for item in items if isinstance(item, str)]
        by_folder = {item.folder: item for item in items if isinstance(item, Expansion)}

        self.assertIn('Stuff packs', sections)
        self.assertIn('Kits', sections)
        self.assertIn('Free packs', sections)
        self.assertEqual(by_folder['SP49'].category, 'stuff')
        self.assertEqual(by_folder['SP68'].category, 'kit')
        self.assertEqual(by_folder['FP01'].category, 'free')

    def test_pack_model_filter_keeps_matching_section_and_summary_counts(self):
        model = Model(filter_text='royalty')
        folders = [item.folder for item in model.items if isinstance(item, Expansion)]

        self.assertEqual(folders, ['EP21'])
        self.assertIn('1 pack', model.summary_text)
        self.assertIn('0 ready', model.summary_text)

    def test_pack_model_category_filter_shows_only_kits(self):
        model = Model(category_filter='kit')
        folders = [item.folder for item in model.items if isinstance(item, Expansion)]

        self.assertIn('SP68', folders)
        self.assertNotIn('EP21', folders)
        self.assertNotIn('FP01', folders)


class JobDrawerStateTests(unittest.TestCase):

    def setUp(self):
        app()

    def test_completed_job_hides_progress_and_cancel_controls(self):
        row = JobRow('Opening file...', handle=object())
        self.assertTrue(row.active)
        self.assertFalse(row.progress_bar.isHidden())
        self.assertFalse(row.cancel_button.isHidden())

        row.finish()

        self.assertFalse(row.active)
        self.assertTrue(row.progress_bar.isHidden())
        self.assertTrue(row.cancel_button.isHidden())
        self.assertEqual(row.property('state'), 'done')
        self.assertEqual(row.percent_label.text(), 'Done')
        close_widget(row)

    def test_activity_drawer_starts_collapsed_but_can_expand(self):
        drawer = QJobStatusDrawer()
        try:
            self.assertTrue(drawer.body.isHidden())
            self.assertFalse(drawer.toggle_button.isChecked())

            drawer.set_expanded(True)

            self.assertFalse(drawer.body.isHidden())
            self.assertTrue(drawer.toggle_button.isChecked())
        finally:
            close_widget(drawer)

    def test_compact_activity_drawer_does_not_auto_expand_for_new_jobs(self):
        class Handle:
            name = 'Opening file...'
            job_id = 'job-1'

            def cancel(self):
                pass

        drawer = QJobStatusDrawer()
        try:
            drawer.set_compact_mode(True)
            drawer.task_started(Handle())

            self.assertTrue(drawer.body.isHidden())
            self.assertIn('active background job', drawer.status_label.text())

            drawer.set_expanded(True)

            self.assertFalse(drawer.body.isHidden())
        finally:
            close_widget(drawer)


if __name__ == '__main__':
    unittest.main()
