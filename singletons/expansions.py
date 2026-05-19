# -*- coding: utf-8 -*-

import os
from collections import namedtuple
from typing import List, Dict, Union

from singletons.config import config
from singletons.interface import interface


STUFF_PACK_CODES = {
    'SP01', 'SP02', 'SP03', 'SP04', 'SP05', 'SP06', 'SP07', 'SP08', 'SP09',
    'SP10', 'SP11', 'SP12', 'SP13', 'SP14', 'SP15', 'SP16', 'SP17', 'SP18',
    'SP46', 'SP49',
}

CATEGORY_TITLES = {
    'expansion': 'Expansion packs',
    'game': 'Game packs',
    'stuff': 'Stuff packs',
    'kit': 'Kits',
    'free': 'Free packs',
}


class Expansion(namedtuple('Expansion', 'names folder metadata')):

    names: Union[str, Dict[str, str]]
    folder: str
    metadata: Dict[str, str]

    def __new__(cls, names, folder, metadata=None):
        return super().__new__(cls, names, folder, metadata or {})

    @property
    def status(self) -> str:
        if self.exists:
            if not self.exists_source:
                return interface.text('OptionsDialog', '{} not exist').format(expansions.strings_source)
            elif not self.exists_dest:
                return interface.text('OptionsDialog', '{} not exist').format(expansions.strings_dest)
            else:
                return interface.text('OptionsDialog', 'FOUND')
        else:
            return interface.text('OptionsDialog', 'NOT FOUND')

    @property
    def name(self) -> str:
        if isinstance(self.names, str):
            return interface.text('OptionsDialog', self.names)
        elif isinstance(self.names, dict):
            key = 'name_' + config.value('interface', 'language').lower()
            return self.names.get(key, self.names.get('name_en_us', self.folder))
        else:
            return self.folder

    @property
    def category(self) -> str:
        pack_type = self.metadata.get('type', '').lower()
        if pack_type == 'base game' or '/' in self.folder:
            return 'base'
        if pack_type == 'expansion pack':
            return 'expansion'
        if pack_type == 'game pack':
            return 'game'
        if pack_type == 'stuff pack':
            return 'stuff'
        if pack_type == 'kit':
            return 'kit'
        if pack_type == 'free pack':
            return 'free'

        folder = self.folder.upper()
        if folder.startswith('EP'):
            return 'expansion'
        if folder.startswith('GP'):
            return 'game'
        if folder.startswith('FP'):
            return 'free'
        if folder.startswith('SP'):
            return 'stuff' if folder in STUFF_PACK_CODES else 'kit'
        return 'kit'

    @property
    def category_title(self) -> str:
        return CATEGORY_TITLES.get(self.category, self.category.title())

    @property
    def offset(self) -> str:
        return '' if '/' in self.folder else '  '

    @property
    def dictionary(self) -> str:
        return 'BASE' if '/' in self.folder else self.folder

    @property
    def file_source(self) -> str:
        return str(
            os.path.join(config.value('dictionaries', 'gamepath'),
                         self.folder, expansions.strings_source + '.package'))

    @property
    def file_dest(self) -> str:
        return str(os.path.join(config.value('dictionaries', 'gamepath'),
                                self.folder, expansions.strings_dest + '.package'))

    @property
    def exists_source(self) -> bool:
        return os.path.exists(self.file_source)

    @property
    def exists_dest(self) -> bool:
        return os.path.exists(self.file_dest)

    @property
    def exists_strings(self) -> bool:
        return self.exists_source and self.exists_dest

    @property
    def exists(self) -> bool:
        path = config.value('dictionaries', 'gamepath')
        if path:
            return os.path.exists(os.path.join(path, self.folder))
        return False


class Expansions:

    def __init__(self) -> None:
        self.__packs = None

    @property
    def items(self) -> List[Union[str, Expansion]]:
        return self.filtered_items()

    def filtered_items(self, filter_text: str = '', category_filter: str = 'all') -> List[Union[str, Expansion]]:
        baseexp = Expansion('BASE GAME', 'Data/Client', {'type': 'Base Game'})

        query = filter_text.strip().lower()
        category_filter = category_filter or 'all'
        rows = []
        if category_filter in ('all', 'base') and self._matches(baseexp, query):
            rows.append(baseexp)

        groups = {
            'expansion': ['', CATEGORY_TITLES['expansion']],
            'game': ['', CATEGORY_TITLES['game']],
            'stuff': ['', CATEGORY_TITLES['stuff']],
            'kit': ['', CATEGORY_TITLES['kit']],
            'free': ['', CATEGORY_TITLES['free']],
        }

        packs = self._parse_expansion_packs()

        if packs:
            for key, item in packs.items():
                expansion = Expansion(item.get('names', {}), key, item.get('metadata', {}))
                group = groups.get(expansion.category)
                if group is not None and self._matches(expansion, query) and self._matches_category(expansion, category_filter):
                    group.append(expansion)

        elif baseexp.exists_source:
            for dirname in os.listdir(config.value('dictionaries', 'gamepath')):
                expansion = Expansion(dirname, dirname)
                group = groups.get(expansion.category)
                if group is None or not self._matches(expansion, query) or not self._matches_category(expansion, category_filter):
                    continue
                if dirname.upper().startswith('EP'):
                    group.append(expansion)
                elif dirname.upper().startswith('GP'):
                    group.append(expansion)
                elif dirname.upper().startswith('SP'):
                    group.append(expansion)
                elif dirname.upper().startswith('FP'):
                    group.append(expansion)

        for key in ('expansion', 'game', 'stuff', 'kit', 'free'):
            group = groups[key]
            if len(group) > 2:
                rows.extend(group)

        return rows

    @staticmethod
    def _matches_category(expansion: Expansion, category_filter: str) -> bool:
        return category_filter == 'all' or expansion.category == category_filter

    @staticmethod
    def _matches(expansion: Expansion, query: str) -> bool:
        if not query:
            return True

        values = (
            expansion.folder,
            expansion.name,
            expansion.category_title,
            expansion.metadata.get('releasedate', ''),
        )
        return any(query in value.lower() for value in values)

    @staticmethod
    def summary(items: List[Union[str, Expansion]]) -> Dict[str, int]:
        packs = [item for item in items if isinstance(item, Expansion)]
        return {
            'total': len(packs),
            'found': sum(1 for item in packs if item.exists),
            'ready': sum(1 for item in packs if item.exists_strings),
            'missing': sum(1 for item in packs if not item.exists),
        }

    @property
    def strings_source(self) -> str:
        return 'Strings_' + config.value('translation', 'source')

    @property
    def strings_dest(self) -> str:
        return 'Strings_' + config.value('translation', 'destination')

    def exists(self) -> List[Expansion]:
        return [exp for exp in self.items if isinstance(exp, Expansion) and exp.exists_strings]

    def reset_cache(self) -> None:
        self.__packs = None
    
    def _parse_expansion_packs(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        if self.__packs is not None:
            return self.__packs

        self.__packs = {}

        try:
            with open('./prefs/dlc.ini', 'r', encoding='utf-8') as fp:
                content = fp.read()
        except FileNotFoundError:
            return {}

        current_pack = None

        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                pack_code = line[1:-1]
                current_pack = {'names': {}, 'metadata': {}}
                self.__packs[pack_code] = current_pack
            elif '=' in line and current_pack is not None:
                key, value = line.split('=', 1)
                key = key.lower().strip()
                if key.startswith('name_'):
                    current_pack['names'][key] = value.strip()
                else:
                    current_pack['metadata'][key] = value.strip()

        return self.__packs


expansions = Expansions()
