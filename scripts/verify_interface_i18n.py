# -*- coding: utf-8 -*-

import argparse
import re
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER_PATTERN = re.compile(r'\{[^{}]+\}')


def _load_catalog(path: Path) -> tuple[str, dict[tuple[str, str], str]]:
    root = ElementTree.parse(path).getroot()
    catalog = {}
    for context in root.findall('context'):
        context_name = context.get('name') or ''
        for item in context.findall('string'):
            source = item.findtext('source') or ''
            translation = item.findtext('translation') or ''
            catalog[(context_name, source)] = translation
    return root.get('version') or '', catalog


def _placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER_PATTERN.findall(text or ''))


def verify(language: str, version: str = '', strict_empty: bool = False, strict_missing: bool = False) -> list[str]:
    source_path = ROOT / 'prefs' / 'interface' / 'english.xml'
    aliases = {
        'en_US': 'english',
        'vi_VN': 'vietnamese',
    }
    target_name = aliases.get(language, language)
    target_path = ROOT / 'prefs' / 'interface' / f'{target_name}.xml'
    if not target_path.exists():
        return [f'Interface file not found: {target_path.relative_to(ROOT)}']

    _source_version, source_catalog = _load_catalog(source_path)
    target_version, target_catalog = _load_catalog(target_path)
    errors = []

    if version and target_version != version:
        errors.append(f'{target_path.relative_to(ROOT)} version is {target_version!r}, expected {version!r}')

    missing = sorted(set(source_catalog) - set(target_catalog))
    if strict_missing and missing:
        errors.append(f'{target_path.relative_to(ROOT)} is missing {len(missing)} source string(s)')

    empty = [
        key for key in source_catalog
        if key in target_catalog and not target_catalog[key].strip()
    ]
    if strict_empty and empty:
        errors.append(f'{target_path.relative_to(ROOT)} has {len(empty)} empty translation(s)')

    placeholder_errors = []
    for key in sorted(set(source_catalog) & set(target_catalog)):
        translation = target_catalog[key]
        if not translation.strip():
            continue
        source_tokens = _placeholders(key[1])
        translation_tokens = _placeholders(translation)
        if source_tokens != translation_tokens:
            placeholder_errors.append((key, source_tokens, translation_tokens))
    if placeholder_errors:
        examples = []
        for key, source_tokens, translation_tokens in placeholder_errors[:5]:
            examples.append(
                f'{key[0]}::{key[1]!r} source={sorted(source_tokens)} translation={sorted(translation_tokens)}'
            )
        errors.append(
            f'{target_path.relative_to(ROOT)} has {len(placeholder_errors)} placeholder mismatch(es): '
            + '; '.join(examples)
        )

    available = len(set(source_catalog) & set(target_catalog))
    translated = available - len(empty)
    coverage = (translated / len(source_catalog) * 100) if source_catalog else 0
    print(
        f'{language}: {translated}/{len(source_catalog)} translated '
        f'({coverage:.1f}%), missing={len(missing)}, empty={len(empty)}'
    )
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Check interface XML localization health.')
    parser.add_argument('--language', default='vietnamese', help='Interface file stem, e.g. vietnamese or english.')
    parser.add_argument('--version', default='', help='Expected interface XML version.')
    parser.add_argument('--strict-empty', action='store_true', help='Fail on empty translations.')
    parser.add_argument('--strict-missing', action='store_true', help='Fail on missing source strings.')
    args = parser.parse_args(argv)

    errors = verify(args.language, args.version, args.strict_empty, args.strict_missing)
    if errors:
        print('Interface localization verification failed:')
        for error in errors:
            print(f'  - {error}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
