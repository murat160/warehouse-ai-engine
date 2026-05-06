"""TranslationMemoryService lookup + remember flow."""

from __future__ import annotations

from src.translator.translation_memory import TranslationMemoryService


def test_lookup_returns_none_when_empty(tm_repo):
    service = TranslationMemoryService(tm_repo)
    assert service.lookup(text="hello", source_lang="en", target_lang="ru") is None


def test_remember_then_lookup_hits(tm_repo):
    service = TranslationMemoryService(tm_repo)
    service.remember(
        source_text="быстрая доставка",
        target_text="çalt eltip bermek",
        source_lang="ru",
        target_lang="tk",
    )
    hit = service.lookup(
        text="  Быстрая   Доставка ",  # normalised match
        source_lang="ru",
        target_lang="tk",
    )
    assert hit is not None
    assert hit.entry.target_text == "çalt eltip bermek"


def test_remember_is_idempotent_per_pair(tm_repo):
    service = TranslationMemoryService(tm_repo)
    service.remember(
        source_text="спасибо",
        target_text="sag boluň",
        source_lang="ru",
        target_lang="tk",
    )
    service.remember(
        source_text="спасибо",
        target_text="sag bolun",  # corrected
        source_lang="ru",
        target_lang="tk",
    )
    hit = service.lookup(text="спасибо", source_lang="ru", target_lang="tk")
    assert hit is not None and hit.entry.target_text == "sag bolun"
    assert len(tm_repo.list(source_lang="ru", target_lang="tk")) == 1
