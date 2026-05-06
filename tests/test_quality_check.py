"""Translation quality heuristics."""

from __future__ import annotations

from src.translator.quality_check import check


def test_empty_translation_fails():
    r = check(source_text="hello", translated_text="", source_lang="en", target_lang="ru")
    assert r.ok is False
    assert "empty translation" in r.issues


def test_russian_must_be_cyrillic():
    r = check(
        source_text="hello",
        translated_text="privet",
        source_lang="en",
        target_lang="ru",
    )
    assert r.ok is False
    assert any("Cyrillic" in i for i in r.issues)


def test_clean_russian_passes():
    r = check(
        source_text="hello world",
        translated_text="привет мир",
        source_lang="en",
        target_lang="ru",
    )
    assert r.ok is True
    assert r.score == 1.0


def test_turkmen_long_text_without_diacritics_is_flagged():
    long_text = "salam dostlar bu uzyn metin diakritikalarsyz " * 4
    r = check(
        source_text="x" * 200,
        translated_text=long_text,
        source_lang="ru",
        target_lang="tk",
    )
    assert any("diacritics" in i for i in r.issues)


def test_unchanged_output_is_flagged():
    r = check(
        source_text="hello world",
        translated_text="hello world",
        source_lang="en",
        target_lang="ru",
    )
    assert r.ok is False
