# -*- coding: utf-8 -*-

import sqlite3
from typing import Tuple

from storages.records import RecordOccurrence


def _chunks(items, size: int):
    for index in range(0, len(items), size):
        yield items[index:index + size]


class WorkspaceCache:

    def __init__(self, path: str = ':memory:') -> None:
        self.connection = sqlite3.connect(path)
        self.__closed = False
        self.connection.execute('PRAGMA foreign_keys = ON')
        self.__create_schema()

    def __create_schema(self) -> None:
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS translation_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                string_id INTEGER NOT NULL,
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                UNIQUE(string_id, source_text, translated_text)
            );

            CREATE TABLE IF NOT EXISTS record_occurrences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL REFERENCES translation_records(id) ON DELETE CASCADE,
                package_key TEXT NOT NULL,
                resource_group INTEGER NOT NULL,
                resource_instance INTEGER NOT NULL,
                resource_type INTEGER NOT NULL,
                source_line INTEGER NOT NULL,
                original_row INTEGER NOT NULL,
                comment TEXT NOT NULL DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_record_occurrences_record
                ON record_occurrences(record_id);

            CREATE INDEX IF NOT EXISTS idx_record_occurrences_package
                ON record_occurrences(package_key);
        """)
        self.connection.commit()

    def clear(self) -> None:
        self.connection.execute('DELETE FROM record_occurrences')
        self.connection.execute('DELETE FROM translation_records')
        self.connection.commit()

    def remove_package(self, package_key: str) -> None:
        self.connection.execute(
            'DELETE FROM record_occurrences WHERE package_key = ?',
            (package_key,)
        )
        self.connection.execute("""
            DELETE FROM translation_records
            WHERE NOT EXISTS (
                SELECT 1
                FROM record_occurrences
                WHERE record_occurrences.record_id = translation_records.id
            )
        """)
        self.connection.commit()

    def add(self, key: Tuple[int, str, str], occurrence: RecordOccurrence) -> int:
        string_id, source_text, translated_text = key
        cursor = self.connection.execute(
            """
            INSERT INTO translation_records (string_id, source_text, translated_text)
            VALUES (?, ?, ?)
            ON CONFLICT(string_id, source_text, translated_text) DO NOTHING
            """,
            (string_id, source_text, translated_text)
        )
        record_id = self.connection.execute(
            """
            SELECT id
            FROM translation_records
            WHERE string_id = ? AND source_text = ? AND translated_text = ?
            """,
            (string_id, source_text, translated_text)
        ).fetchone()[0]

        if cursor.rowcount == 0:
            return record_id

        source_line = occurrence.index_alt[1] if len(occurrence.index_alt) > 1 else 0
        original_row = occurrence.index_alt[0] if occurrence.index_alt else 0

        self.connection.execute(
            """
            INSERT INTO record_occurrences (
                record_id,
                package_key,
                resource_group,
                resource_instance,
                resource_type,
                source_line,
                original_row,
                comment
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                occurrence.package,
                occurrence.resource_original.group,
                occurrence.resource_original.instance,
                occurrence.resource_original.type,
                source_line,
                original_row,
                occurrence.comment or ''
            )
        )
        return record_id

    def add_many(self, entries) -> list:
        entries = list(entries)
        if not entries:
            return []

        first_occurrence_by_key = {}
        for key, occurrence in entries:
            first_occurrence_by_key.setdefault(key, occurrence)

        unique_keys = list(first_occurrence_by_key)
        existing_keys = set()

        for key_chunk in _chunks(unique_keys, 250):
            placeholders = ', '.join(['(?, ?, ?)'] * len(key_chunk))
            params = [value for key in key_chunk for value in key]
            rows = self.connection.execute(
                f"""
                SELECT string_id, source_text, translated_text
                FROM translation_records
                WHERE (string_id, source_text, translated_text) IN ({placeholders})
                """,
                params
            ).fetchall()
            existing_keys.update((string_id, source_text, translated_text)
                                 for string_id, source_text, translated_text in rows)

        self.connection.executemany(
            """
            INSERT INTO translation_records (string_id, source_text, translated_text)
            VALUES (?, ?, ?)
            ON CONFLICT(string_id, source_text, translated_text) DO NOTHING
            """,
            unique_keys
        )

        record_ids = {}
        for key_chunk in _chunks(unique_keys, 250):
            placeholders = ', '.join(['(?, ?, ?)'] * len(key_chunk))
            params = [value for key in key_chunk for value in key]
            rows = self.connection.execute(
                f"""
                SELECT id, string_id, source_text, translated_text
                FROM translation_records
                WHERE (string_id, source_text, translated_text) IN ({placeholders})
                """,
                params
            ).fetchall()
            for record_id, string_id, source_text, translated_text in rows:
                record_ids[(string_id, source_text, translated_text)] = record_id

        occurrence_rows = []
        result_ids = []
        for key, occurrence in first_occurrence_by_key.items():
            if key in existing_keys:
                continue
            record_id = record_ids[key]
            result_ids.append(record_id)
            source_line = occurrence.index_alt[1] if len(occurrence.index_alt) > 1 else 0
            original_row = occurrence.index_alt[0] if occurrence.index_alt else 0
            occurrence_rows.append((
                record_id,
                occurrence.package,
                occurrence.resource_original.group,
                occurrence.resource_original.instance,
                occurrence.resource_original.type,
                source_line,
                original_row,
                occurrence.comment or ''
            ))

        self.connection.executemany(
            """
            INSERT INTO record_occurrences (
                record_id,
                package_key,
                resource_group,
                resource_instance,
                resource_type,
                source_line,
                original_row,
                comment
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            occurrence_rows
        )
        return result_ids

    def commit(self) -> None:
        self.connection.commit()

    def stats(self) -> tuple:
        records = self.connection.execute('SELECT COUNT(*) FROM translation_records').fetchone()[0]
        occurrences = self.connection.execute('SELECT COUNT(*) FROM record_occurrences').fetchone()[0]
        return records, occurrences

    def close(self) -> None:
        if self.__closed:
            return
        self.__closed = True
        self.connection.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
