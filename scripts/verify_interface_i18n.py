# -*- coding: utf-8 -*-

import argparse
import ast
import re
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER_PATTERN = re.compile(r'\{[^{}]*\}')
INTERFACE_DIR = ROOT / 'prefs' / 'interface'
CODE_ROOTS = ('windows', 'widgets', 'singletons', 'utils', 'models', 'storages')
DYNAMIC_INTERFACE_SOURCES = {
    ('ReleaseValidationDialog', 'Severity'),
    ('ReleaseValidationDialog', 'Code'),
    ('ReleaseValidationDialog', 'Category'),
    ('ReleaseValidationDialog', 'Package'),
    ('ReleaseValidationDialog', 'Instance'),
    ('ReleaseValidationDialog', 'String ID'),
    ('ReleaseValidationDialog', 'Status'),
    ('ReleaseValidationDialog', 'Reason'),
    ('ReleaseValidationDialog', 'Original'),
    ('ReleaseValidationDialog', 'Translation'),
    ('ValidationSeverity', 'Critical'),
    ('ValidationSeverity', 'Warning'),
    ('ValidationSeverity', 'Info'),
    ('ValidationCategory', 'Blank risk'),
    ('ValidationCategory', 'Token safety'),
    ('ValidationCategory', 'Status'),
    ('ValidationCategory', 'Duplicate output'),
    ('ValidationCategory', 'Resource'),
    ('ValidationCategory', 'Source changed'),
    ('ValidationCategory', 'Length / layout risk'),
    ('ValidationCategory', 'Summary'),
    ('ValidationProfile', 'Soft release'),
    ('ValidationProfile', 'Strict release'),
}


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


def _interface_files() -> list[Path]:
    return sorted(INTERFACE_DIR.glob('*.xml'))


def _language_aliases() -> dict[str, str]:
    aliases = {
        'en_US': 'english',
        'vi_VN': 'vietnamese',
        'english': 'english',
        'vietnamese': 'vietnamese',
    }
    for path in _interface_files():
        try:
            root = ElementTree.parse(path).getroot()
        except ElementTree.ParseError:
            continue
        aliases[path.stem] = path.stem
        language = root.get('language')
        if language:
            aliases[language] = path.stem
    return aliases


def _target_path(language: str) -> Path:
    target_name = _language_aliases().get(language, language)
    return INTERFACE_DIR / f'{target_name}.xml'


def _placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER_PATTERN.findall(text or ''))


def _used_interface_literals() -> set[tuple[str, str]]:
    used = set(DYNAMIC_INTERFACE_SOURCES)
    for root_name in CODE_ROOTS:
        root = ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or len(node.args) < 2:
                    continue
                func = node.func
                is_interface_text = (
                    isinstance(func, ast.Attribute)
                    and func.attr == 'text'
                    and isinstance(func.value, ast.Name)
                    and func.value.id == 'interface'
                )
                is_display_text = isinstance(func, ast.Name) and func.id == '_display_text'
                if not (is_interface_text or is_display_text):
                    continue
                try:
                    context_name = ast.literal_eval(node.args[0])
                    source = ast.literal_eval(node.args[1])
                except (ValueError, SyntaxError):
                    continue
                if isinstance(context_name, str) and isinstance(source, str):
                    used.add((context_name, source))
    return used


def verify_source_catalog() -> list[str]:
    source_path = INTERFACE_DIR / 'english.xml'
    _source_version, source_catalog = _load_catalog(source_path)
    missing = sorted(_used_interface_literals() - set(source_catalog))
    if not missing:
        return []
    examples = '; '.join(f'{context}::{source!r}' for context, source in missing[:10])
    return [
        f'{source_path.relative_to(ROOT)} is missing {len(missing)} source string(s) used by code: {examples}'
    ]


def verify(language: str, version: str = '', strict_empty: bool = False, strict_missing: bool = False) -> list[str]:
    source_path = INTERFACE_DIR / 'english.xml'
    target_path = _target_path(language)
    if not target_path.exists():
        return [f'Interface file not found: {target_path.relative_to(ROOT)}']

    _source_version, source_catalog = _load_catalog(source_path)
    target_version, target_catalog = _load_catalog(target_path)
    errors = []
    is_source_catalog = target_path.resolve() == source_path.resolve()

    if version and target_version != version:
        errors.append(f'{target_path.relative_to(ROOT)} version is {target_version!r}, expected {version!r}')

    missing = sorted(set(source_catalog) - set(target_catalog))
    if strict_missing and missing:
        errors.append(f'{target_path.relative_to(ROOT)} is missing {len(missing)} source string(s)')

    empty = [
        key for key in source_catalog
        if key in target_catalog and not target_catalog[key].strip()
    ]
    if strict_empty and empty and not is_source_catalog:
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
    translated = available if is_source_catalog else available - len(empty)
    coverage = (translated / len(source_catalog) * 100) if source_catalog else 0
    print(
        f'{language}: {translated}/{len(source_catalog)} translated '
        f'({coverage:.1f}%), missing={len(missing)}, empty={len(empty)}'
    )
    return errors


def verify_all(version: str = '', strict_empty: bool = False, strict_missing: bool = False) -> list[str]:
    errors = verify_source_catalog()
    for path in _interface_files():
        errors.extend(verify(path.stem, version, strict_empty, strict_missing))
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Check interface XML localization health.')
    parser.add_argument('--language', default='vietnamese', help='Interface file stem, e.g. vietnamese or english.')
    parser.add_argument('--all', action='store_true', help='Check every interface XML file.')
    parser.add_argument('--version', default='', help='Expected interface XML version.')
    parser.add_argument('--strict-empty', action='store_true', help='Fail on empty translations.')
    parser.add_argument('--strict-missing', action='store_true', help='Fail on missing source strings.')
    args = parser.parse_args(argv)

    errors = (
        verify_all(args.version, args.strict_empty, args.strict_missing)
        if args.all
        else verify(args.language, args.version, args.strict_empty, args.strict_missing)
    )
    if errors:
        print('Interface localization verification failed:')
        for error in errors:
            print(f'  - {error}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
