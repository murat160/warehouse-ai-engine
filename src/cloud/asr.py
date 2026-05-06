"""Speech-to-text powered by openai-whisper (runs locally, no API key).

The transcribe call returns both the recognised text and the language
Whisper detected — so the rest of the pipeline can route translation
without asking the user to pick a source language.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import whisper

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ASRResult:
    text: str
    language: Optional[str] = None  # ISO 639-1 (or None when unknown)


class ASRService:
    """Wraps an openai-whisper model and exposes a single ``transcribe`` call."""

    def __init__(self, model_name: str = "small") -> None:
        logger.info("loading whisper model %s", model_name)
        self.model_name = model_name
        self.model = whisper.load_model(model_name)

    def transcribe(
        self, wav_path: str, *, language: Optional[str] = None
    ) -> ASRResult:
        """Transcribe ``wav_path``. ``language`` is an optional hint."""
        result = self.model.transcribe(
            wav_path,
            task="transcribe",
            language=language,
        )
        text = (result.get("text") or "").strip()
        detected = result.get("language") or language
        return ASRResult(text=text, language=detected)
