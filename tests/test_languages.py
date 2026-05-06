"""Language registry and validation."""

from __future__ import annotations

import pytest

from src.translator.languages import (
    ALL_PAIRS,
    LANGUAGES,
    PRIORITY_PAIRS,
    LanguagePair,
    UnsupportedLanguageError,
    normalize_language,
)


def test_supports_required_codes():
    assert set(LANGUAGES.keys()) == {"ru", "tk", "tr", "en"}


@pytest.mark.parametrize(
    "value, expected",
    [
        ("ru", "ru"), ("RU", "ru"), ("rus", "ru"), ("русский", "ru"),
        ("tk", "tk"), ("tuk", "tk"), ("turkmen", "tk"), ("türkmençe", "tk"),
        ("tr", "tr"), ("turkish", "tr"),
        ("en", "en"), ("english", "en"),
    ],
)
def test_normalize_language_accepts_aliases(value, expected):
    assert normalize_language(value) == expected


@pytest.mark.parametrize("bad", ["", "xx", "klingon", None])
def test_normalize_language_rejects_unknown(bad):
    with pytest.raises(UnsupportedLanguageError):
        normalize_language(bad)


def test_pair_rejects_same_language():
    with pytest.raises(UnsupportedLanguageError):
        LanguagePair.of("ru", "ru")


def test_priority_pairs_are_ru_tk_only():
    assert PRIORITY_PAIRS == frozenset({("ru", "tk"), ("tk", "ru")})


def test_all_pairs_count():
    # 4 languages × 3 directions each = 12 ordered pairs.
    assert len(ALL_PAIRS) == 12


def test_pair_priority_flag():
    assert LanguagePair.of("ru", "tk").is_priority is True
    assert LanguagePair.of("tk", "ru").is_priority is True
    assert LanguagePair.of("ru", "en").is_priority is False
