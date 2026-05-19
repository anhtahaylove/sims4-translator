# -*- coding: utf-8 -*-

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from packer.dbpf import DbpfPackage
from packer.resource import ResourceID
from packer.stbl import Stbl


DEFAULT_SOURCE_STRINGS = {42: 'Hello', 7: 'World'}
DEFAULT_DESTINATION_STRINGS = {42: 'Bonjour', 7: 'Monde'}
DEFAULT_DUPLICATE_SOURCE_STRINGS = {42: 'Hello'}
DEFAULT_DUPLICATE_DESTINATION_STRINGS = {42: 'Bonjour'}
EXTRA_RESOURCE = ResourceID(group=0x12345678, instance=0x000000000000CAFE, type=0x545AC67A)
EXTRA_PAYLOAD = b'non-stbl-payload'


@dataclass(frozen=True)
class SyntheticPackageInfo:
    path: str
    source: ResourceID
    destination: ResourceID
    duplicate_source: Optional[ResourceID]
    duplicate_destination: Optional[ResourceID]
    extra: Optional[ResourceID]


def build_stbl(rid: ResourceID, strings: Dict[int, str]) -> Stbl:
    stbl = Stbl(rid)
    for key, value in strings.items():
        stbl.add(key, value)
    return stbl


def create_synthetic_package(
    path: str,
    source_strings: Optional[Dict[int, str]] = None,
    destination_strings: Optional[Dict[int, str]] = None,
    include_destination: bool = True,
    include_duplicate: bool = True,
    include_extra: bool = True,
) -> SyntheticPackageInfo:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    source = ResourceID(group=0, instance=0x0000000000000001, type=0x220557DA)
    destination = source.convert_instance('FRE_FR')
    duplicate_source = ResourceID(group=0, instance=0x0000000000000002, type=0x220557DA)
    duplicate_destination = duplicate_source.convert_instance('FRE_FR')

    source_strings = DEFAULT_SOURCE_STRINGS if source_strings is None else source_strings
    destination_strings = DEFAULT_DESTINATION_STRINGS if destination_strings is None else destination_strings

    with DbpfPackage.write(str(output)) as package:
        package.put(source, build_stbl(source, source_strings).binary)
        if include_destination:
            package.put(destination, build_stbl(destination, destination_strings).binary)
        if include_duplicate:
            package.put(duplicate_source, build_stbl(duplicate_source, DEFAULT_DUPLICATE_SOURCE_STRINGS).binary)
            if include_destination:
                package.put(duplicate_destination, build_stbl(duplicate_destination, DEFAULT_DUPLICATE_DESTINATION_STRINGS).binary)
        if include_extra:
            package.put(EXTRA_RESOURCE, EXTRA_PAYLOAD)

    return SyntheticPackageInfo(
        path=str(output),
        source=source,
        destination=destination,
        duplicate_source=duplicate_source if include_duplicate else None,
        duplicate_destination=duplicate_destination if include_duplicate and include_destination else None,
        extra=EXTRA_RESOURCE if include_extra else None,
    )


def read_stbl_by_locale(path: str, locale: str) -> Dict[ResourceID, Dict[int, str]]:
    tables = {}
    with DbpfPackage.read(path) as dbfile:
        for rid in dbfile.search_stbl():
            if rid.language == locale:
                tables[rid] = Stbl(rid, dbfile[rid].content).strings
    return tables


def read_resource_content(path: str, rid: ResourceID):
    with DbpfPackage.read(path) as dbfile:
        dbfile.search()
        resource = dbfile[rid]
        return resource.content if resource else None
