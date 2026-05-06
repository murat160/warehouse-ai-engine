"""Speech-to-text powered by openai-whisper (runs locally, no API key)."""

from __future__ import annotations

import logging
from typing import Optional

import whisper

logger = logging.getLogger(__name__)


class ASRService:
    """Wraps an openai-whisper model and exposes a single ``transcribe`` call."""

    def __init__(self, model_name: str = "small") -> None:
        logger.info("loading whisper model %s", model_name)
        self.model_name = model_name
        self.model = whisper.load_model(model_name)

    def transcribe(self, wav_path: str, *, language: Optional[str] = None) -> str:
        result = self.model.transcribe(
            wav_path,
            task="transcribe",
            language=language,
        )
        return (result.get("text") or "").strip()
