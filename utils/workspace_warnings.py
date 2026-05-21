# -*- coding: utf-8 -*-

from collections import Counter
from typing import Iterable

from storages.records import MainRecord
from utils.constants import (
    FLAG_PROGRESS,
    FLAG_REPLACED,
    FLAG_TRANSLATED,
    FLAG_UNVALIDATED,
    FLAG_VALIDATED,
)
from utils.functions import text_to_table
from utils.release_validation import (
    CATEGORY_BLANK,
    CATEGORY_DUPLICATE,
    CATEGORY_SOURCE_CHANGED,
    CATEGORY_STATUS,
    CATEGORY_SUMMARY,
    CATEGORY_TOKEN,
    PROFILE_SOFT,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    STATUS_LABELS,
    ValidationIssue,
    ValidationReport,
)
from widgets.token_highlight import validate_translation_tokens


def workspace_warnings_report(
        items: Iterable[MainRecord],
        destination_locale: str,
        max_repeated_infos: int = 200,
) -> ValidationReport:
    records = tuple(items or ())
    issues = []
    output_texts = {}
    resources = {}
    status_counter = Counter(STATUS_LABELS.get(item.flag, 'Unknown') for item in records)

    for item in records:
        if item.resource:
            resources[item.resource] = True

        if item.flag in (FLAG_VALIDATED, FLAG_TRANSLATED, FLAG_PROGRESS, FLAG_REPLACED):
            if item.source and not (item.translate or '').strip():
                issues.append(_issue(
                    SEVERITY_CRITICAL,
                    item,
                    'Translated record has an empty translation.',
                    'WORKSPACE_EMPTY_TRANSLATION',
                    CATEGORY_BLANK,
                ))

        token_result = validate_translation_tokens(item.source, item.translate)
        if not token_result.ok:
            issues.append(_issue(
                SEVERITY_WARNING,
                item,
                token_result.details(),
                'WORKSPACE_TOKEN_MISMATCH',
                CATEGORY_TOKEN,
            ))

        if item.source_old or item.translate_old:
            issues.append(_issue(
                SEVERITY_INFO,
                item,
                'Source or translation has a previous value and may need review.',
                'WORKSPACE_MODIFIED_RECORD',
                CATEGORY_SOURCE_CHANGED,
            ))

        try:
            output_resource = item.resource.convert_instance(destination_locale)
        except (AttributeError, ValueError):
            output_resource = item.resource

        output_key = (output_resource, item.id)
        previous = output_texts.get(output_key)
        if previous is not None and previous != item.translate:
            issues.append(_issue(
                SEVERITY_CRITICAL,
                item,
                'Duplicate output resource/string ID has different translated text. '
                f'Previous: {text_to_table(previous)} | Current: {text_to_table(item.translate)}',
                'WORKSPACE_DUPLICATE_OUTPUT_TEXT',
                CATEGORY_DUPLICATE,
            ))
        output_texts.setdefault(output_key, item.translate)

    repeated_texts = Counter(item.translate for item in records if item.translate)
    repeated_count = 0
    for item in records:
        if repeated_count >= max_repeated_infos:
            break
        if item.translate and repeated_texts[item.translate] > 1:
            issues.append(_issue(
                SEVERITY_INFO,
                item,
                f'Repeated translation text appears {repeated_texts[item.translate]:,} times.',
                'WORKSPACE_REPEATED_TRANSLATION',
                CATEGORY_SUMMARY,
            ))
            repeated_count += 1

    if not issues:
        issues.append(ValidationIssue(
            SEVERITY_INFO,
            '-',
            '-',
            '-',
            '-',
            'No workspace warnings found.',
            code='WORKSPACE_NO_WARNINGS',
            category=CATEGORY_SUMMARY,
        ))

    return ValidationReport(
        mode='Workspace Warnings',
        profile=PROFILE_SOFT,
        destination_locale=destination_locale,
        include_untranslated=True,
        conflict_free=False,
        total_records=len(records),
        written_records=len(records),
        package_count=len({item.package for item in records if item.package}),
        resource_count=len(resources),
        status_counts=tuple((label, status_counter.get(label, 0)) for label in (
            'Untranslated',
            'Draft',
            'Approved',
            'Needs review',
            'Edited',
        )),
        issues=tuple(issues),
    )


def _issue(severity: str, item: MainRecord, reason: str, code: str, category: str) -> ValidationIssue:
    return ValidationIssue(
        severity,
        item.package or '-',
        item.instance_hex,
        item.id_hex,
        STATUS_LABELS.get(item.flag, 'Unknown'),
        reason,
        item.source,
        item.translate,
        item,
        code,
        category,
    )
