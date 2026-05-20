# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from packer.resource import ResourceID
from storages.records import MainRecord
from utils.constants import (
    FLAG_PROGRESS,
    FLAG_TRANSLATED,
    FLAG_UNVALIDATED,
    FLAG_VALIDATED,
)
from utils.release_validation import (
    CATEGORY_DUPLICATE,
    PROFILE_SOFT,
    PROFILE_STRICT,
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
    validate_release_records,
)


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

    def test_report_export_writes_text_and_csv(self):
        report = validate_release_records(
            [make_record(source='Hello {0.SimFirstName}', translation='Xin chao', flag=FLAG_VALIDATED)],
            'Manual validation',
            'VI_VN',
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            text_path = os.path.join(tmpdir, 'report.txt')
            csv_path = os.path.join(tmpdir, 'report.csv')

            report.write_text(text_path)
            report.write_csv(csv_path)

            with open(text_path, 'r', encoding='utf-8') as fp:
                text_content = fp.read()
            with open(csv_path, 'r', encoding='utf-8-sig') as fp:
                csv_content = fp.read()

        self.assertIn('Pre-release Validation Report', text_content)
        self.assertIn('Preset: Soft release', text_content)
        self.assertIn('Missing source token', text_content)
        self.assertIn('Severity,Code,Category,Package,Instance,String ID,Status,Reason', csv_content)
        self.assertIn('MISSING_TOKEN,Token safety', csv_content)


if __name__ == '__main__':
    unittest.main()
