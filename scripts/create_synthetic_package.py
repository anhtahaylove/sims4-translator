# -*- coding: utf-8 -*-

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QCoreApplication

from scripts.synthetic_package import (
    EXTRA_PAYLOAD,
    create_synthetic_package,
    read_resource_content,
)
from singletons.config import config
from singletons.state import app_state
from storages.packages import PackagesStorage


DEFAULT_OUTPUT = ROOT / 'build' / 'synthetic' / 'synthetic_smoke.package'


class FakeDictionariesStorage:
    loaded = True

    @staticmethod
    def search(sid=None, source=None):
        return []

    @staticmethod
    def snapshot():
        return (), ()


def configure_storage() -> None:
    QCoreApplication.instance() or QCoreApplication([])
    config.set_value('translation', 'source', 'ENG_US')
    config.set_value('translation', 'destination', 'FRE_FR')
    config.set_value('group', 'original', True)
    config.set_value('group', 'highbit', False)
    config.set_value('save', 'experemental', False)
    config.set_value('save', 'backup', False)
    config.set_value('dictionaries', 'strong', False)
    app_state.set_dictionaries_storage(FakeDictionariesStorage())
    app_state.set_current_package(None)
    app_state.set_current_instance(0)


def validate_package(path: str, extra_resource) -> tuple:
    configure_storage()
    storage = PackagesStorage()
    app_state.set_packages_storage(storage)
    storage.load(path)
    extra_ok = read_resource_content(path, extra_resource) == EXTRA_PAYLOAD if extra_resource else True

    if len(storage.model.items) != 2:
        raise RuntimeError(f'Expected 2 unique loaded rows, got {len(storage.model.items)}')
    if storage.workspace_cache.stats() != (2, 2):
        raise RuntimeError(f'Expected cache stats (2, 2), got {storage.workspace_cache.stats()}')
    if not extra_ok:
        raise RuntimeError('Synthetic non-STBL resource was not preserved')

    return len(storage.model.items), storage.workspace_cache.stats()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Create a synthetic Sims 4 package for GUI smoke testing.')
    parser.add_argument(
        '--output',
        default=str(DEFAULT_OUTPUT),
        help='Output .package path. Defaults to build/synthetic/synthetic_smoke.package.',
    )
    args = parser.parse_args(argv)

    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output

    info = create_synthetic_package(str(output))
    unique_rows, cache_stats = validate_package(info.path, info.extra)

    print(f'Synthetic package: {Path(info.path).resolve()}')
    print(f'Validated load: {unique_rows} unique rows, cache stats {cache_stats}')
    print('Manual GUI smoke checklist:')
    print('  1. Open the app and load the package above.')
    print('  2. Confirm the table shows 2 unique rows: Hello and World.')
    print('  3. Export STBL/XML/XML-DP/JSON/Binary/CSV.')
    print('  4. Try Save As and Finalize As; the app should not freeze or stay busy.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
