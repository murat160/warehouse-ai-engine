"""Speech-to-text orchestrator.

Thin wrapper around an :class:`STTProvider`. Lives in its own module so the
rest of the engine can depend on a stable interface while we swap or add
backends (OpenAI Whisper, whisper.cpp, faster-whisper, MMS-ASR, etc.).
"""

from __future__ import annotations

import logging
from typing import Optional

from ..providers.base import AudioBytes, STTProvider, STTResult
from ..translator.languages import normalize_language

logger = logging.getLogger(__name__)


class SpeechToText:
    def __init__(self, provider: STTProvider) -> None:
        self.provider = provider

    def is_available(self) -> bool:
        return self.provider.is_available()

    def transcribe(
        self,
        audio: AudioBytes,
        *,
        language_hint: Optional[str] = None,
        with_segments: bool = False,
    ) -> STTResult:
        if not audio:
            raise ValueError("audio is required")
        hint = normalize_language(language_hint) if language_hint else None
        return self.provider.transcribe(
            audio,
            language_hint=hint,
            with_segments=with_segments,
        )
