"""Glossary post-processing."""

from __future__ import annotations

from src.translator.glossary import Glossary, GlossaryEntry


def test_default_glossary_replaces_known_terms_ru_tk():
    g = Glossary.default()
    out = g.apply("Спасибо за заказ", "ru", "tk")
    # "спасибо" -> "sag boluň", "заказ" -> "sargyt"; case-insensitive match.
    assert "sag boluň" in out.lower()
    assert "sargyt" in out.lower()


def test_glossary_keeps_unrelated_text():
    g = Glossary.default()
    text = "Это просто предложение без терминов из словаря."
    assert g.apply(text, "ru", "tk") == text


def test_glossary_whole_word_match():
    g = Glossary()
    g.add("ru", "tk", [GlossaryEntry("кот", "pişik")])
    assert g.apply("Скотовод и кот", "ru", "tk") == "Скотовод и pişik"


def test_glossary_unknown_pair_is_noop():
    g = Glossary.default()
    assert g.apply("hello world", "en", "tr") == "hello world"


def test_common_rules_apply_across_pairs():
    g = Glossary.default()
    out = g.apply("Бренд Ehli Trend", "ru", "tk")
    assert "Ehli Trend" in out
