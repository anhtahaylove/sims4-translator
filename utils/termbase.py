# -*- coding: utf-8 -*-

import csv
from dataclasses import dataclass
from pathlib import Path

from singletons.config import ConfigManager
from utils.runtime_paths import resource_path


TERMBASE_FIELDNAMES = ('source_term', 'expected_translation', 'note')

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
class TermbaseEntry:
    source_term: str
    expected_translation: str
    note: str = ''
    source: str = 'user'


@dataclass(frozen=True)
class TermbaseStats:
    locale: str
    effective_entries: int
    bundled_entries: int
    user_entries: int
    user_path: Path


@dataclass(frozen=True)
class TermbaseImportResult:
    imported: int
    skipped: int
    path: Path


def normalize_locale(locale: str) -> str:
    return (locale or '').strip().upper()


def bundled_termbase_path(locale: str) -> Path:
    return resource_path('prefs', 'termbase', f'{normalize_locale(locale)}.csv')


def user_termbase_path(locale: str) -> Path:
    return ConfigManager.default_config_dir() / 'termbase' / f'{normalize_locale(locale)}.csv'


def effective_termbase_entries(locale: str) -> tuple[TermbaseEntry, ...]:
    locale = normalize_locale(locale)
    entries: dict[str, TermbaseEntry] = {}

    for source_term, expected_translation, note in DEFAULT_TERMINOLOGY_TERMS.get(locale, ()):
        entry = TermbaseEntry(source_term, expected_translation, note, 'default')
        entries[source_term.casefold()] = entry

    for entry in read_termbase_csv(bundled_termbase_path(locale), source='bundled'):
        entries[entry.source_term.casefold()] = entry

    for entry in read_termbase_csv(user_termbase_path(locale), source='user'):
        entries[entry.source_term.casefold()] = entry

    return tuple(entries.values())


def effective_termbase_terms(locale: str) -> tuple[tuple[str, str], ...]:
    return tuple(
        (entry.source_term, entry.expected_translation)
        for entry in effective_termbase_entries(locale)
    )


def user_termbase_entries(locale: str) -> tuple[TermbaseEntry, ...]:
    return read_termbase_csv(user_termbase_path(locale), source='user')


def termbase_stats(locale: str) -> TermbaseStats:
    locale = normalize_locale(locale)
    return TermbaseStats(
        locale=locale,
        effective_entries=len(effective_termbase_entries(locale)),
        bundled_entries=len(read_termbase_csv(bundled_termbase_path(locale), source='bundled')),
        user_entries=len(user_termbase_entries(locale)),
        user_path=user_termbase_path(locale),
    )


def read_termbase_csv(path: str | Path, source: str = 'user') -> tuple[TermbaseEntry, ...]:
    try:
        with Path(path).open('r', encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                return ()
            entries = []
            for row in reader:
                source_term = (row.get('source_term') or '').strip()
                expected_translation = (row.get('expected_translation') or '').strip()
                note = (row.get('note') or '').strip()
                if source_term and expected_translation:
                    entries.append(TermbaseEntry(source_term, expected_translation, note, source))
            return tuple(entries)
    except FileNotFoundError:
        return ()


def write_termbase_csv(path: str | Path, entries: tuple[TermbaseEntry, ...] | list[TermbaseEntry]) -> int:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=TERMBASE_FIELDNAMES)
        writer.writeheader()
        count = 0
        for entry in entries:
            if not entry.source_term.strip() or not entry.expected_translation.strip():
                continue
            writer.writerow({
                'source_term': entry.source_term.strip(),
                'expected_translation': entry.expected_translation.strip(),
                'note': entry.note.strip(),
            })
            count += 1
    return count


def export_effective_termbase(locale: str, path: str | Path) -> int:
    return write_termbase_csv(path, effective_termbase_entries(locale))


def import_user_termbase(locale: str, path: str | Path) -> TermbaseImportResult:
    imported_entries = read_termbase_csv(path, source='user')
    if not imported_entries:
        raise ValueError('Termbase CSV is missing required columns or valid entries.')
    destination = user_termbase_path(locale)
    imported = write_termbase_csv(destination, imported_entries)
    return TermbaseImportResult(imported=imported, skipped=len(imported_entries) - imported, path=destination)


def ensure_user_termbase(locale: str) -> Path:
    path = user_termbase_path(locale)
    if path.exists():
        return path
    entries = read_termbase_csv(bundled_termbase_path(locale), source='bundled')
    write_termbase_csv(path, entries)
    return path


def clear_user_termbase(locale: str) -> int:
    path = user_termbase_path(locale)
    count = len(user_termbase_entries(locale))
    if path.exists():
        path.unlink()
    return count
