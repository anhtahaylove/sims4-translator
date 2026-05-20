# -*- coding: utf-8 -*-

import os
import ctypes
import ctypes.wintypes
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom
from copy import deepcopy
from typing import Union

from utils.constants import *


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
            'translation_default_vi_vn': False
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
        self.__config_file = './prefs/config.xml'
        self.__config = deepcopy(self.DEFAULTS)
        self.__load()

    def __load(self) -> None:
        try:
            self.__update_defaults_from_file()
        except (ElementTree.ParseError, FileNotFoundError) as e:
            self.save()
        if self.__normalize_translation_defaults():
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

        with open(self.__config_file, 'wb') as fp:
            fp.write(prettyxml)

    def value(self, section: str, option: str) -> Union[str, int, bool, None]:
        return self.__config.get(section, {}).get(option)

    def set_value(self, section: str, option: str, value: Union[str, int, bool]) -> None:
        if section not in self.__config:
            self.__config[section] = {}
        self.__config[section][option] = value

    def __update_defaults_from_file(self) -> None:
        tree = ElementTree.parse(self.__config_file)
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
        migrated = self.value('migrations', 'translation_default_vi_vn')
        if migrated:
            return False

        if self.value('translation', 'source') == 'ENG_US' and self.value('translation', 'destination') == 'FRE_FR':
            self.set_value('translation', 'destination', 'VI_VN')

        self.set_value('migrations', 'translation_default_vi_vn', True)
        return True

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
