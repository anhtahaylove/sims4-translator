# -*- coding: utf-8 -*-

import os
import tempfile
import unittest
from pathlib import Path

from packer.resource import ResourceID
from storages.records import MainRecord
from utils.constants import (
    FLAG_PROGRESS,
    FLAG_TRANSLATED,
    FLAG_UNVALIDATED,
    FLAG_VALIDATED,
)
from utils.release_validation import (
    CATEGORY_CONSISTENCY,
    CATEGORY_DUPLICATE,
    CATEGORY_LAYOUT,
    PROFILE_SOFT,
    PROFILE_STRICT,
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
    ValidationRequest,
    terminology_terms_for_locale,
    validate_release_task,
    validate_release_records,
)
from utils.task_runner import CancelledTask


def make_record(
        idx=1,
        sid=0x2A,
        source='Hello',
        translation='Xin chao',
        flag=FLAG_VALIDATED,
        instance=0x0000000000001234,
        package='sample.package',
        source_old=None,
        translate_old=None,
):
    rid = ResourceID(group=0, instance=instance, type=0x220557DA)
    return MainRecord(
        idx,
        sid,
        rid.instance,
        rid.group,
        source,
        translation,
        flag,
        rid,
        rid,
        package,
        source_old,
        translate_old,
        (idx, idx, idx, idx),
        '',
    )


class ReleaseValidationTests(unittest.TestCase):

    def reasons(self, report, severity=None):
        return [issue.reason for issue in report.issues if severity is None or issue.severity == severity]

    def test_empty_approved_translation_is_critical(self):
        report = validate_release_records(
            [make_record(source='Hello', translation='', flag=FLAG_VALIDATED)],
            mode='Save as package',
            destination_locale='VI_VN',
        )

        self.assertTrue(any(issue.severity == SEVERITY_CRITICAL for issue in report.issues))
        self.assertTrue(any('empty translation' in reason for reason in self.reasons(report)))

    def test_missing_tokens_are_critical(self):
        record = make_record(
            source='{0.SimFirstName}\\n<b>Hello</b> {1.Money}',
            translation='Xin chao',
            flag=FLAG_VALIDATED,
        )

        report = validate_release_records([record], 'Finalize package', 'VI_VN')
        critical_reasons = self.reasons(report, SEVERITY_CRITICAL)

        self.assertTrue(any('{0.SimFirstName}' in reason for reason in critical_reasons))
        self.assertTrue(any('{1.Money}' in reason for reason in critical_reasons))
        self.assertTrue(any('\\n' in reason for reason in critical_reasons))
        self.assertTrue(any('<b>' in reason for reason in critical_reasons))

    def test_extra_token_and_order_mismatch_are_warnings(self):
        extra = make_record(
            idx=1,
            source='Hello {0.SimFirstName}',
            translation='Xin chao {0.SimFirstName} {1.Money}',
            flag=FLAG_TRANSLATED,
        )
        reordered = make_record(
            idx=2,
            source='{0.SimFirstName} {1.Money}',
            translation='{1.Money} {0.SimFirstName}',
            flag=FLAG_TRANSLATED,
        )

        report = validate_release_records([extra, reordered], 'Export JSON', 'VI_VN')
        warnings = self.reasons(report, SEVERITY_WARNING)

        self.assertTrue(any('Extra translation token' in reason for reason in warnings))
        self.assertTrue(any('Token order differs' in reason for reason in warnings))

    def test_soft_status_records_are_warnings_and_strict_status_records_are_critical(self):
        untranslated = make_record(idx=1, source='Hello', translation='Hello', flag=FLAG_UNVALIDATED)
        draft = make_record(idx=2, source='Draft', translation='Draft text', flag=FLAG_TRANSLATED)
        review = make_record(idx=3, source='World', translation='World text', flag=FLAG_PROGRESS)

        soft = validate_release_records(
            [untranslated, draft, review],
            'Export Everything',
            'VI_VN',
            include_untranslated=True,
            profile=PROFILE_SOFT,
        )
        strict = validate_release_records(
            [untranslated, draft, review],
            'Export Everything',
            'VI_VN',
            include_untranslated=True,
            profile=PROFILE_STRICT,
        )

        soft_status = [issue for issue in soft.issues if issue.category == 'Status']
        strict_status = [issue for issue in strict.issues if issue.category == 'Status']

        self.assertTrue(soft_status)
        self.assertTrue(all(issue.severity == SEVERITY_WARNING for issue in soft_status))
        self.assertTrue(strict_status)
        self.assertTrue(all(issue.severity == SEVERITY_CRITICAL for issue in strict_status))
        self.assertTrue(any(issue.code == 'DRAFT_INCLUDED' for issue in soft_status))

    def test_identical_approved_is_warning_in_soft_and_critical_in_strict(self):
        record = make_record(source='Same', translation='Same', flag=FLAG_VALIDATED)

        soft = validate_release_records([record], 'Save as package', 'VI_VN', profile=PROFILE_SOFT)
        strict = validate_release_records([record], 'Save as package', 'VI_VN', profile=PROFILE_STRICT)

        soft_issue = next(issue for issue in soft.issues if issue.code == 'IDENTICAL_APPROVED')
        strict_issue = next(issue for issue in strict.issues if issue.code == 'IDENTICAL_APPROVED')

        self.assertEqual(soft_issue.severity, SEVERITY_WARNING)
        self.assertEqual(strict_issue.severity, SEVERITY_CRITICAL)

    def test_duplicate_output_string_id_with_different_translation_is_critical(self):
        first = make_record(idx=1, sid=0x2A, translation='One', flag=FLAG_TRANSLATED)
        second = make_record(idx=2, sid=0x2A, translation='Hai', flag=FLAG_TRANSLATED)

        report = validate_release_records([first, second], 'Save as package', 'VI_VN')
        duplicate = next(issue for issue in report.issues if issue.code == 'DUPLICATE_OUTPUT_TEXT')

        self.assertEqual(duplicate.category, CATEGORY_DUPLICATE)
        self.assertEqual(duplicate.severity, SEVERITY_CRITICAL)
        self.assertIn('Previous: One', duplicate.reason)
        self.assertIn('Current: Hai', duplicate.reason)

    def test_untranslated_and_needs_review_included_are_warnings(self):
        untranslated = make_record(idx=1, source='Hello', translation='Hello', flag=FLAG_UNVALIDATED)
        review = make_record(idx=2, source='World', translation='World text', flag=FLAG_PROGRESS)

        report = validate_release_records(
            [untranslated, review],
            'Export Everything',
            'VI_VN',
            include_untranslated=True,
        )
        warnings = self.reasons(report, SEVERITY_WARNING)

        self.assertTrue(any('Untranslated record is included' in reason for reason in warnings))
        self.assertTrue(any('Needs review record is included' in reason for reason in warnings))

    def test_source_old_state_warns_release_reviewer(self):
        report = validate_release_records(
            [make_record(source='New source', source_old='Old source', flag=FLAG_TRANSLATED)],
            'Finalize package',
            'VI_VN',
        )

        self.assertTrue(any('changed since import' in reason for reason in self.reasons(report, SEVERITY_WARNING)))

    def test_layout_risk_warns_for_long_translation(self):
        report = validate_release_records(
            [make_record(
                source='Short enough source text',
                translation=' '.join(['translation'] * 40),
                flag=FLAG_VALIDATED,
            )],
            'Save as package',
            'VI_VN',
        )

        layout_issues = [issue for issue in report.issues if issue.category == CATEGORY_LAYOUT]
        self.assertTrue(layout_issues)
        self.assertTrue(any(issue.code == 'LONG_TRANSLATION_LAYOUT_RISK' for issue in layout_issues))
        self.assertTrue(all(issue.severity == SEVERITY_WARNING for issue in layout_issues))

    def test_layout_risk_warns_for_many_more_lines(self):
        report = validate_release_records(
            [make_record(
                source='One line',
                translation='One\\ntwo\\nthree\\nfour\\nfive',
                flag=FLAG_VALIDATED,
            )],
            'Save as package',
            'VI_VN',
        )

        self.assertTrue(any(issue.code == 'LINE_COUNT_LAYOUT_RISK' for issue in report.issues))

    def test_consistency_warns_when_same_source_has_multiple_translations(self):
        first = make_record(idx=1, sid=1, source='Hello Sim', translation='Xin chào Sim', flag=FLAG_VALIDATED)
        second = make_record(idx=2, sid=2, source='Hello  Sim', translation='Chào Sim', flag=FLAG_VALIDATED)

        report = validate_release_records([first, second], 'Save as package', 'VI_VN')
        issue = next(issue for issue in report.issues if issue.code == 'INCONSISTENT_SOURCE_TRANSLATION')

        self.assertEqual(issue.category, CATEGORY_CONSISTENCY)
        self.assertEqual(issue.severity, SEVERITY_WARNING)
        self.assertIn('2 different translations', issue.reason)

    def test_consistency_does_not_warn_when_same_source_has_same_translation(self):
        first = make_record(idx=1, sid=1, source='Hello Sim', translation='Xin chào Sim', flag=FLAG_VALIDATED)
        second = make_record(idx=2, sid=2, source='Hello  Sim', translation='Xin chào Sim', flag=FLAG_VALIDATED)

        report = validate_release_records([first, second], 'Save as package', 'VI_VN')

        self.assertFalse(any(issue.code == 'INCONSISTENT_SOURCE_TRANSLATION' for issue in report.issues))

    def test_consistency_warns_for_non_approved_unchanged_translation(self):
        report = validate_release_records(
            [make_record(source='Needs localization', translation='Needs localization', flag=FLAG_PROGRESS)],
            'Save as package',
            'VI_VN',
        )

        issue = next(issue for issue in report.issues if issue.code == 'UNCHANGED_TRANSLATION_REVIEW')
        self.assertEqual(issue.category, CATEGORY_CONSISTENCY)

    def test_consistency_allows_safe_identical_token_only_text(self):
        report = validate_release_records(
            [make_record(source='{0.SimFirstName}', translation='{0.SimFirstName}', flag=FLAG_PROGRESS)],
            'Save as package',
            'VI_VN',
        )

        self.assertFalse(any(issue.code == 'UNCHANGED_TRANSLATION_REVIEW' for issue in report.issues))

    def test_consistency_warns_for_missing_vietnamese_glossary_term(self):
        terms = terminology_terms_for_locale('VI_VN')
        self.assertIn(('Trait', 'Đặc điểm'), terms)

        report = validate_release_records(
            [make_record(
                source='This Trait helps your Sim learn faster.',
                translation='Tinh cach nay giup Sim hoc nhanh hon.',
                flag=FLAG_VALIDATED,
            )],
            'Save as package',
            'VI_VN',
        )

        issue = next(issue for issue in report.issues if issue.code == 'TERMINOLOGY_MISMATCH')
        self.assertEqual(issue.category, CATEGORY_CONSISTENCY)
        self.assertEqual(issue.severity, SEVERITY_WARNING)
        self.assertIn('Trait', issue.reason)

    def test_consistency_accepts_expected_vietnamese_glossary_term(self):
        report = validate_release_records(
            [make_record(
                source='This Trait helps your Sim learn faster.',
                translation='Đặc điểm này giúp Sim học nhanh hơn.',
                flag=FLAG_VALIDATED,
            )],
            'Save as package',
            'VI_VN',
        )

        self.assertFalse(any(issue.code == 'TERMINOLOGY_MISMATCH' for issue in report.issues))

    def test_consistency_uses_user_termbase_override(self):
        old_config_dir = os.environ.get('SIMS4_TRANSLATOR_CONFIG_DIR')
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.environ['SIMS4_TRANSLATOR_CONFIG_DIR'] = tmpdir
                termbase_dir = Path(tmpdir) / 'termbase'
                termbase_dir.mkdir()
                (termbase_dir / 'VI_VN.csv').write_text(
                    'source_term,expected_translation,note\n'
                    'Trait,tinh cach,project override\n',
                    encoding='utf-8',
                )

                report = validate_release_records(
                    [make_record(
                        source='This Trait helps your Sim learn faster.',
                        translation='tinh cach nay giup Sim hoc nhanh hon.',
                        flag=FLAG_VALIDATED,
                    )],
                    'Save as package',
                    'VI_VN',
                )
            finally:
                if old_config_dir is None:
                    os.environ.pop('SIMS4_TRANSLATOR_CONFIG_DIR', None)
                else:
                    os.environ['SIMS4_TRANSLATOR_CONFIG_DIR'] = old_config_dir

        self.assertFalse(any(issue.code == 'TERMINOLOGY_MISMATCH' for issue in report.issues))

    def test_consistency_uses_user_termbase_additions(self):
        old_config_dir = os.environ.get('SIMS4_TRANSLATOR_CONFIG_DIR')
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.environ['SIMS4_TRANSLATOR_CONFIG_DIR'] = tmpdir
                termbase_dir = Path(tmpdir) / 'termbase'
                termbase_dir.mkdir()
                (termbase_dir / 'VI_VN.csv').write_text(
                    'source_term,expected_translation,note\n'
                    'Lot,lo dat,project addition\n',
                    encoding='utf-8',
                )

                report = validate_release_records(
                    [make_record(
                        source='This Lot is huge.',
                        translation='Khu nay rat lon.',
                        flag=FLAG_VALIDATED,
                    )],
                    'Save as package',
                    'VI_VN',
                )
            finally:
                if old_config_dir is None:
                    os.environ.pop('SIMS4_TRANSLATOR_CONFIG_DIR', None)
                else:
                    os.environ['SIMS4_TRANSLATOR_CONFIG_DIR'] = old_config_dir

        issue = next(issue for issue in report.issues if issue.code == 'TERMINOLOGY_MISMATCH')
        self.assertIn('Lot', issue.reason)
        self.assertIn('lo dat', issue.reason)

    def test_consistency_ignores_glossary_terms_inside_tokens(self):
        report = validate_release_records(
            [make_record(
                source='{0.SimFirstName} found a reward.',
                translation='{0.SimFirstName} tìm thấy phần thưởng.',
                flag=FLAG_VALIDATED,
            )],
            'Save as package',
            'VI_VN',
        )

        self.assertFalse(any(issue.code == 'TERMINOLOGY_MISMATCH' for issue in report.issues))

    def test_consistency_termbase_is_locale_scoped(self):
        report = validate_release_records(
            [make_record(
                source='This Trait helps your Sim learn faster.',
                translation='Ce trait aide le Sim.',
                flag=FLAG_VALIDATED,
            )],
            'Save as package',
            'FRE_FR',
        )

        self.assertFalse(any(issue.code == 'TERMINOLOGY_MISMATCH' for issue in report.issues))

    def test_report_export_writes_text_and_csv(self):
        report = validate_release_records(
            [make_record(source='Hello {0.SimFirstName}', translation='Xin chao', flag=FLAG_VALIDATED)],
            'Manual validation',
            'VI_VN',
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            text_path = os.path.join(tmpdir, 'report.txt')
            csv_path = os.path.join(tmpdir, 'report.csv')
            md_path = os.path.join(tmpdir, 'report.md')

            report.write_text(text_path)
            report.write_csv(csv_path)
            report.write_markdown(md_path)

            with open(text_path, 'r', encoding='utf-8') as fp:
                text_content = fp.read()
            with open(csv_path, 'r', encoding='utf-8-sig') as fp:
                csv_content = fp.read()
            with open(md_path, 'r', encoding='utf-8') as fp:
                markdown_content = fp.read()

        self.assertIn('Pre-release Validation Report', text_content)
        self.assertIn('Preset: Soft release', text_content)
        self.assertIn('Missing source token', text_content)
        self.assertIn('Severity,Code,Category,Package,Instance,String ID,Status,Reason', csv_content)
        self.assertIn('MISSING_TOKEN,Token safety', csv_content)
        self.assertIn('# Pre-release Validation Report', markdown_content)
        self.assertIn('## Top Categories', markdown_content)
        self.assertIn('- Token safety: 1', markdown_content)
        self.assertIn('`MISSING_TOKEN`', markdown_content)

    def test_validation_task_reports_progress_and_returns_report(self):
        records = tuple(make_record(idx=index, sid=index, flag=FLAG_VALIDATED) for index in range(1, 5))
        request = ValidationRequest(records, 'Manual validation', 'VI_VN')
        progress = []

        class Token:
            def raise_if_cancelled(self):
                return None

        class Reporter:
            def progress(self, current=0, total=0, message=''):
                progress.append((current, total, message))

        report = validate_release_task(Token(), Reporter(), request)

        self.assertEqual(report.total_records, 4)
        self.assertTrue(any(message == 'Scanning records...' for _current, _total, message in progress))
        self.assertTrue(any(message == 'Checking tokens...' for _current, _total, message in progress))
        self.assertTrue(any(message == 'Building report...' for _current, _total, message in progress))

    def test_validation_task_respects_cancellation(self):
        records = tuple(make_record(idx=index, sid=index, flag=FLAG_VALIDATED) for index in range(1, 5))
        request = ValidationRequest(records, 'Manual validation', 'VI_VN')

        class Token:
            def raise_if_cancelled(self):
                raise CancelledTask()

        class Reporter:
            def progress(self, current=0, total=0, message=''):
                return None

        with self.assertRaises(CancelledTask):
            validate_release_task(Token(), Reporter(), request)


if __name__ == '__main__':
    unittest.main()
