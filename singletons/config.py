# -*- coding: utf-8 -*-

import os
import ctypes
import ctypes.wintypes
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom
from copy import deepcopy
from pathlib import Path
from typing import Union

from utils.constants import *


CONFIG_DIR_ENV = 'SIMS4_TRANSLATOR_CONFIG_DIR'
CONFIG_FILE_NAME = 'config.xml'


def is_dark_theme():
    registry = ctypes.windll.advapi32
    hkey_current_user = 0x80000001
    sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize'
    value_name = 'AppsUseLightTheme'

    hkey = ctypes.wintypes.HKEY()
    result = registry.RegOpenKeyExW(hkey_current_user, sub_key, 0, 0x20019, ctypes.byref(hkey))

    if result != 0:
        return False

    value = ctypes.wintypes.DWORD()
    value_length = ctypes.wintypes.DWORD(ctypes.sizeof(value))
    result = registry.RegQueryValueExW(hkey, value_name, 0, None, ctypes.byref(value), ctypes.byref(value_length))
    registry.RegCloseKey(hkey)

    if result != 0:
        return False

    return value.value == 0


class ConfigManager:

    DEFAULTS = {
        'interface': {
            'language': 'en_US',
            'theme': 'balanced'
        },
        'dictionaries': {
            'gamepath': '',
            'dictpath': '',
            'strong': False
        },
        'save': {
            'backup': True,
            'experemental': False
        },
        'group': {
            'original': True,
            'highbit': False,
            'lowbit': False
        },
        'template': {
            'conflict': '1_{name}_{lang_d}',
            'non_conflict': 'z_{name}_{lang_d}'
        },
        'translation': {
            'source': 'ENG_US',
            'destination': 'VI_VN'
        },
        'migrations': {
            'translation_default_vi_vn': False,
            'translation_release_config_1_4_2': False
        },
        'api': {
            'engine': '',
            'deepl_key': '',
            'deepl_glossary_id': ''
        },
        'view': {
            'id': True,
            'instance': False,
            'group': False,
            'source': True,
            'comment': False,
            'colorbar': False,
            'activity_visible': True,
            'activity_expanded': True,
            'row_density': 'comfortable',
            'numeration': NUMERATION_STANDART
        },
        'temporary': {
            'directory': os.path.abspath(os.path.expanduser('~/Documents'))
        }
    }

    def __init__(self) -> None:
        self.__config_file = self.__resolve_config_file()
        self.__legacy_config_file = Path('prefs') / CONFIG_FILE_NAME
        self.__config = deepcopy(self.DEFAULTS)
        self.__load()

    def __load(self) -> None:
        loaded = False
        loaded_from_legacy = False
        for path in (self.__config_file, self.__legacy_config_file):
            try:
                self.__update_defaults_from_file(path)
                loaded = True
                loaded_from_legacy = path == self.__legacy_config_file
                break
            except FileNotFoundError:
                continue
            except ElementTree.ParseError:
                if path == self.__config_file:
                    break
                continue

        if not loaded:
            self.save()
        if self.__normalize_translation_defaults() or loaded_from_legacy:
            self.save()

    def save(self) -> None:
        root = ElementTree.Element('config')
        for section, options in self.__config.items():
            section_element = ElementTree.SubElement(root, section)
            for option, value in options.items():
                option_element = ElementTree.SubElement(section_element, option)
                option_element.text = self.__convert_to_str(value)

        rough = ElementTree.tostring(root, encoding='utf-8').decode('utf-8')
        reparsed = minidom.parseString(rough)
        prettyxml = reparsed.toprettyxml(indent='  ', encoding='utf-8')

        self.__config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.__config_file, 'wb') as fp:
            fp.write(prettyxml)

    def value(self, section: str, option: str) -> Union[str, int, bool, None]:
        return self.__config.get(section, {}).get(option)

    def set_value(self, section: str, option: str, value: Union[str, int, bool]) -> None:
        if section not in self.__config:
            self.__config[section] = {}
        self.__config[section][option] = value

    @property
    def config_file(self) -> str:
        return str(self.__config_file)

    @classmethod
    def default_config_dir(cls) -> Path:
        override = os.environ.get(CONFIG_DIR_ENV)
        if override:
            return Path(override)

        appdata = os.environ.get('APPDATA')
        if appdata:
            return Path(appdata) / APP_NAME

        return Path.home() / '.config' / APP_NAME

    @classmethod
    def __resolve_config_file(cls) -> Path:
        return cls.default_config_dir() / CONFIG_FILE_NAME

    def __update_defaults_from_file(self, path: Path) -> None:
        tree = ElementTree.parse(path)
        root = tree.getroot()
        for section in root:
            section_name = section.tag
            for option in section:
                option_name = option.tag
                option_value = self.__convert_value(option.text)
                if section_name not in self.__config:
                    self.__config[section_name] = {}
                self.__config[section_name][option_name] = option_value

    def __normalize_translation_defaults(self) -> bool:
        changed = False
        migrated = self.value('migrations', 'translation_default_vi_vn')

        if not migrated:
            if self.value('translation', 'source') == 'ENG_US' and self.value('translation', 'destination') == 'FRE_FR':
                self.set_value('translation', 'destination', 'VI_VN')
            self.set_value('migrations', 'translation_default_vi_vn', True)
            changed = True

        # v1.4.1 release builds accidentally bundled the maintainer's local
        # prefs/config.xml with ENG_US -> FRE_FR. Repair that release artifact
        # once, even if the earlier default migration marker was already set.
        release_config_migrated = self.value('migrations', 'translation_release_config_1_4_2')
        if not release_config_migrated:
            if self.value('translation', 'source') == 'ENG_US' and self.value('translation', 'destination') == 'FRE_FR':
                self.set_value('translation', 'destination', 'VI_VN')
            self.set_value('migrations', 'translation_release_config_1_4_2', True)
            changed = True

        return changed

    @staticmethod
    def __convert_value(value: str) -> Union[str, int, bool, None]:
        if value is None:
            return ''
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        try:
            return int(value)
        except ValueError:
            return value
    
    @staticmethod
    def __convert_to_str(value: Union[str, int, bool]) -> str:
        if isinstance(value, bool):
            return 'true' if value else 'false'
        return str(value)

    @property
    def theme_name(self):
        name = self.value('interface', 'theme')
        if name != 'balanced':
            self.set_value('interface', 'theme', 'balanced')
        return 'life'

    def is_dark_theme(self):
        return True


config = ConfigManager()
