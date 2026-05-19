# Graph Report - C:\Users\VET\sims4-translator  (2026-05-19)

## Corpus Check
- Corpus is ~44,750 words - fits in a single context window. You may not need a graph.

## Summary
- 1024 nodes · 2102 edges · 32 communities detected
- Extraction: 49% EXTRACTED · 51% INFERRED · 0% AMBIGUOUS · INFERRED: 1070 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `MainWindow` - 69 edges
2. `ResourceID` - 62 edges
3. `CancellationToken` - 58 edges
4. `TaskReporter` - 57 edges
5. `PackagesStorage` - 53 edges
6. `DbpfPackage` - 44 edges
7. `Stbl` - 41 edges
8. `MainRecord` - 40 edges
9. `ExportDialog` - 38 edges
10. `Container` - 37 edges

## Surprising Connections (you probably didn't know these)
- `StorageSignals` --uses--> `Model`  [INFERRED]
  C:\Users\VET\sims4-translator\storages\packages.py → C:\Users\VET\sims4-translator\models\main.py
- `_NullReporter` --uses--> `Model`  [INFERRED]
  C:\Users\VET\sims4-translator\storages\packages.py → C:\Users\VET\sims4-translator\models\main.py
- `PackagesStorage` --uses--> `Model`  [INFERRED]
  C:\Users\VET\sims4-translator\storages\packages.py → C:\Users\VET\sims4-translator\models\main.py
- `StorageSignals` --uses--> `ProxyModel`  [INFERRED]
  C:\Users\VET\sims4-translator\storages\packages.py → C:\Users\VET\sims4-translator\models\main.py
- `_NullReporter` --uses--> `ProxyModel`  [INFERRED]
  C:\Users\VET\sims4-translator\storages\packages.py → C:\Users\VET\sims4-translator\models\main.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (77): Container, DbpfPackage, Exception, NamedTuple, _build_export_stbl(), _build_stbl(), _converted_resource(), DictionarySnapshot (+69 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (34): AbstractTableModel, AbstractTableModel, UpdateSignals, DictionariesStorage, DictionaryLoadRequest, DictionaryLoadResult, load_dictionaries_task(), _NullReporter (+26 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (16): ColumnAction, finalize(), finalize_as(), load(), load_bundle(), MainWindow, __packages_cleared(), __packages_closed() (+8 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (24): list, AbstractRecord, MainRecord, resource_for_occurrence(), NoopReporter, TranslationTaskTests, __error_translate_chunk(), __finished_translate_chunk() (+16 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (14): exists(), exists_dest(), exists_source(), Expansion, Expansions, items(), DelegatePaint, DictSignals (+6 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (14): check_binary(), check_json(), check_package(), check_stbl(), check_xml(), current_package(), __dictionary_snapshot(), PackagesStorage (+6 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (10): __export_records(), ExportDialog, Ui_ExportDialog, object, app(), Button, Checked, ExportDialogAsyncTests (+2 more)

### Community 7 - "Community 7"
Cohesion: 0.1
Nodes (14): __finished(), ProgressWidget, QColorBar, TranslatedWidget, UnvalidatedWidget, __update(), UpdateWorker, ValidatedWidget (+6 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (11): DictionaryDelegatePaint, GridPalette, HeaderProxy, MainDelegatePaint, __mix(), QProxyStyle, QStyledItemDelegate, QTableView (+3 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (7): DbpfLocator, _DbpfReader, _DbpfWriter, decode_ref_pack(), read(), write(), Resource

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (13): edit_translation_task(), EditDialog, EditTranslationRequest, EditTranslationResult, __translated(), __translation_error(), Ui_EditDialog, QDialog (+5 more)

### Community 11 - "Community 11"
Cohesion: 0.11
Nodes (3): at(), Packer, seek()

### Community 12 - "Community 12"
Cohesion: 0.1
Nodes (9): ImportDialog, ImportStats, Ui_ImportDialog, Checked, FakePackage, FakeStorage, FakeTableView, ImportDialogTests (+1 more)

### Community 13 - "Community 13"
Cohesion: 0.16
Nodes (23): RuntimeError, SyntheticSmokeVerifierTests, write_smoke_exports(), _assert_expected_ids(), configure_storage(), _destination_locales(), _export_files(), FakeDictionariesStorage (+15 more)

### Community 14 - "Community 14"
Cohesion: 0.1
Nodes (5): app(), DeduplicationTests, wait_for(), _chunks(), WorkspaceCache

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (9): CustomProxyStyle, QCleaningLineEdit, QCleaningLineEdit, QComboBox, QLineEdit, FilesComboBox, FixedLineEdit, InstancesComboBox (+1 more)

### Community 16 - "Community 16"
Cohesion: 0.13
Nodes (5): BracketHighlighter, LineNumberArea, QTextEditor, QPlainTextEdit, QSyntaxHighlighter

### Community 17 - "Community 17"
Cohesion: 0.09
Nodes (0):

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (14): compare(), fnv32(), fnv64(), _hash(), open_supported(), open_xml(), openfile(), save_binary() (+6 more)

### Community 19 - "Community 19"
Cohesion: 0.19
Nodes (5): app(), export_records(), export_request(), SyntheticPackageIntegrationTests, wait_for()

### Community 20 - "Community 20"
Cohesion: 0.26
Nodes (4): ConfigManager, __convert_to_str(), __convert_value(), theme_name()

### Community 21 - "Community 21"
Cohesion: 0.26
Nodes (2): Interface, Lang

### Community 22 - "Community 22"
Cohesion: 0.31
Nodes (6): __deepl(), extract_placeholders(), __google(), insert_placeholders(), __mymemory(), Translator

### Community 23 - "Community 23"
Cohesion: 0.31
Nodes (3): destination(), Languages, source()

### Community 24 - "Community 24"
Cohesion: 0.22
Nodes (1): AppState

### Community 25 - "Community 25"
Cohesion: 0.43
Nodes (4): configure_storage(), FakeDictionariesStorage, main(), validate_package()

### Community 26 - "Community 26"
Cohesion: 0.47
Nodes (3): build_stbl(), create_synthetic_package(), SyntheticPackageInfo

### Community 27 - "Community 27"
Cohesion: 0.5
Nodes (0): 

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (0): 

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **Thin community `Community 28`** (2 nodes): `stylesheet.py`, `stylesheet()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `dark.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `light.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `constants.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MainWindow` connect `Community 2` to `Community 3`, `Community 4`, `Community 6`, `Community 10`, `Community 12`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **Why does `PackagesStorage` connect `Community 5` to `Community 0`, `Community 1`, `Community 3`, `Community 13`, `Community 14`, `Community 19`, `Community 25`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Why does `MainRecord` connect `Community 3` to `Community 0`, `Community 4`, `Community 5`, `Community 6`, `Community 12`, `Community 17`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `MainWindow` (e.g. with `Ui_MainWindow` and `EditDialog`) actually correct?**
  _`MainWindow` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 58 inferred relationships involving `ResourceID` (e.g. with `DbpfLocator` and `_DbpfReader`) actually correct?**
  _`ResourceID` has 58 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `CancellationToken` (e.g. with `.start()` and `StorageSignals`) actually correct?**
  _`CancellationToken` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `TaskReporter` (e.g. with `.run()` and `StorageSignals`) actually correct?**
  _`TaskReporter` has 54 INFERRED edges - model-reasoned connections that need verification._
