# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QComboBox

from singletons.config import config
from singletons.translator import translator


def refresh_engine_combo(combo: QComboBox, preferred_engine: str = None) -> str:
    engine = preferred_engine if preferred_engine is not None else config.value('api', 'engine')
    current = engine or combo.currentText()

    combo.blockSignals(True)
    combo.clear()
    combo.addItems(translator.engines)
    engine_index = combo.findText(current)
    combo.setCurrentIndex(engine_index if engine_index >= 0 else 0)
    combo.blockSignals(False)

    return combo.currentText()
