# -*- coding: utf-8 -*-

"""Render localized UI surfaces and scan for obvious layout clipping.

This is a release QA helper, not a pixel-perfect visual regression tool. It
uses synthetic app state so it can run in CI/offscreen without real packages.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('SIMS4_TRANSLATOR_CONFIG_DIR', str(ROOT / 'build' / 'i18n-visual-qa' / 'config'))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QAbstractButton,
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QTabBar,
    QWidget,
)

import resource_rc  # noqa: F401, E402
from packer.resource import ResourceID  # noqa: E402
from singletons.config import config  # noqa: E402
from singletons.interface import Lang, interface  # noqa: E402
from singletons.state import app_state  # noqa: E402
from storages.dictionaries import DictionariesStorage  # noqa: E402
from storages.packages import PackagesStorage  # noqa: E402
from storages.records import MainRecord  # noqa: E402
from utils.constants import (  # noqa: E402
    APP_VERSION,
    FLAG_PROGRESS,
    FLAG_REPLACED,
    FLAG_TRANSLATED,
    FLAG_UNVALIDATED,
    FLAG_VALIDATED,
)
from utils.release_validation import (  # noqa: E402
    PROFILE_SOFT,
    ValidationIssue,
    ValidationReport,
    validate_release_records,
)
from windows.edit_dialog import EditDialog  # noqa: E402
from windows.main_window import MainWindow  # noqa: E402
from windows.options_dialog import OptionsDialog  # noqa: E402
from windows.release_validation_dialog import ReleaseValidationDialog  # noqa: E402
from windows.translate_dialog import TranslateDialog  # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass


DEFAULT_LANGUAGES = ('english', 'german', 'russian', 'ukrainian', 'brasil', 'chinese', 'vietnamese')
PROTECTED_TERMS = (
    'Ctrl+Enter',
    'Ctrl+Shift+Enter',
    'DeepL',
    'Gemini',
    'OpenAI-compatible',
    'Ollama',
    'Validate Release',
    'Save as package',
    'The Sims 4',
    'API',
    'URL',
    'JSON',
    'XML',
    'STBL',
    'ZIP',
    'token',
    'tokens',
    'package',
    'packages',
)
PROTECTED_PATTERN = re.compile(
    r'(\{[^{}]*\}|https?://\S+|Ctrl(?:\+Shift)?\+[A-Za-z0-9]+|\\n|\\r|\\x0a|\\x0d)'
)
WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")


@dataclass(frozen=True)
class LayoutIssue:
    window: str
    widget_class: str
    object_name: str
    text: str
    reason: str
    size: str
    hint: str


class VisualPackageStub:
    key = '[f803547f] visual_i18n_qa.package'
    name = 'visual_i18n_qa'
    filename = '[f803547f] visual_i18n_qa.package'
    instances = ['0x8000000000000001']
    modified = False

    def __len__(self):
        return 24

    def modify(self, state=True):
        self.modified = state

    def save(self):
        self.modified = False

    def finalize(self, path=None):
        self.modified = False


def app() -> QApplication:
    instance = QApplication.instance() or QApplication([])
    instance.setQuitOnLastWindowClosed(False)
    return instance


def qa_output_dir(version: str = APP_VERSION, language: str = '') -> Path:
    path = ROOT / 'build' / 'i18n-visual-qa' / f'v{version}'
    return path / language if language else path


def interface_file_map() -> dict[str, tuple[str, str]]:
    mapping = {}
    for path in sorted((ROOT / 'prefs' / 'interface').glob('*.xml')):
        root = ElementTree.parse(path).getroot()
        code = root.get('language') or path.stem
        mapping[path.stem] = (code, path.stem)
        mapping[code] = (code, path.stem)
    return mapping


def pseudo_localize_text(text: str, expansion: float = 0.4) -> str:
    if not text:
        return text

    protected: list[str] = []

    def protect(value: str) -> str:
        protected.append(value)
        return f'@@P{len(protected) - 1}@@'

    result = PROTECTED_PATTERN.sub(lambda match: protect(match.group(0)), text)
    for term in sorted(PROTECTED_TERMS, key=len, reverse=True):
        result = re.sub(re.escape(term), lambda match: protect(match.group(0)), result)

    def expand(match: re.Match[str]) -> str:
        word = match.group(0)
        extra = max(1, int(math.ceil(len(word) * expansion)))
        return word + (word[-1] * min(extra, 8))

    result = WORD_PATTERN.sub(expand, result)
    for index, value in enumerate(protected):
        result = result.replace(f'@@P{index}@@', value)
    return f'[[{result}]]'


def build_pseudo_catalog(english_path: Path | None = None) -> dict[str, dict[str, str]]:
    english_path = english_path or ROOT / 'prefs' / 'interface' / 'english.xml'
    root = ElementTree.parse(english_path).getroot()
    items: dict[str, dict[str, str]] = {}
    for context in root.findall('context'):
        context_name = context.get('name')
        if not context_name:
            continue
        context_items = {}
        for entry in context.findall('string'):
            source = entry.findtext('source') or ''
            context_items[source] = pseudo_localize_text(source)
        items[context_name] = context_items
    return items


@contextmanager
def active_interface(language: str):
    previous_language = config.value('interface', 'language')
    previous_current = getattr(interface, '_Interface__current', None)
    if language == 'pseudo':
        setattr(
            interface,
            '_Interface__current',
            Lang('pseudo', 'Pseudo Layout Stress', build_pseudo_catalog(), 'Visual QA', APP_VERSION),
        )
    else:
        aliases = interface_file_map()
        code, _stem = aliases.get(language, (language, language))
        config.set_value('interface', 'language', code)
        interface.reload()
    try:
        yield
    finally:
        config.set_value('interface', 'language', previous_language)
        if language == 'pseudo':
            setattr(interface, '_Interface__current', previous_current)
        else:
            interface.reload()


def make_records(count: int = 24) -> list[MainRecord]:
    records = []
    flags = (FLAG_UNVALIDATED, FLAG_PROGRESS, FLAG_VALIDATED, FLAG_TRANSLATED, FLAG_REPLACED)
    for index in range(1, count + 1):
        rid = ResourceID(group=0, instance=0x8000000000000001, type=0x220557DA)
        if index % 3 == 0:
            source = (
                'Package-heavy string with tokens {0.SimPronounSubjective} {1.SimFirstName} and repeated QA text. '
                'This row is intentionally long enough to check table, Selection Preview, Editor, token highlight, '
                'and validation report wrapping.'
            )
        elif index % 3 == 1:
            source = (
                'Dialog line with XML-like <font color="#1E8E16">{0.Number}</font> and escaped line break\\n'
                'Next paragraph. QA row keeps placeholders visible.'
            )
        else:
            source = (
                'Career notification: {0.SimFirstName} finished a task, gained {2.Number}, and unlocked '
                '<i>new advice</i>.'
            )
        translation = source if index % 5 else ''
        records.append(MainRecord(
            index,
            index,
            rid.instance,
            rid.group,
            source,
            translation,
            flags[index % len(flags)],
            rid,
            rid,
            VisualPackageStub.key,
            source if index % 7 == 0 else None,
            translation if index % 6 == 0 else None,
            (index, index, index, index),
            'Visual QA synthetic row',
        ))
    return records


def configure_synthetic_workspace() -> list[MainRecord]:
    records = make_records()
    storage = PackagesStorage()
    storage.packages.append(VisualPackageStub())
    storage.model.append(records)
    storage.model.filter(list(records))
    app_state.set_packages_storage(storage)
    app_state.set_dictionaries_storage(DictionariesStorage())
    app_state.set_current_package(None)
    app_state.set_current_instance(0)
    config.set_value('translation', 'source', 'ENG_US')
    config.set_value('translation', 'destination', 'VI_VN')
    config.set_value('api', 'deepl_key', 'visual-qa-key')
    config.set_value('api', 'gemini_key', 'visual-qa-key')
    config.set_value('api', 'gemini_model', 'gemini-2.5-flash')
    config.set_value('api', 'openai_key', 'visual-qa-key')
    config.set_value('api', 'openai_base_url', 'https://api.openai.com')
    config.set_value('api', 'openai_model', 'gpt-4o-mini')
    config.set_value('api', 'ollama_enabled', True)
    config.set_value('api', 'ollama_base_url', 'http://localhost:11434')
    config.set_value('api', 'ollama_model', 'translategemma:12b')
    return list(records)


@contextmanager
def options_without_network_refresh():
    original = OptionsDialog.refresh_ollama_models
    OptionsDialog.refresh_ollama_models = lambda self: None
    try:
        yield
    finally:
        OptionsDialog.refresh_ollama_models = original


def validation_report(records: Iterable[MainRecord]) -> ValidationReport:
    report = validate_release_records(
        records,
        mode='Validate Release',
        destination_locale='VI_VN',
        include_untranslated=True,
        conflict_free=False,
        profile=PROFILE_SOFT,
    )
    if report.issues:
        return report
    return ValidationReport(
        mode='Validate Release',
        profile=PROFILE_SOFT,
        destination_locale='VI_VN',
        include_untranslated=True,
        conflict_free=False,
        total_records=len(tuple(records)),
        written_records=len(tuple(records)),
        package_count=1,
        resource_count=1,
        status_counts=(('Untranslated', 1),),
        issues=(ValidationIssue(
            severity='Warning',
            code='VISUAL_QA',
            category='Length / layout risk',
            package=VisualPackageStub.key,
            instance='0x8000000000000001',
            string_id='0x00000001',
            status='Needs review',
            reason='Synthetic visual QA issue with deliberately long text.',
            original='Original visual QA text {0.SimFirstName}',
            translation='Translated visual QA text {0.SimFirstName}',
        ),),
    )


def render_scenes(language: str) -> list[tuple[str, QWidget]]:
    records = configure_synthetic_workspace()
    widgets: list[tuple[str, QWidget]] = []

    window = MainWindow()
    window.resize(1365, 768)
    window.show()
    app().processEvents()
    app_state.packages_storage.signals.loaded.emit([VisualPackageStub.key])
    window.update_proxy()
    window.tableview.selectRow(0)
    window.update_inspector_item(records[0])
    app().processEvents()
    widgets.append(('main-window', window))

    with options_without_network_refresh():
        options = OptionsDialog(window)
    options.tabs.setCurrentWidget(options.tab_providers)
    options.resize(840, 680)
    options.show()
    app().processEvents()
    widgets.append(('options-providers', options))

    translate = TranslateDialog(window)
    translate.resize(640, 560)
    translate.show()
    app().processEvents()
    widgets.append(('batch-translate', translate))

    edit = EditDialog(window)
    edit.prepare(records[2])
    edit.resize(1280, 820)
    edit.show()
    app().processEvents()
    widgets.append(('translation-studio', edit))

    release = ReleaseValidationDialog(validation_report(records), parent=window)
    release.resize(1280, 760)
    release.show()
    app().processEvents()
    widgets.append(('release-qa', release))

    return widgets


def widget_label(widget: QWidget) -> str:
    if isinstance(widget, QTabBar):
        return ' | '.join(widget.tabText(index) for index in range(widget.count()))
    if isinstance(widget, QComboBox):
        return widget.currentText()
    for attr in ('text', 'title', 'placeholderText'):
        method = getattr(widget, attr, None)
        if callable(method):
            try:
                return method() or ''
            except TypeError:
                return ''
    return ''


def _scan_text_widget(window_name: str, widget: QWidget) -> LayoutIssue | None:
    if not widget.isVisible() or widget.width() <= 0 or widget.height() <= 0:
        return None
    if isinstance(widget, QLabel) and widget.wordWrap():
        return None
    if isinstance(widget, QLineEdit):
        return None
    if isinstance(widget, (QAbstractButton, QCheckBox, QRadioButton, QGroupBox, QComboBox, QTabBar, QLabel)):
        text = widget_label(widget).strip()
    else:
        return None
    if not text:
        return None

    hint = widget.sizeHint()
    minimum_hint = widget.minimumSizeHint()
    width_slack = max(48, int(widget.width() * 0.45))
    if hint.width() > widget.width() + width_slack and len(text) > 18:
        return LayoutIssue(
            window=window_name,
            widget_class=widget.__class__.__name__,
            object_name=widget.objectName(),
            text=text[:160],
            reason='text width is much larger than the rendered widget',
            size=f'{widget.width()}x{widget.height()}',
            hint=f'{hint.width()}x{hint.height()}',
        )
    if minimum_hint.height() > widget.height() + 8 and len(text) > 8:
        return LayoutIssue(
            window=window_name,
            widget_class=widget.__class__.__name__,
            object_name=widget.objectName(),
            text=text[:160],
            reason='minimum height is larger than the rendered widget',
            size=f'{widget.width()}x{widget.height()}',
            hint=f'{minimum_hint.width()}x{minimum_hint.height()}',
        )
    return None


def scan_widget_layout(window_name: str, root: QWidget) -> list[LayoutIssue]:
    root.layout().activate() if root.layout() else None
    app().processEvents()
    issues = []
    for widget in (root, *root.findChildren(QWidget)):
        if widget is not root and widget.window() is not root:
            continue
        issue = _scan_text_widget(window_name, widget)
        if issue:
            issues.append(issue)
    return issues


def close_widgets(widgets: Iterable[tuple[str, QWidget]]) -> None:
    for _name, widget in reversed(tuple(widgets)):
        widget.close()
        widget.deleteLater()
    app().processEvents()


def run_language(language: str, version: str, screenshots: bool, strict_layout: bool) -> list[LayoutIssue]:
    with active_interface(language):
        widgets = render_scenes(language)
        try:
            language_dir = qa_output_dir(version, language)
            if screenshots:
                language_dir.mkdir(parents=True, exist_ok=True)
            issues = []
            for scene_name, widget in widgets:
                if screenshots:
                    widget.grab().save(str(language_dir / f'{scene_name}.png'))
                if strict_layout:
                    issues.extend(scan_widget_layout(scene_name, widget))
            if screenshots or issues:
                language_dir.mkdir(parents=True, exist_ok=True)
                with open(language_dir / 'layout-report.json', 'w', encoding='utf-8') as fp:
                    json.dump([asdict(issue) for issue in issues], fp, indent=2, ensure_ascii=False)
            return issues
        finally:
            close_widgets(widgets)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Render localized UI smoke scenes and scan for obvious layout issues.')
    parser.add_argument('--languages', nargs='*', default=list(DEFAULT_LANGUAGES), help='Interface XML stems or language codes.')
    parser.add_argument('--pseudo', action='store_true', help='Run pseudo-localization stress mode.')
    parser.add_argument('--version', default=APP_VERSION, help='Version folder under build/i18n-visual-qa.')
    parser.add_argument('--strict-layout', action='store_true', help='Fail when obvious layout clipping is detected.')
    screenshots = parser.add_mutually_exclusive_group()
    screenshots.add_argument('--screenshots', action='store_true', help='Save screenshots under build/i18n-visual-qa.')
    screenshots.add_argument('--no-screenshots', action='store_true', help='Do not save screenshots.')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    app()
    languages = ['pseudo'] if args.pseudo else args.languages
    screenshots = bool(args.screenshots)
    all_issues = []
    for language in languages:
        print(f'==> Visual i18n smoke: {language}')
        issues = run_language(language, args.version, screenshots, args.strict_layout)
        all_issues.extend(issues)
        print(f'{language}: {len(issues)} layout issue(s)')

    if all_issues:
        for issue in all_issues:
            print(
                f'{issue.window}: {issue.widget_class} {issue.object_name or "<unnamed>"} '
                f'[{issue.size}, hint {issue.hint}] {issue.reason}: {issue.text}'
            )
        return 1 if args.strict_layout else 0
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
