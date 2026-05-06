"""Translator orchestration: provider selection, glossary, quality, fallback."""

from __future__ import annotations

import pytest

from src.providers.base import ProviderUnavailableError
from src.translator.translator_service import TranslatorService

from .conftest import FakeTranslationProvider


def test_translates_priority_pair_with_glossary(fake_provider):
    service = TranslatorService(primary=fake_provider, latency_budget=10.0)
    result = service.translate(text="Спасибо", source_lang="ru", target_lang="tk")
    assert result.target_lang == "tk"
    assert result.provider == "fake"
    assert result.fallback_used is False
    # Priority pair is reflected by quality_check accepting Latin output.
    assert result.quality.ok is True


def test_falls_back_when_primary_unavailable():
    primary = FakeTranslationProvider(available=False)
    fallback = FakeTranslationProvider()
    service = TranslatorService(primary=primary, fallback=fallback, latency_budget=10.0)
    result = service.translate(text="Привет", source_lang="ru", target_lang="en")
    assert result.fallback_used is True
    assert result.provider == "fake"  # both fakes share the name "fake"


def test_no_fallback_raises_when_primary_unavailable():
    primary = FakeTranslationProvider(available=False)
    service = TranslatorService(primary=primary, latency_budget=10.0)
    with pytest.raises(ProviderUnavailableError):
        service.translate(text="Привет", source_lang="ru", target_lang="en")


def test_empty_input_short_circuits(fake_provider):
    service = TranslatorService(primary=fake_provider)
    result = service.translate(text="   ", source_lang="ru", target_lang="tk")
    assert result.text == ""
    assert result.provider == "noop"


def test_records_latency_and_notes_on_overrun(fake_provider):
    service = TranslatorService(primary=fake_provider, latency_budget=0.0)
    result = service.translate(text="hi", source_lang="en", target_lang="ru")
    # We set the budget to zero, so any positive latency must produce a note.
    assert any("latency" in n for n in result.notes)


def test_unsupported_language_rejected(fake_provider):
    from src.translator.languages import UnsupportedLanguageError

    service = TranslatorService(primary=fake_provider)
    with pytest.raises(UnsupportedLanguageError):
        service.translate(text="hi", source_lang="ru", target_lang="ru")
