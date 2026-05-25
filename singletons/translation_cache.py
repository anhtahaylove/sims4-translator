# -*- coding: utf-8 -*-

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from singletons.config import ConfigManager, config


CACHE_FILE_NAME = 'translation-cache.sqlite3'


@dataclass(frozen=True)
class TranslationCacheStats:
    entries: int
    size_bytes: int


class TranslationCache:

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else ConfigManager.default_config_dir() / CACHE_FILE_NAME

    @property
    def enabled(self) -> bool:
        return bool(config.value('translation_cache', 'enabled'))

    def lookup(
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
                FROM translations
                WHERE source_locale = ?
                  AND destination_locale = ?
                  AND engine = ?
                  AND variant = ?
                  AND source_hash = ?
                ''',
                (source_locale, destination_locale, engine, variant, self.__source_hash(source_text)),
            ).fetchone()
        finally:
            conn.close()
        return row[0] if row else None

    def store(
            self,
            source_locale: str,
            destination_locale: str,
            engine: str,
            variant: str,
            source_text: str,
            translated_text: str,
    ) -> None:
        conn = self.__connect()
        try:
            conn.execute(
                '''
                INSERT INTO translations (
                    source_locale,
                    destination_locale,
                    engine,
                    variant,
                    source_hash,
                    translated_text,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(source_locale, destination_locale, engine, variant, source_hash)
                DO UPDATE SET
                    translated_text = excluded.translated_text,
                    updated_at = excluded.updated_at
                ''',
                (
                    source_locale,
                    destination_locale,
                    engine,
                    variant,
                    self.__source_hash(source_text),
                    translated_text,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def clear(self) -> None:
        if not self.path.exists():
            return
        conn = self.__connect()
        try:
            conn.execute('DELETE FROM translations')
            conn.commit()
            conn.execute('VACUUM')
        finally:
            conn.close()

    def stats(self) -> TranslationCacheStats:
        if not self.path.exists():
            return TranslationCacheStats(0, 0)
        conn = self.__connect()
        try:
            row = conn.execute('SELECT COUNT(*) FROM translations').fetchone()
        finally:
            conn.close()
        return TranslationCacheStats(int(row[0] or 0), self.path.stat().st_size)

    def __connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS translations (
                source_locale TEXT NOT NULL,
                destination_locale TEXT NOT NULL,
                engine TEXT NOT NULL,
                variant TEXT NOT NULL,
                source_hash TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (source_locale, destination_locale, engine, variant, source_hash)
            )
            '''
        )
        conn.commit()
        return conn

    @staticmethod
    def __source_hash(source_text: str) -> str:
        return hashlib.sha256((source_text or '').encode('utf-8')).hexdigest()


translation_cache = TranslationCache()
