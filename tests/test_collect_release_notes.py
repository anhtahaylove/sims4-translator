# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from scripts.collect_release_notes import (
    ReleaseNotesError,
    collect_changesets,
    render_changelog_section,
    render_github_release_notes,
    update_changelog,
)


class CollectReleaseNotesTests(unittest.TestCase):

    def _write_changeset(self, root: Path, name: str, text: str) -> Path:
        changes = root / 'changes'
        changes.mkdir(parents=True, exist_ok=True)
        path = changes / name
        path.write_text(text, encoding='utf-8')
        return path

    def test_collects_multiple_changesets_for_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_changeset(
                root,
                'v2.2.19-release-notes.md',
                'Version: 2.2.19\nCategory: Build\n\n- Generate release notes from committed changesets.\n',
            )
            self._write_changeset(
                root,
                'v2.2.19-docs.md',
                'Version: 2.2.19\nCategory: Docs\n\n- Document the release-note workflow.\n',
            )

            changesets = collect_changesets('2.2.19', root)

        self.assertEqual([changeset.category for changeset in changesets], ['Docs', 'Build'])

    def test_missing_changeset_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ReleaseNotesError, 'No changesets found'):
                collect_changesets('2.2.19', Path(tmp))

    def test_invalid_category_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_changeset(
                root,
                'v2.2.19-bad.md',
                'Version: 2.2.19\nCategory: Misc\n\n- This should fail.\n',
            )

            with self.assertRaisesRegex(ReleaseNotesError, 'invalid Category'):
                collect_changesets('2.2.19', root)

    def test_empty_body_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_changeset(root, 'v2.2.19-empty.md', 'Version: 2.2.19\nCategory: Fixed\n\n')

            with self.assertRaisesRegex(ReleaseNotesError, 'at least one'):
                collect_changesets('2.2.19', root)

    def test_rendered_markdown_groups_categories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_changeset(
                root,
                'v2.2.19-build.md',
                'Version: 2.2.19\nCategory: Build\n\n- Generate release notes from changesets.\n',
            )
            changesets = collect_changesets('2.2.19', root)

        section = render_changelog_section('2.2.19', changesets, '2026-05-27')

        self.assertIn('## Version 2.2.19 - 2026-05-27', section)
        self.assertIn('### Build', section)
        self.assertIn('- Generate release notes from changesets.', section)

    def test_github_release_notes_keep_trust_verification_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_changeset(
                root,
                'v2.2.19-build.md',
                'Version: 2.2.19\nCategory: Build\n\n- Generate release notes from changesets.\n',
            )
            changesets = collect_changesets('2.2.19', root)

        notes = render_github_release_notes('2.2.19', changesets, 'owner/repo')

        self.assertIn('Why this release exists:', notes)
        self.assertIn('Why two JSON-looking files?', notes)
        self.assertIn('gh release verify v2.2.19 --repo owner/repo', notes)
        self.assertIn('gh attestation verify .\\The-Sims-4-Translator-Plus-v2.2.19-windows.zip', notes)
        self.assertIn('cosign verify-blob', notes)
        self.assertIn('not duplicates', notes)

    def test_update_changelog_replaces_existing_version_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / 'CHANGELOG.md'
            changelog.write_text(
                '# Changelog\n\n## Version 2.2.19 - 2026-05-27\n\n- Old note.\n\n## Version 2.2.18 - 2026-05-27\n\n- Previous.\n',
                encoding='utf-8',
            )

            update_changelog(changelog, '## Version 2.2.19 - 2026-05-27\n\n### Build\n\n- New note.\n', '2.2.19')
            text = changelog.read_text(encoding='utf-8')

        self.assertIn('- New note.', text)
        self.assertNotIn('- Old note.', text)
        self.assertIn('## Version 2.2.18 - 2026-05-27', text)


if __name__ == '__main__':
    unittest.main()
