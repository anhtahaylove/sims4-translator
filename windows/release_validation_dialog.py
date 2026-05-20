# -*- coding: utf-8 -*-

from typing import Callable

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from utils.functions import text_to_table
from utils.release_validation import (
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    VALIDATION_CATEGORIES,
    ValidationIssue,
    ValidationReport,
)


ISSUE_COLUMNS = (
    'Severity',
    'Code',
    'Category',
    'Package',
    'Instance',
    'String ID',
    'Status',
    'Reason',
    'Original',
    'Translation',
)


class ReleaseIssueModel(QAbstractTableModel):

    def __init__(self, issues: tuple[ValidationIssue, ...], parent=None):
        super().__init__(parent)
        self.issues = issues

    def rowCount(self, _parent=QModelIndex()) -> int:
        return len(self.issues)

    def columnCount(self, _parent=QModelIndex()) -> int:
        return len(ISSUE_COLUMNS)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        issue = self.issues[index.row()]
        value = self.__value(issue, index.column())
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            return value
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return ISSUE_COLUMNS[section]
        return None

    def issue_at(self, row: int) -> ValidationIssue:
        return self.issues[row]

    @staticmethod
    def __value(issue: ValidationIssue, column: int) -> str:
        values = (
            issue.severity,
            issue.code,
            issue.category,
            issue.package,
            issue.instance,
            issue.string_id,
            issue.status,
            issue.reason,
            text_to_table(issue.original),
            text_to_table(issue.translation),
        )
        return values[column]


class ReleaseIssueFilterProxy(QSortFilterProxyModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.severity = 'All'
        self.category = 'All'
        self.query = ''

    def set_filters(self, severity: str, category: str, query: str) -> None:
        self.beginFilterChange()
        self.severity = severity or 'All'
        self.category = category or 'All'
        self.query = (query or '').strip().lower()
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        model = self.sourceModel()
        issue = model.issue_at(source_row)

        if self.severity != 'All' and issue.severity != self.severity:
            return False
        if self.category != 'All' and issue.category != self.category:
            return False
        if not self.query:
            return True

        searchable = ' '.join((
            issue.severity,
            issue.code,
            issue.category,
            issue.package,
            issue.instance,
            issue.string_id,
            issue.status,
            issue.reason,
            text_to_table(issue.original),
            text_to_table(issue.translation),
        )).lower()
        return self.query in searchable


class ReleaseValidationDialog(QDialog):

    __tab_severities = (SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_INFO, 'All')

    def __init__(self, report: ValidationReport, open_issue: Callable = None, parent=None):
        super().__init__(parent)
        self.report = report
        self.__open_issue = open_issue

        self.setWindowTitle('Pre-release Validation Report')
        self.setWindowIcon(QIcon(':/logo.ico'))
        self.setMinimumSize(1040, 660)
        self.resize(1280, 760)
        self.setModal(True)

        self.issue_model = ReleaseIssueModel(report.issues, self)
        self.issue_proxy = ReleaseIssueFilterProxy(self)
        self.issue_proxy.setSourceModel(self.issue_model)
        self.__setup_ui()
        self.__apply_filters()

    @classmethod
    def confirm(cls, parent, report: ValidationReport, open_issue: Callable = None) -> bool:
        dialog = cls(report, open_issue, parent)
        return dialog.exec() == QDialog.DialogCode.Accepted

    def __setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(self.__header())
        layout.addWidget(self.__filters())

        self.tabs = QTabWidget(self)
        self.tabs.setObjectName('releaseValidationTabs')
        for label, severity in (
                ('Critical', SEVERITY_CRITICAL),
                ('Warning', SEVERITY_WARNING),
                ('Info', SEVERITY_INFO),
                ('All', None),
        ):
            self.tabs.addTab(QWidget(self.tabs), f'{label} ({len(self.report.filtered(severity))})')
        self.tabs.currentChanged.connect(lambda _index: self.__apply_filters())
        layout.addWidget(self.tabs)

        self.issue_table = QTableView(self)
        self.issue_table.setObjectName('releaseValidationTable')
        self.issue_table.setModel(self.issue_proxy)
        self.issue_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.issue_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.issue_table.setSortingEnabled(True)
        self.issue_table.setAlternatingRowColors(True)
        self.issue_table.setWordWrap(False)
        self.issue_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.issue_table.verticalHeader().setVisible(False)
        self.__apply_review_table_layout()
        self.issue_table.doubleClicked.connect(self.__issue_double_clicked)
        layout.addWidget(self.issue_table, 1)

        self.result_count = QLabel(self)
        self.result_count.setObjectName('releaseValidationResultCount')
        layout.addWidget(self.result_count)

        layout.addLayout(self.__footer())

    def __header(self) -> QFrame:
        header = QFrame(self)
        header.setObjectName('releaseValidationHeader')
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(10)

        title = QLabel('Pre-release Validation Report', header)
        title.setObjectName('releaseValidationTitle')
        detail = QLabel(
            'Review potential blank-text and token issues before writing release files.',
            header,
        )
        detail.setObjectName('releaseValidationDetail')
        summary = QLabel(self.report.summary(), header)
        summary.setObjectName('releaseValidationSummary')

        cards = QGridLayout()
        cards.setContentsMargins(0, 0, 0, 0)
        cards.setHorizontalSpacing(8)
        cards.setVerticalSpacing(8)
        for index, (label, value) in enumerate((
                ('Critical', f'{self.report.critical_count:,}'),
                ('Warning', f'{self.report.warning_count:,}'),
                ('Info', f'{self.report.info_count:,}'),
                ('Records', f'{self.report.written_records:,}/{self.report.total_records:,}'),
                ('Packages', f'{self.report.package_count:,}'),
                ('STBL resources', f'{self.report.resource_count:,}'),
                ('Destination', self.report.destination_locale),
                ('Preset', self.report.profile.name),
        )):
            cards.addWidget(self.__summary_card(label, value, header), index // 4, index % 4)

        header_layout.addWidget(title)
        header_layout.addWidget(detail)
        header_layout.addWidget(summary)
        header_layout.addLayout(cards)
        return header

    @staticmethod
    def __summary_card(label: str, value: str, parent) -> QFrame:
        card = QFrame(parent)
        card.setObjectName('releaseValidationCard')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)
        card_label = QLabel(label, card)
        card_label.setObjectName('releaseValidationCardLabel')
        card_value = QLabel(value, card)
        card_value.setObjectName('releaseValidationCardValue')
        layout.addWidget(card_label)
        layout.addWidget(card_value)
        return card

    def __filters(self) -> QFrame:
        filters = QFrame(self)
        filters.setObjectName('releaseValidationFilters')
        layout = QHBoxLayout(filters)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        category_label = QLabel('Category', filters)
        self.category_filter = QComboBox(filters)
        self.category_filter.addItem('All')
        for category in VALIDATION_CATEGORIES:
            self.category_filter.addItem(category)
        self.category_filter.currentTextChanged.connect(lambda _text: self.__apply_filters())

        search_label = QLabel('Search', filters)
        self.search_filter = QLineEdit(filters)
        self.search_filter.setPlaceholderText('Search package, instance, ID, reason, original, or translation...')
        self.search_filter.textChanged.connect(lambda _text: self.__apply_filters())

        layout.addWidget(category_label)
        layout.addWidget(self.category_filter)
        layout.addSpacing(8)
        layout.addWidget(search_label)
        layout.addWidget(self.search_filter, 1)
        return filters

    def __footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(8)
        self.btn_export = QPushButton('Export report', self)
        self.btn_copy_issue = QPushButton('Copy selected issue', self)
        self.btn_copy_summary = QPushButton('Copy summary', self)
        self.btn_back = QPushButton('Back to Fix', self)
        self.btn_continue = QPushButton(
            'Continue anyway' if self.report.critical_count else 'Continue',
            self,
        )

        self.btn_export.clicked.connect(self.export_report)
        self.btn_copy_issue.clicked.connect(self.copy_selected_issue)
        self.btn_copy_summary.clicked.connect(self.copy_summary)
        self.btn_back.clicked.connect(self.reject)
        self.btn_continue.clicked.connect(self.accept)

        if self.report.critical_count:
            self.btn_back.setDefault(True)
            self.btn_back.setAutoDefault(True)
        else:
            self.btn_continue.setDefault(True)
            self.btn_continue.setAutoDefault(True)

        footer.addWidget(self.btn_export)
        footer.addWidget(self.btn_copy_issue)
        footer.addWidget(self.btn_copy_summary)
        footer.addStretch(1)
        footer.addWidget(self.btn_back)
        footer.addWidget(self.btn_continue)
        return footer

    def __apply_review_table_layout(self) -> None:
        header = self.issue_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        # Review view: metadata stays searchable/exportable, but the table prioritizes
        # what users need to fix: reason, affected record, and text previews.
        self.issue_table.setColumnHidden(1, True)  # Code
        self.issue_table.setColumnHidden(2, True)  # Category

        widths = {
            0: 90,   # Severity
            3: 210,  # Package
            4: 150,  # Instance
            5: 110,  # String ID
            6: 120,  # Status
            7: 460,  # Reason
            8: 360,  # Original
            9: 360,  # Translation
        }
        for column, width in widths.items():
            self.issue_table.setColumnWidth(column, width)

        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)

    def __current_severity(self) -> str:
        index = self.tabs.currentIndex()
        if index < 0 or index >= len(self.__tab_severities):
            return 'All'
        return self.__tab_severities[index]

    def __apply_filters(self) -> None:
        self.issue_proxy.set_filters(
            self.__current_severity(),
            self.category_filter.currentText() if hasattr(self, 'category_filter') else 'All',
            self.search_filter.text() if hasattr(self, 'search_filter') else '',
        )
        if hasattr(self, 'result_count'):
            self.result_count.setText(
                f'{self.issue_proxy.rowCount():,} issue(s) shown from {len(self.report.issues):,}.'
            )

    def __issue_double_clicked(self, proxy_index: QModelIndex) -> None:
        if not self.__open_issue or not proxy_index.isValid():
            return

        source_index = self.issue_proxy.mapToSource(proxy_index)
        issue = self.issue_model.issue_at(source_index.row())
        if issue.record is not None:
            self.__open_issue(issue.record)

    def copy_summary(self) -> None:
        QApplication.clipboard().setText(self.report.summary())

    def copy_selected_issue(self) -> None:
        issue = self.__selected_issue()
        if issue is None:
            return

        text = '\t'.join((
            issue.severity,
            issue.code,
            issue.category,
            issue.package,
            issue.instance,
            issue.string_id,
            issue.status,
            issue.reason,
            text_to_table(issue.original),
            text_to_table(issue.translation),
        ))
        QApplication.clipboard().setText(text)

    def __selected_issue(self) -> ValidationIssue | None:
        selection_model = self.issue_table.selectionModel()
        if selection_model is None:
            return None

        rows = selection_model.selectedRows()
        if not rows:
            current = self.issue_table.currentIndex()
            rows = [current] if current.isValid() else []
        if not rows:
            return None

        source_index = self.issue_proxy.mapToSource(rows[0])
        if not source_index.isValid():
            return None
        return self.issue_model.issue_at(source_index.row())

    def export_report(self) -> None:
        dialog = QFileDialog(self, 'Export Pre-release Validation Report')
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilters(('Text report (*.txt)', 'CSV report (*.csv)'))
        dialog.setDefaultSuffix('txt')

        if dialog.exec() != QFileDialog.DialogCode.Accepted:
            return

        path = dialog.selectedFiles()[0]
        selected_filter = dialog.selectedNameFilter()
        if path.lower().endswith('.csv') or selected_filter.startswith('CSV'):
            self.report.write_csv(path)
        else:
            self.report.write_text(path)
