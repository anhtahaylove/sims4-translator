# -*- coding: utf-8 -*-

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterator


TOKEN_BRACE = 'brace'
TOKEN_LINEBREAK = 'linebreak'
TOKEN_NUMBER = 'number'
TOKEN_SIM = 'sim'
TOKEN_TAG = 'tag'

TOKEN_PATTERN = re.compile(
    r'(?P<linebreak>(?:\\n)+)'
    r'|(?P<tag></?[A-Za-z][^<>]*>)'
    r'|(?P<brace>\{[^{}]+\})'
)


@dataclass(frozen=True)
class HighlightToken:
    start: int
    end: int
    text: str
    kind: str


@dataclass(frozen=True)
class TokenValidationResult:
    missing: tuple[str, ...] = ()
    extra: tuple[str, ...] = ()
    order_mismatch: bool = False
    linebreak_mismatch: bool = False

    @property
    def ok(self) -> bool:
        return not self.missing and not self.extra and not self.order_mismatch and not self.linebreak_mismatch

    def summary(self) -> str:
        if self.ok:
            return 'Token check: OK'

        parts = []
        if self.missing:
            parts.append(f'Missing {len(self.missing)}')
        if self.extra:
            parts.append(f'Extra {len(self.extra)}')
        if self.linebreak_mismatch:
            parts.append('Line breaks differ')
        if self.order_mismatch:
            parts.append('Order differs')
        return 'Token check: ' + ' | '.join(parts)

    def details(self) -> str:
        if self.ok:
            return 'All source tokens are preserved in the translation draft.'

        parts = []
        if self.missing:
            parts.append('Missing: ' + ', '.join(self.missing))
        if self.extra:
            parts.append('Extra: ' + ', '.join(self.extra))
        if self.linebreak_mismatch:
            parts.append('Line-break count differs')
        if self.order_mismatch:
            parts.append('Token order differs')
        return '; '.join(parts)


def iter_highlight_tokens(text: str) -> Iterator[HighlightToken]:
    for match in TOKEN_PATTERN.finditer(text or ''):
        token = match.group(0)
        yield HighlightToken(
            start=match.start(),
            end=match.end(),
            text=token,
            kind=classify_token(token),
        )


def validate_translation_tokens(source: str, translation: str) -> TokenValidationResult:
    source_tokens = tuple(token.text for token in iter_highlight_tokens(source))
    translation_tokens = tuple(token.text for token in iter_highlight_tokens(translation))

    missing = tuple((Counter(source_tokens) - Counter(translation_tokens)).elements())
    extra = tuple((Counter(translation_tokens) - Counter(source_tokens)).elements())
    order_mismatch = not missing and not extra and source_tokens != translation_tokens
    linebreak_mismatch = __linebreak_count(source_tokens) != __linebreak_count(translation_tokens)

    return TokenValidationResult(
        missing=missing,
        extra=extra,
        order_mismatch=order_mismatch,
        linebreak_mismatch=linebreak_mismatch,
    )


def __linebreak_count(tokens: tuple[str, ...]) -> int:
    return sum(token.count('\\n') for token in tokens if classify_token(token) == TOKEN_LINEBREAK)


def classify_token(token: str) -> str:
    if not token:
        return TOKEN_BRACE

    if token.startswith('\\n'):
        return TOKEN_LINEBREAK
    if token.startswith('<') and token.endswith('>'):
        return TOKEN_TAG
    if token.startswith('{') and token.endswith('}'):
        lowered = token.lower()
        if any(marker in lowered for marker in ('.number', '.money', '.currency', '.decimal', '.integer')):
            return TOKEN_NUMBER
        if '.sim' in lowered or 'simfirstname' in lowered or 'simlastname' in lowered:
            return TOKEN_SIM
    return TOKEN_BRACE
