# -*- coding: utf-8 -*-

import csv
import hashlib
import re
import sqlite3
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from singletons.config import ConfigManager, config
from utils.functions import text_to_edit, text_to_stbl


MEMORY_FILE_NAME = 'translation-memory.sqlite3'
STATUS_APPROVED = 'approved'
STATUS_DRAFT = 'draft'


@dataclass(frozen=True)
class TranslationMemoryStats:
    entries: int
    size_bytes: int


@dataclass(frozen=True)
class TranslationMemoryGroupStats:
    source_locale: str
    destination_locale: str
    engine: str
    entries: int


@dataclass(frozen=True)
class TranslationMemoryImportResult:
    imported: int
    skipped: int


@dataclass(frozen=True)
class TranslationMemoryEntry:
    source_locale: str
    destination_locale: str
    engine: str
    variant: str
    source_text: str
    translated_text: str
    status: str = STATUS_APPROVED
    score: float = 1.0
    package: str = ''
    record_id: int = 0
    instance: str = ''


class TranslationMemory:

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else ConfigManager.default_config_dir() / MEMORY_FILE_NAME

    @property
    def enabled(self) -> bool:
        return bool(config.value('translation_cache', 'enabled'))

    def lookup_exact(
            self,
            source_locale: str,
            destination_locale: str,
            engine: str,
            variant: str,
            source_text: str,
    ) -> str | None:
        conn = self.__connect()
        try:
            row = conn.execute(
                '''
                SELECT translated_text
                FROM entries
                WHERE source_locale = ?
                  AND destination_locale = ?
                  AND engine = ?
                  AND variant = ?
                  AND normalized_source_hash = ?
                ORDER BY CASE status WHEN 'approved' THEN 0 ELSE 1 END, updated_at DESC
                LIMIT 1
                ''',
                (
                    source_locale,
                    destination_locale,
                    engine,
                    variant,
                    self.__source_hash(source_text),
                ),
            ).fetchone()
        finally:
            conn.close()
        return str(row['translated_text']) if row else None

    def suggestions(
            self,
            source_locale: str,
            destination_locale: str,
            source_text: str,
            engine: str = '',
            variant: str = '',
            limit: int = 5,
            min_score: float = 0.72,
    ) -> tuple[TranslationMemoryEntry, ...]:
        normalized = normalize_source(source_text)
        if not normalized:
            return ()

        conn = self.__connect()
        try:
            rows = conn.execute(
                '''
                SELECT source_locale, destination_locale, engine, variant, source_text, translated_text,
                       status, package, record_id, instance, normalized_source
                FROM entries
                WHERE source_locale = ?
                  AND destination_locale = ?
                ORDER BY updated_at DESC
                LIMIT 2000
                ''',
                (source_locale, destination_locale),
            ).fetchall()
        finally:
            conn.close()

        scored = []
        for row in rows:
            score = SequenceMatcher(None, normalized, row['normalized_source']).ratio()
            if score < min_score:
                continue
            provider_bonus = 0.05 if row['engine'] == engine and row['variant'] == variant else 0.0
            status_bonus = 0.03 if row['status'] == STATUS_APPROVED else 0.0
            scored.append((
                min(score + provider_bonus + status_bonus, 1.0),
                TranslationMemoryEntry(
                    source_locale=row['source_locale'],
                    destination_locale=row['destination_locale'],
                    engine=row['engine'],
                    variant=row['variant'],
                    source_text=row['source_text'],
                    translated_text=row['translated_text'],
                    status=row['status'],
                    score=score,
                    package=row['package'],
                    record_id=int(row['record_id'] or 0),
                    instance=row['instance'],
                ),
            ))

        scored.sort(key=lambda item: item[0], reverse=True)
        return tuple(entry for _score, entry in scored[:limit])

    def store(
            self,
            source_locale: str,
            destination_locale: str,
            engine: str,
            variant: str,
            source_text: str,
            translated_text: str,
            status: str = STATUS_APPROVED,
            package: str = '',
            record_id: int = 0,
            instance: str | int = '',
    ) -> None:
        normalized = normalize_source(source_text)
        translated = text_to_stbl(translated_text)
        if not normalized or not translated.strip() or normalize_source(translated) == normalized:
            return

        conn = self.__connect()
        try:
            conn.execute(
                '''
                INSERT INTO entries (
                    source_locale,
                    destination_locale,
                    engine,
                    variant,
                    normalized_source_hash,
                    normalized_source,
                    source_text,
                    translated_text,
                    status,
                    package,
                    record_id,
                    instance,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(
                    source_locale,
                    destination_locale,
                    engine,
                    variant,
                    normalized_source_hash,
                    translated_text
                )
                DO UPDATE SET
                    source_text = excluded.source_text,
                    status = excluded.status,
                    package = excluded.package,
                    record_id = excluded.record_id,
                    instance = excluded.instance,
                    updated_at = excluded.updated_at
                ''',
                (
                    source_locale,
                    destination_locale,
                    engine,
                    variant,
                    self.__source_hash(source_text),
                    normalized,
                    text_to_stbl(source_text),
                    translated,
                    status if status in (STATUS_APPROVED, STATUS_DRAFT) else STATUS_DRAFT,
                    _safe_package_name(package),
                    int(record_id or 0),
                    _instance_text(instance),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def clear(
            self,
            source_locale: str = '',
            destination_locale: str = '',
            engine: str = '',
    ) -> None:
        if not self.path.exists():
            return
        conn = self.__connect()
        try:
            clauses = []
            params = []
            if source_locale:
                clauses.append('source_locale = ?')
                params.append(source_locale)
            if destination_locale:
                clauses.append('destination_locale = ?')
                params.append(destination_locale)
            if engine:
                clauses.append('engine = ?')
                params.append(engine)
            where = f" WHERE {' AND '.join(clauses)}" if clauses else ''
            conn.execute(f'DELETE FROM entries{where}', params)
            conn.commit()
            conn.execute('VACUUM')
        finally:
            conn.close()

    def stats(self) -> TranslationMemoryStats:
        if not self.path.exists():
            return TranslationMemoryStats(0, 0)
        conn = self.__connect()
        try:
            row = conn.execute('SELECT COUNT(*) FROM entries').fetchone()
        finally:
            conn.close()
        return TranslationMemoryStats(int(row[0] or 0), self.path.stat().st_size)

    def group_stats(self) -> tuple[TranslationMemoryGroupStats, ...]:
        if not self.path.exists():
            return ()
        conn = self.__connect()
        try:
            rows = conn.execute(
                '''
                SELECT source_locale, destination_locale, engine, COUNT(*) AS entries
                FROM entries
                GROUP BY source_locale, destination_locale, engine
                ORDER BY entries DESC, source_locale, destination_locale, engine
                '''
            ).fetchall()
        finally:
            conn.close()
        return tuple(
            TranslationMemoryGroupStats(
                source_locale=row['source_locale'],
                destination_locale=row['destination_locale'],
                engine=row['engine'],
                entries=int(row['entries'] or 0),
            )
            for row in rows
        )

    def count(
            self,
            source_locale: str = '',
            destination_locale: str = '',
            engine: str = '',
    ) -> int:
        if not self.path.exists():
            return 0
        conn = self.__connect()
        try:
            clauses = []
            params = []
            if source_locale:
                clauses.append('source_locale = ?')
                params.append(source_locale)
            if destination_locale:
                clauses.append('destination_locale = ?')
                params.append(destination_locale)
            if engine:
                clauses.append('engine = ?')
                params.append(engine)
            where = f" WHERE {' AND '.join(clauses)}" if clauses else ''
            row = conn.execute(f'SELECT COUNT(*) FROM entries{where}', params).fetchone()
            return int(row[0] or 0)
        finally:
            conn.close()

    def export_csv(self, path: str | Path) -> int:
        rows = self.__all_entries()
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=_csv_fieldnames())
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row[field] for field in _csv_fieldnames()})
        return len(rows)

    def import_csv(self, path: str | Path) -> TranslationMemoryImportResult:
        imported = 0
        skipped = 0
        with Path(path).open('r', encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            required = set(_csv_fieldnames())
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise ValueError('Translation Memory CSV is missing required columns.')

            for row in reader:
                before = self.count()
                self.store(
                    row.get('source_locale', ''),
                    row.get('destination_locale', ''),
                    row.get('engine', ''),
                    row.get('variant', ''),
                    row.get('source_text', ''),
                    row.get('translated_text', ''),
                    status=row.get('status', STATUS_DRAFT),
                    package=row.get('package', ''),
                    record_id=_safe_int(row.get('record_id', '')),
                    instance=row.get('instance', ''),
                )
                after = self.count()
                if after > before or self.lookup_exact(
                        row.get('source_locale', ''),
                        row.get('destination_locale', ''),
                        row.get('engine', ''),
                        row.get('variant', ''),
                        row.get('source_text', ''),
                ) == text_to_stbl(row.get('translated_text', '')):
                    imported += 1
                else:
                    skipped += 1
        return TranslationMemoryImportResult(imported, skipped)

    def __connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS entries (
                source_locale TEXT NOT NULL,
                destination_locale TEXT NOT NULL,
                engine TEXT NOT NULL,
                variant TEXT NOT NULL,
                normalized_source_hash TEXT NOT NULL,
                normalized_source TEXT NOT NULL,
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                status TEXT NOT NULL,
                package TEXT NOT NULL DEFAULT '',
                record_id INTEGER NOT NULL DEFAULT 0,
                instance TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                PRIMARY KEY (
                    source_locale,
                    destination_locale,
                    engine,
                    variant,
                    normalized_source_hash,
                    translated_text
                )
            )
            '''
        )
        conn.commit()
        return conn

    def __all_entries(self) -> tuple[sqlite3.Row, ...]:
        if not self.path.exists():
            return ()
        conn = self.__connect()
        try:
            rows = conn.execute(
                '''
                SELECT source_locale, destination_locale, engine, variant, source_text, translated_text,
                       status, package, record_id, instance, updated_at
                FROM entries
                ORDER BY updated_at DESC, source_locale, destination_locale, engine
                '''
            ).fetchall()
        finally:
            conn.close()
        return tuple(rows)

    @staticmethod
    def __source_hash(source_text: str) -> str:
        return hashlib.sha256(normalize_source(source_text).encode('utf-8')).hexdigest()


def normalize_source(text: str | None) -> str:
    normalized = text_to_edit(text_to_stbl(text))
    normalized = re.sub(r'\s+', ' ', normalized).strip().casefold()
    return normalized


def _safe_package_name(package: str | None) -> str:
    if not package:
        return ''
    return Path(str(package)).name


def _instance_text(instance: str | int | None) -> str:
    if instance is None:
        return ''
    if isinstance(instance, int):
        return f'0x{instance:016x}'
    return str(instance)


def _safe_int(value: str | int | None) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _csv_fieldnames() -> tuple[str, ...]:
    return (
        'source_locale',
        'destination_locale',
        'engine',
        'variant',
        'source_text',
        'translated_text',
        'status',
        'package',
        'record_id',
        'instance',
        'updated_at',
    )


translation_memory = TranslationMemory()
