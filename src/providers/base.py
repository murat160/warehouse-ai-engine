"""Provider interfaces for translation, speech-to-text and text-to-speech.

Concrete providers (OpenAI, fallback, future ones) implement these abstract
classes. The translator/speech services depend on the interface only, so we
can swap providers per-language or per-deployment.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

AudioBytes = bytes


class ProviderError(RuntimeError):
    """Generic provider failure. Wraps backend errors with provider context."""


class ProviderUnavailableError(ProviderError):
    """Raised when a provider is not configured (e.g. missing API key)."""


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------


class TranslationProvider(ABC):
    """Translates plain text between two of our supported languages."""

    name: str = "abstract"

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider can serve a request right now."""

    @abstractmethod
    def translate(
        self,
        *,
        text: str,
        source_lang: str,
        target_lang: str,
        literary: bool = False,
    ) -> str:
        """Translate ``text`` from ``source_lang`` to ``target_lang``.

        ``literary`` is a hint asking the provider to prefer a clean,
        literary register — used for the priority ru<->tk pair.
        """


# ---------------------------------------------------------------------------
# Speech-to-text
# ---------------------------------------------------------------------------


@dataclass
class TranscriptSegment:
    """A single timestamped span of recognised speech."""

    start: float
    end: float
    text: str


@dataclass
class STTResult:
    """Output of a speech-to-text run."""

    text: str
    language: Optional[str] = None
    segments: List[TranscriptSegment] = field(default_factory=list)
    duration: float = 0.0


class STTProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def transcribe(
        self,
        audio: AudioBytes,
        *,
        language_hint: Optional[str] = None,
        with_segments: bool = False,
    ) -> STTResult: ...


# ---------------------------------------------------------------------------
# Text-to-speech
# ---------------------------------------------------------------------------


@dataclass
class TTSResult:
    """Output of a text-to-speech run."""

    audio: AudioBytes
    sample_rate: int
    format: str = "wav"


class TTSProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def is_available(self, language: str) -> bool: ...

    @abstractmethod
    def synthesize(
        self,
        text: str,
        *,
        language: str,
        voice: Optional[str] = None,
    ) -> TTSResult: ...
