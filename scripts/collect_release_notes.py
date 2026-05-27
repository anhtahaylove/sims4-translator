# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import datetime as _dt
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / 'CHANGELOG.md'
CHANGES_DIR = ROOT / 'changes'
ALLOWED_CATEGORIES = ('Added', 'Changed', 'Fixed', 'Security', 'Docs', 'Build')
VERSION_PATTERN = re.compile(r'^\d+\.\d+\.\d+$')


class ReleaseNotesError(RuntimeError):
    pass


@dataclass(frozen=True)
class Changeset:
    path: Path
    version: str
    category: str
    bullets: tuple[str, ...]


def _relative(path: Path, root: Path = ROOT) -> str:
    try:
        return str(path.relative_to(root)).replace('\\', '/')
    except ValueError:
        return str(path)


def _parse_header(line: str, key: str, path: Path) -> str:
    prefix = f'{key}:'
    if not line.startswith(prefix):
        raise ReleaseNotesError(f'{_relative(path)} line must start with "{prefix}"')
    value = line[len(prefix):].strip()
    if not value:
        raise ReleaseNotesError(f'{_relative(path)} has an empty {key} value')
    return value


def parse_changeset(path: Path, root: Path = ROOT) -> Changeset:
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    if len(lines) < 3:
        raise ReleaseNotesError(f'{_relative(path, root)} is too short')

    version = _parse_header(lines[0], 'Version', path)
    category = _parse_header(lines[1], 'Category', path)
    if lines[2].strip():
        raise ReleaseNotesError(f'{_relative(path, root)} must have a blank line after Category')
    if not VERSION_PATTERN.match(version):
        raise ReleaseNotesError(f'{_relative(path, root)} has invalid Version {version!r}')
    if category not in ALLOWED_CATEGORIES:
        allowed = ', '.join(ALLOWED_CATEGORIES)
        raise ReleaseNotesError(f'{_relative(path, root)} has invalid Category {category!r}; use one of: {allowed}')

    bullets = tuple(line.strip() for line in lines[3:] if line.strip())
    if not bullets:
        raise ReleaseNotesError(f'{_relative(path, root)} must include at least one release-note bullet')
    for bullet in bullets:
        if not bullet.startswith('- '):
            raise ReleaseNotesError(f'{_relative(path, root)} release-note lines must be Markdown bullets')

    return Changeset(path=path, version=version, category=category, bullets=bullets)


def _candidate_paths(version: str, root: Path = ROOT) -> list[Path]:
    changes = root / 'changes'
    paths = []
    if changes.exists():
        paths.extend(sorted(changes.glob('*.md')))
        paths.extend(sorted((changes / 'archive' / f'v{version}').glob('*.md')))
    return paths


def collect_changesets(version: str, root: Path = ROOT) -> list[Changeset]:
    if not VERSION_PATTERN.match(version):
        raise ReleaseNotesError(f'Release version must be X.Y.Z, got {version!r}')

    seen_names: dict[str, Path] = {}
    matches: list[Changeset] = []
    for path in _candidate_paths(version, root):
        if path.name in seen_names:
            first = _relative(seen_names[path.name], root)
            second = _relative(path, root)
            raise ReleaseNotesError(f'Duplicate changeset filename {path.name!r}: {first} and {second}')
        seen_names[path.name] = path

        changeset = parse_changeset(path, root)
        if changeset.version == version:
            matches.append(changeset)

    if not matches:
        raise ReleaseNotesError(
            f'No changesets found for {version}. Add changes/v{version}-short-reason.md before releasing.'
        )
    return matches


def grouped_bullets(changesets: list[Changeset]) -> dict[str, list[str]]:
    grouped = {category: [] for category in ALLOWED_CATEGORIES}
    seen_bullets: dict[str, Path] = {}
    for changeset in changesets:
        for bullet in changeset.bullets:
            if bullet in seen_bullets:
                first = _relative(seen_bullets[bullet])
                second = _relative(changeset.path)
                raise ReleaseNotesError(f'Duplicate release-note bullet in {first} and {second}: {bullet}')
            seen_bullets[bullet] = changeset.path
            grouped[changeset.category].append(bullet)
    return {category: bullets for category, bullets in grouped.items() if bullets}


def render_changelog_section(version: str, changesets: list[Changeset], date: str) -> str:
    lines = [f'## Version {version} - {date}', '']
    for category, bullets in grouped_bullets(changesets).items():
        lines.extend((f'### {category}', ''))
        lines.extend(bullets)
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def render_github_release_notes(version: str, changesets: list[Changeset], repo: str) -> str:
    tag = f'v{version}'
    zip_name = f'The-Sims-4-Translator-Plus-v{version}-windows.zip'
    checksum_name = f'{zip_name}.sha256'
    bundle_name = f'{zip_name}.sigstore.json'

    lines = [
        f'The Sims 4 Translator Plus {tag}',
        '',
        'This release was built by GitHub Actions from the public repository.',
        '',
        'Why this release exists:',
        '',
    ]
    for category, bullets in grouped_bullets(changesets).items():
        lines.extend((f'### {category}', ''))
        lines.extend(bullets)
        lines.append('')

    lines.extend(
        [
            'Release assets:',
            f'- Windows ZIP: `{zip_name}`',
            f'- SHA256 checksum: `{checksum_name}`',
            f'- Sigstore/cosign ZIP signature bundle: `{bundle_name}`',
            '- GitHub immutable release attestation: generated automatically by GitHub and shown as `Release attestation (json)`',
            '',
            'Why two JSON-looking files?',
            '- `Release attestation (json)` is generated by GitHub for the immutable release. It binds this tag, commit, and all release assets.',
            f'- `{bundle_name}` is generated by cosign for the Windows ZIP. It proves the ZIP was signed by this repository\'s GitHub Actions release workflow.',
            'They are intentionally different trust layers, not duplicates.',
            '',
            'Verify the checksum:',
            '```powershell',
            f'Get-FileHash .\\{zip_name} -Algorithm SHA256',
            '```',
            '',
            'Verify the immutable GitHub release attestation:',
            '```powershell',
            f'gh release verify {tag} --repo {repo}',
            f'gh release verify-asset {tag} .\\{zip_name} --repo {repo}',
            '```',
            '',
            'Verify GitHub build provenance:',
            '```powershell',
            f'gh attestation verify .\\{zip_name} --repo {repo}',
            '```',
            '',
            'Verify the cosign keyless signature:',
            '```powershell',
            f'cosign verify-blob --bundle .\\{bundle_name} --certificate-identity "https://github.com/{repo}/.github/workflows/release-build.yml@refs/tags/{tag}" --certificate-oidc-issuer "https://token.actions.githubusercontent.com" .\\{zip_name}',
            '```',
            '',
            'Notes:',
            '- The Windows executable is not Authenticode code-signed yet, so SmartScreen may still warn on first run.',
            '- GitHub release attestation and Sigstore/cosign prove release provenance; they do not replace Windows code signing.',
            '- This community project is not affiliated with Electronic Arts, Maxis, or The Sims.',
        ]
    )
    return '\n'.join(lines).rstrip() + '\n'


def update_changelog(changelog_path: Path, section: str, version: str) -> None:
    if changelog_path.exists():
        text = changelog_path.read_text(encoding='utf-8')
    else:
        text = '# Changelog\n'

    heading_pattern = re.compile(
        rf'^## Version {re.escape(version)}\b.*?(?=^## Version |\Z)',
        re.MULTILINE | re.DOTALL,
    )
    if heading_pattern.search(text):
        updated = heading_pattern.sub(section.rstrip() + '\n\n', text, count=1)
    else:
        marker = '# Changelog'
        if marker not in text:
            raise ReleaseNotesError(f'{_relative(changelog_path)} must contain "# Changelog"')
        updated = text.replace(marker, f'{marker}\n\n{section.rstrip()}', 1)
        if not updated.endswith('\n'):
            updated += '\n'
    changelog_path.write_text(updated.rstrip() + '\n', encoding='utf-8')


def archive_changesets(changesets: list[Changeset], version: str, root: Path = ROOT) -> None:
    archive_dir = root / 'changes' / 'archive' / f'v{version}'
    archive_dir.mkdir(parents=True, exist_ok=True)
    for changeset in changesets:
        active_dir = root / 'changes'
        if changeset.path.parent.resolve() != active_dir.resolve():
            continue
        destination = archive_dir / changeset.path.name
        if destination.exists():
            if destination.read_text(encoding='utf-8') != changeset.path.read_text(encoding='utf-8'):
                raise ReleaseNotesError(f'Cannot archive {_relative(changeset.path, root)}; destination differs')
            changeset.path.unlink()
            continue
        shutil.move(str(changeset.path), str(destination))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Collect release changesets and render release notes.')
    parser.add_argument('--version', required=True, help='Release version without leading v, for example 2.2.19.')
    parser.add_argument('--check', action='store_true', help='Validate that release notes exist for the version.')
    parser.add_argument('--write-changelog', action='store_true', help='Insert or replace this version section in CHANGELOG.md and archive active changesets.')
    parser.add_argument('--output', help='Write full GitHub Release notes to this file.')
    parser.add_argument('--date', default=_dt.date.today().isoformat(), help='Date for CHANGELOG.md, default: today.')
    parser.add_argument('--repo', default='anhtahaylove/sims4-translator', help='GitHub repository used in verification commands.')
    args = parser.parse_args(argv)

    try:
        changesets = collect_changesets(args.version)
        if args.write_changelog:
            section = render_changelog_section(args.version, changesets, args.date)
            update_changelog(CHANGELOG, section, args.version)
            archive_changesets(changesets, args.version)
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(render_github_release_notes(args.version, changesets, args.repo), encoding='utf-8')
        print(f'Release notes OK for {args.version}: {len(changesets)} changeset(s).')
        return 0
    except ReleaseNotesError as exc:
        print(f'Release notes verification failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
