# -*- coding: utf-8 -*-

from typing import List, NamedTuple

from packer.resource import ResourceID
from singletons.config import config
from utils.functions import compare
from utils.constants import *


class AbstractRecord(list):

    def __init__(self, *args):
        super().__init__(args)


class RecordOccurrence(NamedTuple):
    resource_original: ResourceID
    package: str
    index_alt: tuple
    comment: str = ''


class MainRecord(AbstractRecord):

    def __init__(self, *args):
        super().__init__(*args)

        if len(self) <= RECORD_MAIN_OCCURRENCES:
            self.append([
                RecordOccurrence(
                    self.resource_original,
                    self.package,
                    self[RECORD_MAIN_INDEX_ALT],
                    self.comment
                )
            ])

    @property
    def idx(self) -> int:
        return self[RECORD_MAIN_INDEX]

    @idx.setter
    def idx(self, value: int) -> None:
        self[RECORD_MAIN_INDEX] = value

    @property
    def idx_standart(self) -> int:
        return self[RECORD_MAIN_INDEX_ALT][0]

    @property
    def idx_source(self) -> int:
        return self[RECORD_MAIN_INDEX_ALT][1]

    @property
    def idx_dp(self) -> int:
        return self[RECORD_MAIN_INDEX_ALT][1]

    @property
    def id(self) -> int:
        return self[RECORD_MAIN_ID]

    @property
    def id_hex(self) -> str:
        return '0x{sid:08X}'.format(sid=self[RECORD_MAIN_ID])

    @property
    def instance(self) -> int:
        return self[RECORD_MAIN_INSTANCE]

    @property
    def instance_hex(self) -> str:
        return '0x{instance:016X}'.format(instance=self[RECORD_MAIN_INSTANCE])

    @property
    def group(self) -> int:
        return self[RECORD_MAIN_GROUP]

    @property
    def group_hex(self) -> str:
        return '0x{group:08X}'.format(group=self[RECORD_MAIN_GROUP])

    @property
    def source(self) -> str:
        return self[RECORD_MAIN_SOURCE]

    @property
    def source_old(self) -> str:
        return self[RECORD_MAIN_SOURCE_OLD]

    @source_old.setter
    def source_old(self, value: str) -> None:
        self[RECORD_MAIN_SOURCE_OLD] = value

    @property
    def translate(self) -> str:
        return self[RECORD_MAIN_TRANSLATE]

    @translate.setter
    def translate(self, value: str) -> None:
        self[RECORD_MAIN_TRANSLATE] = value

    @property
    def translate_old(self) -> str:
        return self[RECORD_MAIN_TRANSLATE_OLD]

    @translate_old.setter
    def translate_old(self, value: str) -> None:
        self[RECORD_MAIN_TRANSLATE_OLD] = value

    @property
    def flag(self) -> int:
        return self[RECORD_MAIN_FLAG]

    @flag.setter
    def flag(self, value: int) -> None:
        self[RECORD_MAIN_FLAG] = value

    @property
    def resource(self) -> ResourceID:
        return self[RECORD_MAIN_RESOURCE]

    @property
    def resource_original(self) -> ResourceID:
        return self[RECORD_MAIN_RESOURCE_ORIGINAL]

    @property
    def package(self) -> str:
        return self[RECORD_MAIN_PACKAGE]

    @property
    def comment(self) -> str:
        return self[RECORD_MAIN_COMMENT]

    @comment.setter
    def comment(self, value: str) -> None:
        self[RECORD_MAIN_COMMENT] = value

    @property
    def occurrences(self) -> List[RecordOccurrence]:
        return self[RECORD_MAIN_OCCURRENCES]

    @property
    def occurrence_count(self) -> int:
        return len(self.occurrences)

    @property
    def dedupe_key(self) -> tuple:
        return self.id, self.source, self.translate

    def add_occurrence(self, occurrence: RecordOccurrence) -> None:
        self.occurrences.append(occurrence)

    def has_package(self, package: str) -> bool:
        return any(o.package == package for o in self.occurrences)

    def has_instance(self, instance: int) -> bool:
        return any(self.resource_for_occurrence(o).instance == instance for o in self.occurrences)

    def has_occurrence(self, package: str = None, instance: int = 0) -> bool:
        for occurrence in self.occurrences:
            if package and occurrence.package != package:
                continue
            if instance and self.resource_for_occurrence(occurrence).instance != instance:
                continue
            return True
        return False

    def remove_package(self, package: str) -> bool:
        self[RECORD_MAIN_OCCURRENCES] = [o for o in self.occurrences if o.package != package]
        if not self.occurrences:
            return False

        self.__sync_primary_occurrence()
        return True

    @staticmethod
    def resource_for_occurrence(occurrence: RecordOccurrence) -> ResourceID:
        rid = occurrence.resource_original
        if not config.value('group', 'original'):
            rid = rid.convert_group(highbit=config.value('group', 'highbit'))
        return rid

    def expanded(self, package: str = None, instance: int = 0) -> List['MainRecord']:
        records = []
        for occurrence in self.occurrences:
            if package and occurrence.package != package:
                continue

            rid = self.resource_for_occurrence(occurrence)
            if instance and rid.instance != instance:
                continue

            records.append(MainRecord(
                self.idx,
                self.id,
                rid.instance,
                rid.group,
                self.source,
                self.translate,
                self.flag,
                rid,
                occurrence.resource_original,
                occurrence.package,
                self.source_old,
                self.translate_old,
                occurrence.index_alt,
                self.comment,
                [occurrence]
            ))
        return records

    def __sync_primary_occurrence(self) -> None:
        occurrence = self.occurrences[0]
        rid = self.resource_for_occurrence(occurrence)
        self[RECORD_MAIN_INSTANCE] = rid.instance
        self[RECORD_MAIN_GROUP] = rid.group
        self[RECORD_MAIN_RESOURCE] = rid
        self[RECORD_MAIN_RESOURCE_ORIGINAL] = occurrence.resource_original
        self[RECORD_MAIN_PACKAGE] = occurrence.package
        self[RECORD_MAIN_INDEX_ALT] = occurrence.index_alt

    def compare(self) -> bool:
        return compare(self[RECORD_MAIN_SOURCE], self[RECORD_MAIN_TRANSLATE])
