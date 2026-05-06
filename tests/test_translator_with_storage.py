"""Integration: TranslatorService + user glossary + translation memory + channels."""

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
    result = service.translate(
        text="доставка", source_lang="ru", target_lang="tk"
    )
    assert "eltip bermek" in result.text
    assert "eltip bermek" in result.user_glossary_hits


def test_style_tone_emotion_propagate_to_result(glossary_repo, tm_repo):
    service = _build_service(glossary_repo, tm_repo)
    result = service.translate(
        text="Hello world",
        source_lang="en",
        target_lang="tk",
        style="blogger",
        tone="energetic",
        emotion="excited",
    )
    assert result.style == "blogger"
    assert result.tone == "energetic"
    assert result.emotion == "excited"


def test_unknown_style_falls_back_to_natural(glossary_repo, tm_repo):
    service = _build_service(glossary_repo, tm_repo)
    result = service.translate(
        text="Hello", source_lang="en", target_lang="ru", style="hyperbolic",
    )
    assert result.style == "natural"


def test_default_style_is_natural_not_literary(glossary_repo, tm_repo):
    service = _build_service(glossary_repo, tm_repo)
    # Default is now NATURAL even for the priority ru<->tk pair.
    result = service.translate(text="Привет", source_lang="ru", target_lang="tk")
    assert result.style == "natural"


def test_channel_glossary_wins_over_global(glossary_repo, tm_repo):
    glossary_repo.create(
        source_lang="ru", target_lang="tk",
        source_text="доставка", target_text="дост-global",
    )
    glossary_repo.create(
        source_lang="ru", target_lang="tk",
        source_text="доставка", target_text="дост-channel",
        channel_id="chan-1",
    )
    service = _build_service(glossary_repo, tm_repo)
    no_chan = service.translate(
        text="доставка", source_lang="ru", target_lang="tk",
    )
    with_chan = service.translate(
        text="доставка", source_lang="ru", target_lang="tk",
        channel_id="chan-1",
    )
    assert "дост-global" in no_chan.text
    assert "дост-channel" in with_chan.text


def test_channel_tm_short_circuits_provider(glossary_repo, tm_repo):
    tm_repo.upsert(
        source_lang="ru", target_lang="tk",
        source_text="спасибо", target_text="global-thanks",
    )
    tm_repo.upsert(
        source_lang="ru", target_lang="tk",
        source_text="спасибо", target_text="channel-thanks",
        channel_id="chan-1",
    )
    service = _build_service(glossary_repo, tm_repo)
    out = service.translate(
        text="спасибо", source_lang="ru", target_lang="tk", channel_id="chan-1"
    )
    assert out.tm_hit and out.text == "channel-thanks"
