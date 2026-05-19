# -*- coding: utf-8 -*-

import argparse
import csv
import json
import sys
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QCoreApplication

from packer.dbpf import DbpfPackage
from packer.resource import ResourceID
from packer.stbl import Stbl
from singletons.config import config
from singletons.state import app_state
from storages.packages import PackagesStorage


DEFAULT_DIRECTORY = ROOT / 'build' / 'synthetic'
DEFAULT_PACKAGE = 'synthetic_smoke.package'
EXPECTED_SOURCE = {42: 'Hello', 7: 'World'}
EXPECTED_IDS = set(EXPECTED_SOURCE)
SOURCE_LOCALE = 'ENG_US'
STBL_TYPE = 0x220557DA


class SmokeVerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SmokeSummary:
    checks: Tuple[str, ...]
    warnings: Tuple[str, ...]


class FakeDictionariesStorage:
    loaded = True

    @staticmethod
    def search(sid=None, source=None):
        return []

    @staticmethod
    def snapshot():
        return (), ()


def configure_storage(destination_locale: str) -> None:
    QCoreApplication.instance() or QCoreApplication([])
    config.set_value('translation', 'source', SOURCE_LOCALE)
    config.set_value('translation', 'destination', destination_locale)
    config.set_value('group', 'original', True)
    config.set_value('group', 'highbit', False)
    config.set_value('save', 'experemental', False)
    config.set_value('save', 'backup', False)
    config.set_value('dictionaries', 'strong', False)
    app_state.set_dictionaries_storage(FakeDictionariesStorage())
    app_state.set_current_package(None)
    app_state.set_current_instance(0)


def _parse_key(value) -> int:
    if isinstance(value, int):
        return value
    text = str(value)
    return int(text, 16)


def _assert_expected_ids(ids: Sequence[int], label: str) -> None:
    if len(ids) != len(set(ids)):
        raise SmokeVerificationError(f'{label}: duplicate string keys found: {ids}')
    if set(ids) != EXPECTED_IDS:
        raise SmokeVerificationError(f'{label}: expected keys {sorted(EXPECTED_IDS)}, got {sorted(ids)}')


def _package_stbl_tables(path: Path):
    tables = []
    with DbpfPackage.read(str(path)) as package:
        package.search()
        for rid in package.search_stbl():
            tables.append((rid, Stbl(rid, package[rid].content).strings))
    return tables


def _destination_locales(tables) -> List[str]:
    locales = {
        rid.language
        for rid, strings in tables
        if rid.language and rid.language != SOURCE_LOCALE and EXPECTED_IDS.issubset(strings)
    }
    return sorted(locales) or ['FRE_FR']


def verify_package_load(path: Path, destination_locale: str) -> str:
    configure_storage(destination_locale)
    storage = PackagesStorage()
    app_state.set_packages_storage(storage)
    storage.load(str(path))

    rows = [(item.id, item.source, item.translate) for item in storage.model.items]
    row_ids = [row[0] for row in rows]
    _assert_expected_ids(row_ids, f'{path.name} loaded as {destination_locale}')

    sources = {string_id: source for string_id, source, _translated in rows}
    if sources != EXPECTED_SOURCE:
        raise SmokeVerificationError(
            f'{path.name} loaded as {destination_locale}: expected sources {EXPECTED_SOURCE}, got {sources}'
        )

    cache_stats = storage.workspace_cache.stats()
    if cache_stats != (2, 2):
        raise SmokeVerificationError(
            f'{path.name} loaded as {destination_locale}: expected cache stats (2, 2), got {cache_stats}'
        )

    return f'{path.name} loaded as {destination_locale}: 2 unique rows, cache {cache_stats}'


def verify_primary_package(path: Path) -> List[str]:
    tables = _package_stbl_tables(path)
    if not tables:
        raise SmokeVerificationError(f'{path.name}: no STBL resources found')

    full_source_tables = [
        strings for rid, strings in tables
        if rid.language == SOURCE_LOCALE and strings == EXPECTED_SOURCE
    ]
    if not full_source_tables:
        raise SmokeVerificationError(f'{path.name}: full {SOURCE_LOCALE} source STBL was not found')

    checks = [f'{path.name}: {len(tables)} STBL resource(s) parsed']
    for locale in _destination_locales(tables):
        checks.append(verify_package_load(path, locale))
    return checks


def verify_export_package(path: Path) -> str:
    tables = _package_stbl_tables(path)
    if not tables:
        raise SmokeVerificationError(f'{path.name}: no STBL resources found')
    for rid, strings in tables:
        _assert_expected_ids(list(strings.keys()), f'{path.name} {rid.language}')
    return f'{path.name}: package export parsed with {len(tables)} STBL resource(s)'


def verify_json_export(path: Path) -> str:
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    entries = data.get('Entries')
    if not isinstance(entries, list):
        raise SmokeVerificationError(f'{path.name}: JSON export missing Entries list')
    _assert_expected_ids([_parse_key(entry.get('Key')) for entry in entries], path.name)
    return f'{path.name}: JSON export has {len(entries)} unique entries'


def verify_xml_export(path: Path) -> str:
    root = ElementTree.parse(path).getroot()
    if root.tag == 'STBLXMLResources':
        nodes = root.findall('.//String')
        ids = [_parse_key(node.get('id')) for node in nodes]
    elif root.tag == 'StblData':
        nodes = root.findall('.//TextStringDefinition')
        ids = [_parse_key(node.get('InstanceID')) for node in nodes]
    else:
        raise SmokeVerificationError(f'{path.name}: unsupported XML root {root.tag}')
    _assert_expected_ids(ids, path.name)
    return f'{path.name}: XML export has {len(ids)} unique strings'


def verify_csv_export(path: Path) -> str:
    with path.open('r', encoding='utf-8-sig', newline='') as fp:
        rows = list(csv.reader(fp))
    if not rows or rows[0] != ['Key', 'Translated Text']:
        raise SmokeVerificationError(f'{path.name}: unexpected CSV header')
    ids = [_parse_key(row[0]) for row in rows[1:]]
    _assert_expected_ids(ids, path.name)
    return f'{path.name}: CSV export has {len(ids)} unique rows'


def verify_stbl_export(path: Path) -> str:
    strings = Stbl(ResourceID(group=0, instance=1, type=STBL_TYPE), path.read_bytes()).strings
    _assert_expected_ids(list(strings.keys()), path.name)
    return f'{path.name}: STBL/Binary export has {len(strings)} unique strings'


def _export_files(directory: Path, primary_package: Path) -> Iterable[Path]:
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if path == primary_package or path.name.endswith('.backup') or not path.is_file():
            continue
        yield path


def verify_export_file(path: Path) -> str:
    if path.suffix == '.json':
        return verify_json_export(path)
    if path.suffix == '.xml':
        return verify_xml_export(path)
    if path.suffix == '.csv':
        return verify_csv_export(path)
    if path.suffix in {'.stbl', '.binary'}:
        return verify_stbl_export(path)
    if path.suffix == '.package':
        return verify_export_package(path)
    raise SmokeVerificationError(f'{path.name}: unsupported smoke artifact extension')


def verify_directory(directory: Path, require_gui_outputs: bool = False) -> SmokeSummary:
    directory = Path(directory).resolve()
    if not directory.exists():
        raise SmokeVerificationError(f'Smoke directory does not exist: {directory}')

    temp_files = sorted(path.name for path in directory.glob('*.tmp'))
    if temp_files:
        raise SmokeVerificationError(f'Temporary export files were left behind: {temp_files}')

    primary_package = directory / DEFAULT_PACKAGE
    if not primary_package.exists():
        raise SmokeVerificationError(f'Missing primary synthetic package: {primary_package}')

    checks = verify_primary_package(primary_package)
    exports = list(_export_files(directory, primary_package))
    warnings = []

    if require_gui_outputs and not exports:
        raise SmokeVerificationError('No GUI export artifacts found')
    if not exports:
        warnings.append('No GUI export artifacts found; only the synthetic package was verified.')

    for path in exports:
        checks.append(verify_export_file(path))

    return SmokeSummary(tuple(checks), tuple(warnings))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Verify synthetic GUI smoke-test artifacts.')
    parser.add_argument(
        '--directory',
        default=str(DEFAULT_DIRECTORY),
        help='Directory containing synthetic smoke artifacts. Defaults to build/synthetic.',
    )
    parser.add_argument(
        '--require-gui-outputs',
        action='store_true',
        help='Fail if only the generated package exists and no GUI export outputs are present.',
    )
    args = parser.parse_args(argv)

    try:
        summary = verify_directory(Path(args.directory), args.require_gui_outputs)
    except Exception as exc:
        print(f'Synthetic smoke verification failed: {exc}')
        return 1

    print('Synthetic smoke verification passed.')
    for check in summary.checks:
        print(f'  OK: {check}')
    for warning in summary.warnings:
        print(f'  WARN: {warning}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
