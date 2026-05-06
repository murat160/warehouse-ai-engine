"""Supported languages and language-pair validation.

The engine supports four languages: Russian, Turkmen, Turkish and English.
Translation is bidirectional between every pair, with ru<->tk being the
primary, highest-quality direction.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Dict, FrozenSet, Tuple


@dataclass(frozen=True)
class Language:
    """ISO 639-1 language descriptor with display metadata."""

    code: str
    name_en: str
    name_native: str
    script: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.code


LANGUAGES: Dict[str, Language] = {
    "ru": Language(code="ru", name_en="Russian", name_native="Русский", script="Cyrillic"),
    "tk": Language(code="tk", name_en="Turkmen", name_native="Türkmençe", script="Latin"),
    "tr": Language(code="tr", name_en="Turkish", name_native="Türkçe", script="Latin"),
    "en": Language(code="en", name_en="English", name_native="English", script="Latin"),
}

SUPPORTED_CODES: FrozenSet[str] = frozenset(LANGUAGES.keys())

# Priority pairs are translated with extra glossary post-processing and a
# stricter literary-register system prompt.
PRIORITY_PAIRS: FrozenSet[Tuple[str, str]] = frozenset(
    {("ru", "tk"), ("tk", "ru")}
)

# All directions we explicitly support; equals every ordered pair of the four
# supported languages (12 directions).
ALL_PAIRS: FrozenSet[Tuple[str, str]] = frozenset(
    permutations(SUPPORTED_CODES, 2)
)


# A small set of common aliases users tend to type. Anything else falls
# through to a hard error so we never silently translate as the wrong language.
_ALIASES: Dict[str, str] = {
    "ru": "ru", "rus": "ru", "russian": "ru", "русский": "ru",
    "tk": "tk", "tuk": "tk", "tkm": "tk", "turkmen": "tk", "türkmençe": "tk", "туркменский": "tk",
    "tr": "tr", "tur": "tr", "turkish": "tr", "türkçe": "tr", "турецкий": "tr",
    "en": "en", "eng": "en", "english": "en", "английский": "en",
}


class UnsupportedLanguageError(ValueError):
    """Raised when a caller asks for a language code we do not handle."""


def normalize_language(value: str) -> str:
    """Coerce a user-supplied language identifier into our canonical code."""

    if value is None:
        raise UnsupportedLanguageError("language is required")
    key = value.strip().lower()
    code = _ALIASES.get(key)
    if code is None:
        raise UnsupportedLanguageError(
            f"unsupported language: {value!r}. supported: {sorted(SUPPORTED_CODES)}"
        )
    return code


@dataclass(frozen=True)
class LanguagePair:
    """A validated source -> target language pair."""

    source: Language
    target: Language

    @classmethod
    def of(cls, source: str, target: str) -> "LanguagePair":
        src = normalize_language(source)
        tgt = normalize_language(target)
        if src == tgt:
            raise UnsupportedLanguageError("source and target must differ")
        return cls(source=LANGUAGES[src], target=LANGUAGES[tgt])

    @property
    def codes(self) -> Tuple[str, str]:
        return (self.source.code, self.target.code)

    @property
    def is_priority(self) -> bool:
        return self.codes in PRIORITY_PAIRS

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.source.code}->{self.target.code}"
