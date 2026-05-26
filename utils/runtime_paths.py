# -*- coding: utf-8 -*-

import sys
from pathlib import Path


def resource_base_path() -> Path:
    frozen_base = getattr(sys, '_MEIPASS', None)
    if frozen_base:
        return Path(frozen_base)
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def resource_path(*parts: str) -> Path:
    return resource_base_path().joinpath(*parts)
