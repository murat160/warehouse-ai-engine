"""Text-to-speech orchestrator with per-language provider routing.

For Turkmen (``tk``) we prefer the offline Meta MMS-TTS provider when it is
enabled by configuration — its quality on ``tk`` is currently better than
generic multilingual cloud voices. For ru/tr/en we route to the primary
(OpenAI) provider.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..providers.base import (
    ProviderUnavailableError,
    TTSProvider,
    TTSResult,
)
from ..translator.languages import normalize_language

logger = logging.getLogger(__name__)


class TextToSpeech:
    def __init__(
        self,
        *,
        primary: TTSProvider,
        fallback: Optional[TTSProvider] = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback

    def is_available(self, language: str) -> bool:
        lang = normalize_language(language)
        if self._supports(self.primary, lang):
            return True
        return self._supports(self.fallback, lang)

    def synthesize(
        self,
        text: str,
        *,
        language: str,
        voice: Optional[str] = None,
    ) -> TTSResult:
        if not text or not text.strip():
            raise ValueError("text is required")
        lang = normalize_language(language)

        # Turkmen routes to fallback first when available — better voice.
        order = (
            (self.fallback, self.primary) if lang == "tk" else (self.primary, self.fallback)
        )
        last_error: Optional[Exception] = None
        for provider in order:
            if provider is None:
                continue
            if not self._supports(provider, lang):
                continue
            try:
                return provider.synthesize(text, language=lang, voice=voice)
            except ProviderUnavailableError as exc:
                last_error = exc
                continue
        raise ProviderUnavailableError(
            f"no TTS provider can serve language={lang!r}: {last_error}"
        )

    @staticmethod
    def _supports(provider: Optional[TTSProvider], language: str) -> bool:
        if provider is None:
            return False
        try:
            return bool(provider.is_available(language))
        except TypeError:
            # Older interface: is_available() with no args.
            return bool(provider.is_available())  # type: ignore[call-arg]
