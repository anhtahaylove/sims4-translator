# -*- coding: utf-8 -*-

import re
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


def iter_highlight_tokens(text: str) -> Iterator[HighlightToken]:
    for match in TOKEN_PATTERN.finditer(text or ''):
        token = match.group(0)
        yield HighlightToken(
            start=match.start(),
            end=match.end(),
            text=token,
            kind=classify_token(token),
        )


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
