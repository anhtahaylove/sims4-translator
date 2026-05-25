# -*- coding: utf-8 -*-

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
)

from widgets.comboboxes import NoWheelComboBox
from singletons.interface import interface


@dataclass(frozen=True)
class TokenCatalogItem:
    category: str
    label: str
    token: str
    hint: str = ''


TOKEN_SUFFIXES = (
    '',
    'capitalize',
    'enAn',
    'enHouseholdNamePlural',
    'xxAllCaps',
    'xxUpper',
)


TOKEN_CATALOG = (
    TokenCatalogItem('Names & Pronouns', 'Sim first name', 'SimFirstName'),
    TokenCatalogItem('Names & Pronouns', 'Sim last name', 'SimLastName'),
    TokenCatalogItem('Names & Pronouns', 'Sim full name', 'SimName'),
    TokenCatalogItem('Names & Pronouns', 'Subject pronoun', 'SimPronounSubjective', 'He/She'),
    TokenCatalogItem('Names & Pronouns', 'Object pronoun', 'SimPronounObjective', 'Him/Her'),
    TokenCatalogItem('Names & Pronouns', 'Possessive pronoun', 'SimPronounPossessiveDependent', 'His/Her'),
    TokenCatalogItem('Numbers & Money', 'Number', 'Number'),
    TokenCatalogItem('Numbers & Money', 'Money', 'Money'),
    TokenCatalogItem('Numbers & Money', 'Currency', 'Currency'),
    TokenCatalogItem('Numbers & Money', 'Decimal', 'Decimal'),
    TokenCatalogItem('Formatting', 'Line break', '\\n', 'Insert one escaped line break'),
    TokenCatalogItem('Formatting', 'Double line break', '\\n\\n', 'Insert two escaped line breaks'),
    TokenCatalogItem('Formatting', 'Bold tag pair', '<b></b>'),
    TokenCatalogItem('Formatting', 'Italic tag pair', '<i></i>'),
)


class TokenAssistantWidget(QFrame):

    insert_requested = Signal(str)
    copy_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('tokenAssistantPanel')
        self.__items = tuple(TOKEN_CATALOG)
        self.__setup_ui()
        self.retranslate()
        self.__refresh_tokens()
        self.__refresh_preview()

    def __setup_ui(self):
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(7)

        self.title = QLabel(self)
        self.title.setObjectName('sectionLabel')
        self.category = NoWheelComboBox(self)
        self.category.currentTextChanged.connect(self.__refresh_tokens)

        self.token = NoWheelComboBox(self)
        self.token.currentIndexChanged.connect(self.__refresh_preview)

        self.index = QSpinBox(self)
        self.index.setRange(0, 99)
        self.index.setValue(0)
        self.index.valueChanged.connect(self.__refresh_preview)

        self.suffix = NoWheelComboBox(self)
        self.suffix.addItems(('None',) + TOKEN_SUFFIXES[1:])
        self.suffix.currentIndexChanged.connect(self.__refresh_preview)

        self.male = QLineEdit(self)
        self.male.textChanged.connect(self.__refresh_preview)
        self.female = QLineEdit(self)
        self.female.textChanged.connect(self.__refresh_preview)

        self.preview = QLineEdit(self)
        self.preview.setObjectName('editResource')
        self.preview.setReadOnly(True)

        self.btn_insert = QPushButton(self)
        self.btn_insert.setObjectName('primaryButton')
        self.btn_copy = QPushButton(self)
        self.btn_copy.setObjectName('secondaryButton')
        self.btn_insert.clicked.connect(lambda _checked=False: self.insert_requested.emit(self.current_token()))
        self.btn_copy.clicked.connect(lambda _checked=False: self.copy_requested.emit(self.current_token()))

        layout.addWidget(self.title, 0, 0)
        self.category_label = QLabel(self)
        self.token_label = QLabel(self)
        self.index_label = QLabel(self)
        self.suffix_label = QLabel(self)
        self.pair_label = QLabel(self)

        layout.addWidget(self.category_label, 0, 1)
        layout.addWidget(self.category, 0, 2)
        layout.addWidget(self.token_label, 0, 3)
        layout.addWidget(self.token, 0, 4, 1, 2)
        layout.addWidget(self.index_label, 1, 0)
        layout.addWidget(self.index, 1, 1)
        layout.addWidget(self.suffix_label, 1, 2)
        layout.addWidget(self.suffix, 1, 3)
        layout.addWidget(self.preview, 1, 4, 1, 2)
        layout.addWidget(self.pair_label, 2, 0)
        layout.addWidget(self.male, 2, 1, 1, 2)
        layout.addWidget(self.female, 2, 3, 1, 2)
        layout.addWidget(self.btn_insert, 2, 5)
        layout.addWidget(self.btn_copy, 2, 6)
        layout.setColumnStretch(4, 1)

    def retranslate(self):
        current_category = self.category.currentData()
        self.title.setText(interface.text('TokenAssistant', 'Token Assistant'))
        self.category_label.setText(interface.text('TokenAssistant', 'Category'))
        self.token_label.setText(interface.text('TokenAssistant', 'Token'))
        self.index_label.setText(interface.text('TokenAssistant', 'Index'))
        self.suffix_label.setText(interface.text('TokenAssistant', 'Suffix'))
        self.pair_label.setText(interface.text('TokenAssistant', 'Male/Female pair'))
        self.male.setPlaceholderText(interface.text('TokenAssistant', 'Male text...'))
        self.female.setPlaceholderText(interface.text('TokenAssistant', 'Female text...'))
        self.btn_insert.setText(interface.text('TokenAssistant', 'Insert'))
        self.btn_copy.setText(interface.text('TokenAssistant', 'Copy'))

        self.category.blockSignals(True)
        self.category.clear()
        for category in tuple(dict.fromkeys(item.category for item in self.__items)):
            self.category.addItem(interface.text('TokenAssistant', category), category)
        if current_category:
            index = self.category.findData(current_category)
            if index >= 0:
                self.category.setCurrentIndex(index)
        self.category.blockSignals(False)
        self.__refresh_tokens()

    def __refresh_tokens(self):
        category = self.category.currentData() or self.category.currentText()
        self.token.blockSignals(True)
        self.token.clear()
        for item in self.__items:
            if item.category != category:
                continue
            label = interface.text('TokenAssistant', item.label)
            hint = interface.text('TokenAssistant', item.hint) if item.hint else ''
            label = label if not hint else f'{label} ({hint})'
            self.token.addItem(label, item)
        self.token.blockSignals(False)
        self.__refresh_preview()

    def __refresh_preview(self):
        self.preview.setText(self.current_token())

    def current_token(self) -> str:
        male = self.male.text().strip()
        female = self.female.text().strip()
        if male or female:
            return f'{{M{self.index.value()}.{male}}}{{F{self.index.value()}.{female}}}'

        item = self.token.currentData()
        if not item:
            return ''
        if item.category == 'Formatting':
            return item.token

        suffix = TOKEN_SUFFIXES[self.suffix.currentIndex()]
        suffix_part = f'|{suffix}' if suffix else ''
        return f'{{{self.index.value()}.{item.token}{suffix_part}}}'
