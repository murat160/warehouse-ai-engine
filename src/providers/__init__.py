"""Provider abstraction layer for translation, STT and TTS backends."""

from .base import (
    AudioBytes,
    ProviderError,
    ProviderUnavailableError,
    STTProvider,
    STTResult,
    TTSProvider,
    TTSResult,
    TranslationProvider,
    TranscriptSegment,
)
from .fallback_provider import FallbackProvider
from .openai_provider import OpenAIProvider

__all__ = [
    "AudioBytes",
    "FallbackProvider",
    "OpenAIProvider",
    "ProviderError",
    "ProviderUnavailableError",
    "STTProvider",
    "STTResult",
    "TTSProvider",
    "TTSResult",
    "TranscriptSegment",
    "TranslationProvider",
]
