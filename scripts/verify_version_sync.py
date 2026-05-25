# -*- coding: utf-8 -*-

import argparse
import ast
import re
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXACT_ZIP_PATTERN = re.compile(r'The-Sims-4-Translator-Plus-v\d+\.\d+\.\d+-windows\.zip')


def _constant_value(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise RuntimeError(f'{name} was not found in {path}')


def _interface_version(path: Path) -> str:
    return ElementTree.parse(path).getroot().get('version') or ''


def verify(version: str) -> list[str]:
    errors = []

    app_version = _constant_value(ROOT / 'utils' / 'constants.py', 'APP_VERSION')
    if app_version != version:
        errors.append(f'utils/constants.py APP_VERSION is {app_version!r}, expected {version!r}')

    changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    if not re.search(rf'^## Version {re.escape(version)}\b', changelog, re.MULTILINE):
        errors.append(f'CHANGELOG.md is missing latest heading for Version {version}')

    for path in sorted((ROOT / 'prefs' / 'interface').glob('*.xml')):
        xml_version = _interface_version(path)
        if xml_version != version:
            errors.append(f'{path.relative_to(ROOT)} version is {xml_version!r}, expected {version!r}')

    for path in (ROOT / 'README.md', ROOT / 'README.vi.md', ROOT / 'docs' / 'release-checklist.md'):
        text = path.read_text(encoding='utf-8')
        exact_zip = EXACT_ZIP_PATTERN.search(text)
        if exact_zip:
            errors.append(f'{path.relative_to(ROOT)} hard-codes release ZIP {exact_zip.group(0)}')

    checklist = (ROOT / 'docs' / 'release-checklist.md').read_text(encoding='utf-8')
    if 'The-Sims-4-Translator-Plus-vX.Y.Z-windows.zip' not in checklist:
        errors.append('docs/release-checklist.md is missing the release ZIP naming template')

    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Verify release version references stay in sync.')
    parser.add_argument('--version', required=True, help='Expected semantic version, for example 2.0.0.')
    args = parser.parse_args(argv)

    errors = verify(args.version)
    if errors:
        print('Version sync verification failed:')
        for error in errors:
            print(f'  - {error}')
        return 1

    print(f'Version sync OK for {args.version}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
