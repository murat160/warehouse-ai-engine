"""Integration: TranslatorService + user glossary + translation memory."""

from __future__ import annotations

from src.translator.translation_memory import TranslationMemoryService
from src.translator.translator_service import TranslatorService
from src.translator.user_glossary import UserGlossaryService

from .conftest import FakeTranslationProvider


def _build_service(glossary_repo, tm_repo) -> TranslatorService:
    return TranslatorService(
        primary=FakeTranslationProvider(),
        user_glossary=UserGlossaryService(glossary_repo),
        translation_memory=TranslationMemoryService(tm_repo),
        latency_budget=10.0,
    )


def test_translation_memory_short_circuits_provider(glossary_repo, tm_repo):
    tm_repo.upsert(
        source_lang="ru", target_lang="tk",
        source_text="спасибо", target_text="sag boluň",
    )
    service = _build_service(glossary_repo, tm_repo)
    result = service.translate(text="Спасибо", source_lang="ru", target_lang="tk")
    assert result.tm_hit is True
    assert result.provider == "translation-memory"
    assert result.text == "sag boluň"


def test_user_glossary_overrides_provider_output(glossary_repo, tm_repo):
    glossary_repo.create(
        source_lang="ru", target_lang="tk",
        source_text="доставка", target_text="eltip bermek",
    )
    service = _build_service(glossary_repo, tm_repo)
    # The fake provider echoes the source. Our glossary entry replaces
    # any "доставка" token in the output, regardless of where it sits.
    result = service.translate(
        text="доставка", source_lang="ru", target_lang="tk"
    )
    assert "eltip bermek" in result.text
    assert "eltip bermek" in result.user_glossary_hits


def test_style_propagates_to_result(glossary_repo, tm_repo):
    service = _build_service(glossary_repo, tm_repo)
    result = service.translate(
        text="Hello world",
        source_lang="en",
        target_lang="tk",
        style="respectful",
    )
    assert result.style == "respectful"


def test_unknown_style_falls_back_to_neutral(glossary_repo, tm_repo):
    service = _build_service(glossary_repo, tm_repo)
    result = service.translate(
        text="Hello",
        source_lang="en",
        target_lang="ru",
        style="hyperbolic",
    )
    assert result.style == "neutral"
