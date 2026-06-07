# -*- coding: utf-8 -*-

import csv
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

from packer.resource import ResourceID
from singletons.config import ConfigManager
from singletons.translation_memory import normalize_source
from storages.records import MainRecord
from utils.constants import (
    FLAG_PROGRESS,
    FLAG_REPLACED,
    FLAG_TRANSLATED,
    FLAG_UNVALIDATED,
    FLAG_VALIDATED,
)
from utils.functions import compare, fnv64, text_to_edit, text_to_table, text_to_stbl
from utils.runtime_paths import resource_path
from widgets.token_highlight import validate_translation_tokens


SEVERITY_CRITICAL = 'Critical'
SEVERITY_WARNING = 'Warning'
SEVERITY_INFO = 'Info'

CATEGORY_BLANK = 'Blank risk'
CATEGORY_TOKEN = 'Token safety'
CATEGORY_STATUS = 'Status'
CATEGORY_DUPLICATE = 'Duplicate output'
CATEGORY_RESOURCE = 'Resource'
CATEGORY_SOURCE_CHANGED = 'Source changed'
CATEGORY_SUMMARY = 'Summary'
CATEGORY_LAYOUT = 'Length / layout risk'
CATEGORY_CONSISTENCY = 'Consistency'

VALIDATION_CATEGORIES = (
    CATEGORY_BLANK,
    CATEGORY_TOKEN,
    CATEGORY_STATUS,
    CATEGORY_DUPLICATE,
    CATEGORY_RESOURCE,
    CATEGORY_SOURCE_CHANGED,
    CATEGORY_LAYOUT,
    CATEGORY_CONSISTENCY,
    CATEGORY_SUMMARY,
)


STATUS_LABELS = {
    FLAG_UNVALIDATED: 'Untranslated',
    FLAG_PROGRESS: 'Needs review',
    FLAG_VALIDATED: 'Approved',
    FLAG_TRANSLATED: 'Draft',
    FLAG_REPLACED: 'Edited',
}


DEFAULT_TERMINOLOGY_TERMS = {
    'VI_VN': (
        ('Sim', 'Sim', 'Keep The Sims character noun as the franchise term.'),
        ('Moodlet', 'moodlet', 'Common Sims UI term.'),
        ('Aspiration', 'Khát vọng', 'Vietnamese release term.'),
        ('Trait', 'Đặc điểm', 'Vietnamese release term.'),
        ('Household', 'Hộ gia đình', 'Vietnamese release term.'),
    ),
}


@dataclass(frozen=True)
class ValidationProfile:
    name: str
    strict_status: bool = False
    identical_original_severity: str = SEVERITY_WARNING


PROFILE_SOFT = ValidationProfile('Soft release')
PROFILE_STRICT = ValidationProfile(
    'Strict release',
    strict_status=True,
    identical_original_severity=SEVERITY_CRITICAL,
)

VALIDATION_PROFILES = (PROFILE_SOFT, PROFILE_STRICT)


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    package: str
    instance: str
    string_id: str
    status: str
    reason: str
    original: str = ''
    translation: str = ''
    record: MainRecord = None
    code: str = ''
    category: str = ''


@dataclass(frozen=True)
class ValidationRequest:
    items: Tuple[MainRecord, ...]
    mode: str
    destination_locale: str
    include_untranslated: bool = True
    conflict_free: bool = False
    profile: ValidationProfile = PROFILE_SOFT


@dataclass(frozen=True)
class ValidationReport:
    mode: str
    profile: ValidationProfile
    destination_locale: str
    include_untranslated: bool
    conflict_free: bool
    total_records: int
    written_records: int
    package_count: int
    resource_count: int
    status_counts: Tuple[Tuple[str, int], ...]
    issues: Tuple[ValidationIssue, ...]

    @property
    def critical_count(self) -> int:
        return self.count(SEVERITY_CRITICAL)

    @property
    def warning_count(self) -> int:
        return self.count(SEVERITY_WARNING)

    @property
    def info_count(self) -> int:
        return self.count(SEVERITY_INFO)

    def count(self, severity: str) -> int:
        return sum(1 for issue in self.issues if issue.severity == severity)

    def summary(self) -> str:
        return (
            f'Pre-release validation ({self.profile.name}): {self.critical_count} critical, '
            f'{self.warning_count} warning, {self.info_count} info '
            f'for {self.written_records:,}/{self.total_records:,} record(s).'
        )

    def filtered(self, severity: str = None, category: str = None, query: str = '') -> Tuple[ValidationIssue, ...]:
        query = (query or '').strip().lower()
        issues = self.issues
        if severity and severity != 'All':
            issues = tuple(issue for issue in issues if issue.severity == severity)
        if category and category != 'All':
            issues = tuple(issue for issue in issues if issue.category == category)
        if query:
            issues = tuple(issue for issue in issues if query in _issue_search_text(issue))
        return tuple(issues)

    def to_text(self) -> str:
        lines = [
            'Pre-release Validation Report',
            self.summary(),
            f'Mode: {self.mode}',
            f'Preset: {self.profile.name}',
            f'Destination: {self.destination_locale}',
            f'Conflict-free save mode: {"on" if self.conflict_free else "off"}',
            f'Packages: {self.package_count:,}',
            f'STBL resources: {self.resource_count:,}',
            '',
            'Status counts:',
        ]
        for status, count in self.status_counts:
            lines.append(f'  {status}: {count:,}')
        lines.extend(('', 'Issues:'))
        for issue in self.issues:
            lines.append(
                '\t'.join((
                    issue.severity,
                    issue.code,
                    issue.category,
                    issue.package,
                    issue.instance,
                    issue.string_id,
                    issue.status,
                    issue.reason,
                    text_to_table(issue.original),
                    text_to_table(issue.translation),
                ))
            )
        return '\n'.join(lines)

    def to_markdown_summary(self) -> str:
        severity_counts = Counter(issue.severity for issue in self.issues)
        category_counts = Counter(issue.category or 'Uncategorized' for issue in self.issues)
        code_counts = Counter(issue.code or 'UNCATEGORIZED' for issue in self.issues)
        lines = [
            '# Pre-release Validation Report',
            '',
            self.summary(),
            '',
            '## Overview',
            '',
            f'- Mode: {_markdown_text(self.mode)}',
            f'- Preset: {_markdown_text(self.profile.name)}',
            f'- Destination: `{_markdown_text(self.destination_locale)}`',
            f'- Records: {self.written_records:,}/{self.total_records:,}',
            f'- Packages: {self.package_count:,}',
            f'- STBL resources: {self.resource_count:,}',
            f'- Conflict-free save mode: {"on" if self.conflict_free else "off"}',
            '',
            '## Issue Counts',
            '',
            f'- Critical: {severity_counts.get(SEVERITY_CRITICAL, 0):,}',
            f'- Warning: {severity_counts.get(SEVERITY_WARNING, 0):,}',
            f'- Info: {severity_counts.get(SEVERITY_INFO, 0):,}',
            '',
            '## Top Categories',
            '',
        ]

        if category_counts:
            for category, count in category_counts.most_common(8):
                lines.append(f'- {_markdown_text(category)}: {count:,}')
        else:
            lines.append('- No issues.')

        lines.extend(('', '## Status Counts', ''))
        if self.status_counts:
            for status, count in self.status_counts:
                lines.append(f'- {_markdown_text(status)}: {count:,}')
        else:
            lines.append('- No status counts.')

        lines.extend(('', '## Top Issue Codes', ''))
        if code_counts:
            for code, count in code_counts.most_common(8):
                lines.append(f'- `{_markdown_text(code)}`: {count:,}')
        else:
            lines.append('- No issue codes.')

        lines.extend(('', '## Sample Issues', ''))
        sample_issues = [issue for issue in self.issues if issue.category != CATEGORY_SUMMARY][:10]
        if not sample_issues:
            lines.append('- No actionable issues.')
        for issue in sample_issues:
            location = ' / '.join(part for part in (issue.package, issue.instance, issue.string_id) if part and part != '-')
            if location:
                location = f' ({_markdown_text(location)})'
            lines.append(
                f'- **{_markdown_text(issue.severity)}** `{_markdown_text(issue.code or "-")}` '
                f'{_markdown_text(issue.category or "-")}{location}: {_markdown_text(issue.reason)}'
            )
        return '\n'.join(lines)

    def write_text(self, path: str) -> None:
        with open(path, 'w', encoding='utf-8') as fp:
            fp.write(self.to_text())

    def write_markdown(self, path: str) -> None:
        with open(path, 'w', encoding='utf-8') as fp:
            fp.write(self.to_markdown_summary())

    def write_csv(self, path: str) -> None:
        with open(path, 'w', encoding='utf-8-sig', newline='') as fp:
            writer = csv.writer(fp)
            writer.writerow(('Severity', 'Code', 'Category', 'Package', 'Instance', 'String ID', 'Status', 'Reason',
                             'Original', 'Translation'))
            for issue in self.issues:
                writer.writerow((
                    issue.severity,
                    issue.code,
                    issue.category,
                    issue.package,
                    issue.instance,
                    issue.string_id,
                    issue.status,
                    issue.reason,
                    text_to_table(issue.original),
                    text_to_table(issue.translation),
                ))


def validate_release_records(
        items: Iterable[MainRecord],
        mode: str,
        destination_locale: str,
        include_untranslated: bool = True,
        conflict_free: bool = False,
        profile: ValidationProfile = PROFILE_SOFT,
) -> ValidationReport:
    return _validate_release_records(
        items,
        mode,
        destination_locale,
        include_untranslated,
        conflict_free,
        profile,
    )


def validate_release_task(token, reporter, request: ValidationRequest) -> ValidationReport:
    return _validate_release_records(
        request.items,
        request.mode,
        request.destination_locale,
        request.include_untranslated,
        request.conflict_free,
        request.profile,
        token=token,
        reporter=reporter,
    )


def terminology_terms_for_locale(destination_locale: str) -> Tuple[Tuple[str, str], ...]:
    locale = (destination_locale or '').upper()
    terms: dict[str, Tuple[str, str]] = {}

    for source_term, expected_translation, _note in DEFAULT_TERMINOLOGY_TERMS.get(locale, ()):
        terms[source_term.lower()] = (source_term, expected_translation)

    for path in _terminology_paths(locale):
        for source_term, expected_translation in _read_terminology_file(path):
            terms[source_term.lower()] = (source_term, expected_translation)

    return tuple(terms.values())


def _terminology_paths(locale: str) -> Tuple[Path, ...]:
    if not locale:
        return ()
    filename = f'{locale}.csv'
    return (
        resource_path('prefs', 'termbase', filename),
        ConfigManager.default_config_dir() / 'termbase' / filename,
    )


def _read_terminology_file(path: Path) -> Tuple[Tuple[str, str], ...]:
    try:
        with open(path, 'r', encoding='utf-8-sig', newline='') as fp:
            rows = csv.DictReader(fp)
            terms = []
            for row in rows:
                source_term = (row.get('source_term') or '').strip()
                expected_translation = (row.get('expected_translation') or '').strip()
                if source_term and expected_translation:
                    terms.append((source_term, expected_translation))
            return tuple(terms)
    except FileNotFoundError:
        return ()


def _validate_release_records(
        items: Iterable[MainRecord],
        mode: str,
        destination_locale: str,
        include_untranslated: bool = True,
        conflict_free: bool = False,
        profile: ValidationProfile = PROFILE_SOFT,
        token=None,
        reporter=None,
) -> ValidationReport:
    profile = validation_profile(profile)
    source_items = tuple(items or ())
    if token:
        token.raise_if_cancelled()
    if reporter:
        reporter.progress(0, len(source_items), 'Scanning records...')
    written = tuple(_written_items(source_items, include_untranslated, conflict_free))
    issues = []
    resources = {}
    output_texts = {}
    status_counter = Counter(STATUS_LABELS.get(item.flag, 'Unknown') for item in source_items)
    progress_step = max(1000, len(written) // 100 or 1)

    for index, item in enumerate(written, start=1):
        if token and (index == 1 or index % progress_step == 0):
            token.raise_if_cancelled()
        rid = _output_resource(item, destination_locale, conflict_free)
        if rid is None:
            issues.append(_issue(
                SEVERITY_CRITICAL,
                item,
                'Output resource cannot be converted to destination locale.',
                code='RESOURCE_CONVERSION_FAILED',
                category=CATEGORY_RESOURCE,
            ))
            continue

        resources[rid] = True
        output_key = (rid, item.id)
        translated_text = text_to_stbl(item.translate)
        previous = output_texts.get(output_key)
        if previous is not None and previous != translated_text:
            issues.append(_issue(
                SEVERITY_CRITICAL,
                item,
                'Duplicate output resource/string ID has different translated text. '
                f'Previous: {text_to_table(previous)} | Current: {text_to_table(translated_text)}',
                rid=rid,
                code='DUPLICATE_OUTPUT_TEXT',
                category=CATEGORY_DUPLICATE,
            ))
        else:
            output_texts[output_key] = translated_text

        issues.extend(_record_issues(item, include_untranslated, rid, profile))
        if reporter and (index == len(written) or index % progress_step == 0):
            reporter.progress(index, len(written), 'Checking tokens...')

    if token:
        token.raise_if_cancelled()
    if reporter:
        reporter.progress(len(written), len(written), 'Building report...')

    issues.extend(_consistency_issues(written, destination_locale))

    issues.append(ValidationIssue(
        SEVERITY_INFO,
        '-',
        '-',
        '-',
        '-',
        (
            f'{len(written):,}/{len(source_items):,} record(s), {len(resources):,} STBL resource(s), '
            f'{len({item.package for item in written if item.package}):,} package(s), '
            f'destination {destination_locale}, preset {profile.name}.'
        ),
        code='SUMMARY',
        category=CATEGORY_SUMMARY,
    ))

    return ValidationReport(
        mode=mode,
        profile=profile,
        destination_locale=destination_locale,
        include_untranslated=include_untranslated,
        conflict_free=conflict_free,
        total_records=len(source_items),
        written_records=len(written),
        package_count=len({item.package for item in written if item.package}),
        resource_count=len(resources),
        status_counts=tuple((label, status_counter.get(label, 0)) for label in (
            'Approved',
            'Draft',
            'Needs review',
            'Edited',
            'Untranslated',
        )),
        issues=tuple(issues),
    )


def validation_profile(profile) -> ValidationProfile:
    if isinstance(profile, ValidationProfile):
        return profile
    for candidate in VALIDATION_PROFILES:
        if candidate.name == profile:
            return candidate
    return PROFILE_SOFT


def _written_items(items: Tuple[MainRecord, ...], include_untranslated: bool, conflict_free: bool):
    for item in items:
        if item.flag == FLAG_UNVALIDATED and (not include_untranslated or conflict_free):
            continue
        yield item


def _output_resource(item: MainRecord, destination_locale: str, conflict_free: bool):
    try:
        rid = item.resource
        if conflict_free:
            rid = ResourceID(
                group=rid.group,
                type=rid.type,
                instance=fnv64('translator:' + os.path.abspath('.') + rid.str_instance)
            )
        return rid.convert_instance(destination_locale)
    except Exception:
        return None


def _record_issues(item: MainRecord, include_untranslated: bool, rid=None, profile: ValidationProfile = PROFILE_SOFT) -> list:
    issues = []
    source = text_to_stbl(item.source)
    translation = text_to_stbl(item.translate)

    if item.flag in (FLAG_PROGRESS, FLAG_TRANSLATED, FLAG_VALIDATED, FLAG_REPLACED) \
            and source.strip() and not translation.strip():
        issues.append(_issue(
            SEVERITY_CRITICAL,
            item,
            'Release record has an empty translation.',
            rid=rid,
            code='EMPTY_TRANSLATION',
            category=CATEGORY_BLANK,
        ))

    if item.flag == FLAG_VALIDATED and source.strip() and compare(source, translation):
        issues.append(_issue(
            profile.identical_original_severity,
            item,
            'Approved translation is identical to the original text.',
            rid=rid,
            code='IDENTICAL_APPROVED',
            category=CATEGORY_BLANK,
        ))

    token_result = validate_translation_tokens(source, translation)
    if token_result.missing:
        issues.append(_issue(
            SEVERITY_CRITICAL,
            item,
            'Missing source token(s): ' + ', '.join(token_result.missing),
            rid=rid,
            code='MISSING_TOKEN',
            category=CATEGORY_TOKEN,
        ))
    if token_result.extra:
        issues.append(_issue(
            SEVERITY_WARNING,
            item,
            'Extra translation token(s): ' + ', '.join(token_result.extra),
            rid=rid,
            code='EXTRA_TOKEN',
            category=CATEGORY_TOKEN,
        ))
    if token_result.order_mismatch:
        issues.append(_issue(
            SEVERITY_WARNING,
            item,
            'Token order differs from the original text.',
            rid=rid,
            code='TOKEN_ORDER_MISMATCH',
            category=CATEGORY_TOKEN,
        ))
    if token_result.linebreak_mismatch and not _has_linebreak_token(token_result.missing + token_result.extra):
        issues.append(_issue(
            SEVERITY_WARNING,
            item,
            'Line-break count differs from the original text.',
            rid=rid,
            code='LINEBREAK_COUNT_MISMATCH',
            category=CATEGORY_TOKEN,
        ))

    issues.extend(_layout_issues(item, source, translation, rid))

    status_severity = SEVERITY_CRITICAL if profile.strict_status else SEVERITY_WARNING
    if item.flag == FLAG_PROGRESS:
        issues.append(_issue(
            status_severity,
            item,
            'Needs review record is included in release output.',
            rid=rid,
            code='NEEDS_REVIEW_INCLUDED',
            category=CATEGORY_STATUS,
        ))
    if item.flag == FLAG_TRANSLATED:
        issues.append(_issue(
            status_severity,
            item,
            'Draft record is included in release output.',
            rid=rid,
            code='DRAFT_INCLUDED',
            category=CATEGORY_STATUS,
        ))
    if item.flag == FLAG_UNVALIDATED and include_untranslated:
        issues.append(_issue(
            status_severity,
            item,
            'Untranslated record is included in release output.',
            rid=rid,
            code='UNTRANSLATED_INCLUDED',
            category=CATEGORY_STATUS,
        ))
    if item.source_old:
        issues.append(_issue(
            SEVERITY_WARNING,
            item,
            'Original text changed since import/dictionary match.',
            rid=rid,
            code='SOURCE_CHANGED',
            category=CATEGORY_SOURCE_CHANGED,
        ))

    return issues


def _consistency_issues(items: Tuple[MainRecord, ...], destination_locale: str) -> list:
    issues = []
    source_groups = {}
    terminology_terms = terminology_terms_for_locale(destination_locale)

    for item in items:
        source = text_to_stbl(item.source)
        translation = text_to_stbl(item.translate)
        normalized_source = normalize_source(source)
        normalized_translation = normalize_source(translation)
        if not normalized_source or not normalized_translation:
            continue

        if item.flag in (FLAG_PROGRESS, FLAG_TRANSLATED, FLAG_REPLACED) \
                and compare(source, translation) and not _safe_identical_translation(source):
            issues.append(_issue(
                SEVERITY_WARNING,
                item,
                'Translation is still identical to the original; review whether this should be localized.',
                code='UNCHANGED_TRANSLATION_REVIEW',
                category=CATEGORY_CONSISTENCY,
            ))

        source_groups.setdefault(normalized_source, []).append((item, normalized_translation, translation))
        if terminology_terms:
            issues.extend(_terminology_issues(item, source, translation, terminology_terms))

    for group in source_groups.values():
        translations = {}
        for item, normalized_translation, translation in group:
            translations.setdefault(normalized_translation, (item, translation))
        if len(translations) <= 1:
            continue

        representative = group[0][0]
        examples = []
        for _normalized, (_item, translation) in list(translations.items())[:3]:
            examples.append(text_to_table(translation)[:96])
        issues.append(_issue(
            SEVERITY_WARNING,
            representative,
            f'Same source text has {len(translations)} different translations; review consistency. '
            'Examples: ' + ' | '.join(examples),
            code='INCONSISTENT_SOURCE_TRANSLATION',
            category=CATEGORY_CONSISTENCY,
        ))

    return issues


def _terminology_issues(
        item: MainRecord,
        source: str,
        translation: str,
        terminology_terms: tuple,
) -> list:
    if not translation.strip():
        return []

    issues = []
    source_text = _localizable_term_text(source)
    translation_text = _localizable_term_text(translation)
    if not source_text or not translation_text:
        return []

    for source_term, expected_translation in terminology_terms:
        if not _contains_term(source_text, source_term):
            continue
        if _contains_term(translation_text, expected_translation):
            continue
        issues.append(_issue(
            SEVERITY_WARNING,
            item,
            f'Glossary term "{source_term}" should usually be translated as "{expected_translation}" '
            'for Vietnamese release consistency.',
            code='TERMINOLOGY_MISMATCH',
            category=CATEGORY_CONSISTENCY,
        ))
    return issues


def _safe_identical_translation(source: str) -> bool:
    text = text_to_edit(source)
    text = re.sub(r'\{[^{}]+\}|<[^>]+>|\\n|%[A-Za-z]', '', text)
    text = text.strip()
    return not text or not re.search(r'[A-Za-zÀ-ỹ]', text)


def _localizable_term_text(text: str) -> str:
    text = text_to_edit(text)
    text = re.sub(r'\{[^{}]+\}|<[^>]+>|\\n|%[A-Za-z]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _contains_term(text: str, term: str) -> bool:
    if not text or not term:
        return False
    pattern = r'(?<![\w])' + re.escape(term) + r'(?![\w])'
    return re.search(pattern, text, re.IGNORECASE) is not None


def _issue(
        severity: str,
        item: MainRecord,
        reason: str,
        rid=None,
        code: str = '',
        category: str = '',
) -> ValidationIssue:
    display_rid = rid or item.resource
    return ValidationIssue(
        severity=severity,
        package=item.package or '-',
        instance=_resource_instance_hex(display_rid, item),
        string_id=item.id_hex,
        status=STATUS_LABELS.get(item.flag, 'Unknown'),
        reason=reason,
        original=item.source or '',
        translation=item.translate or '',
        record=item,
        code=code,
        category=category,
    )


def _layout_issues(item: MainRecord, source: str, translation: str, rid=None) -> list:
    source_display = text_to_edit(source)
    translation_display = text_to_edit(translation)
    if not translation_display.strip():
        return []

    issues = []
    source_len = len(source_display)
    translation_len = len(translation_display)
    if source_len >= 20 and translation_len > max(int(source_len * 1.8), source_len + 80):
        issues.append(_issue(
            SEVERITY_WARNING,
            item,
            'Translation is much longer than the original text; review possible UI overflow.',
            rid=rid,
            code='LONG_TRANSLATION_LAYOUT_RISK',
            category=CATEGORY_LAYOUT,
        ))

    source_lines = _visual_lines(source_display)
    translation_lines = _visual_lines(translation_display)
    if len(translation_lines) >= max(len(source_lines) + 3, len(source_lines) * 2 + 1):
        issues.append(_issue(
            SEVERITY_WARNING,
            item,
            'Translation uses many more visual lines than the original text; review possible UI overflow.',
            rid=rid,
            code='LINE_COUNT_LAYOUT_RISK',
            category=CATEGORY_LAYOUT,
        ))

    source_max = max((len(line) for line in source_lines), default=0)
    translation_max = max((len(line) for line in translation_lines), default=0)
    if translation_max > max(160, int(source_max * 1.75)):
        issues.append(_issue(
            SEVERITY_WARNING,
            item,
            'Translation has a very long line; review possible UI overflow.',
            rid=rid,
            code='LONG_LINE_LAYOUT_RISK',
            category=CATEGORY_LAYOUT,
        ))

    return issues


def _visual_lines(text: str) -> list[str]:
    return text.replace('\r', '').split('\n') if text else ['']


def _resource_instance_hex(rid, item: MainRecord) -> str:
    if hasattr(rid, 'hex_instance'):
        return rid.hex_instance
    if hasattr(rid, 'instance_hex'):
        return rid.instance_hex
    return item.instance_hex


def _has_linebreak_token(tokens) -> bool:
    return any(str(token).startswith('\\n') for token in tokens)


def _issue_search_text(issue: ValidationIssue) -> str:
    return ' '.join((
        issue.severity,
        issue.code,
        issue.category,
        issue.package,
        issue.instance,
        issue.string_id,
        issue.status,
        issue.reason,
        text_to_table(issue.original),
        text_to_table(issue.translation),
    )).lower()


def _markdown_text(value: object) -> str:
    text = text_to_table(str(value or ''))
    return text.replace('\\', '\\\\').replace('|', '\\|')
